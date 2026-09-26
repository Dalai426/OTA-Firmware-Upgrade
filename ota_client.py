import json
import paho.mqtt.client as mqtt
import sys
from pathlib import Path
from MerkleTree import build_merkle_tree
import math
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from typing import cast

manifest_topic='ota/manifest'
chunk_topic='ota/chunk'
status_topic='client/status'

BROKER = "localhost"
PORT = 1883
PASSWORD="my_password"
USERNAME="ota_server"

signature_length = 384

with open("public_key.pem", "rb") as key_file:
    public_key = cast(
        RSAPublicKey,
        serialization.load_pem_public_key(
            key_file.read()
        )
    )

class Chunk:
    def __init__(self, status: str, path: str, content: bytes | None):
        self.status: str = status
        self.path: Path = Path(path)
        self.content: bytes | None = content
        self.path.parent.mkdir(parents=True, exist_ok=True)

class OtaUpdate:
    def __init__(self, version:str, root:str, chunk_count:int,manifest_path:str):
        self.version = version
        self.root = root
        self.chunk_count = chunk_count
        self.manifest_path: Path = Path(manifest_path)
        self.reconstructed_firmware_path:Path = Path(self.version) / "firmware_reconstructed.txt"
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.chunks: dict[int, Chunk] = {}
        for i in range(chunk_count):
            self.chunks[i] = Chunk(
                status="pending",
                path=f"{version}/data/chunk_{i}.bin",
                content=None
            )
    def reconstruct_firmware(self):
        with self.reconstructed_firmware_path.open("wb") as firmware:
            for index in sorted(self.chunks):
                chunk = self.chunks[index]
                with chunk.path.open("rb") as f:
                    firmware.write(f.read())


    
otaUpdate : OtaUpdate | None

def receive_manifest(payload:bytes):
    global otaUpdate
    try:
        signature = payload[:signature_length]
        manifest_payload = payload[signature_length:]
        try:
            public_key.verify(
                signature,
                manifest_payload,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
        except InvalidSignature:
            print("Invalid manifest signature.")
            raise InvalidSignature

        data = json.loads(manifest_payload.decode("utf-8"))
        root = data['root']
        version=data['version']
        chunk_count:int=data['chunk_count']
        otaUpdate = OtaUpdate(version, root, chunk_count,f"{version}/data/manifest.json")
        with otaUpdate.manifest_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        
        returningStatus = {
            "status": "PendingChunks",
            "version": version
        }
        client.publish(status_topic, payload=json.dumps(returningStatus).encode("utf-8"), qos=2)
        print("Ready for receiving chunks")
    except Exception as e:
        print(f"Error occurred while sending status information: {e}")
        otaUpdate=None
        return

def receive_chunks(payload:bytes):
    global otaUpdate
    try:
        # Separate metadata and chunk data
        json_data, chunk_data = payload.split(b"\n", 1)
        meta_data=json.loads(json_data.decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        print("Invalid chunk payload")
        return

    if otaUpdate is None:
        return
    if meta_data["version"]!=otaUpdate.version:
        print("Ignoring chunk: version mismatch")
        return
    
    chunk_index = meta_data.get("chunk_index")
    if chunk_index not in otaUpdate.chunks:
        print(f"Ignoring chunk: invalid chunk index {chunk_index}")
        return
    chunk = otaUpdate.chunks[chunk_index]

    # writing chunk into file.
    if chunk is not None and chunk.status=='pending':
        with open(chunk.path, "wb") as f:
            f.write(chunk_data)
        chunk.content=chunk_data
        chunk.status="received"

    if all(
        chunk.status == "received"
        for chunk in otaUpdate.chunks.values()
    ):
        if validate_merkle_tree(ota=otaUpdate):
            otaUpdate.reconstruct_firmware()
            client.publish(status_topic, payload=json.dumps({
                "status": "SuccessfullyDelivered",
                "version": otaUpdate.version
            }).encode("utf-8"), qos=2)
        else:
            print("Verification failed.")
            client.publish(status_topic, payload=json.dumps({
                "status": "DeliveryFailed",
                "version": otaUpdate.version
            }).encode("utf-8"), qos=2)
            otaUpdate=None

def validate_merkle_tree(ota:OtaUpdate):
    tree_height = int(math.log2(ota.chunk_count))
    merkle_root=build_merkle_tree(tree_height,0,chunks=[chunk.content for chunk in ota.chunks.values()])
    if ota.root != merkle_root.hash:
        return False
    return True
    


def on_message(client, userdata, message):
    print("Topic:", message.topic)
    print("Received", len(message.payload), "bytes")
    topic:str=message.topic
    if topic == manifest_topic:
        receive_manifest(message.payload)
    elif topic.startswith(f"{chunk_topic}/"):
        receive_chunks(message.payload)



client = mqtt.Client()
client.username_pw_set(
    username=USERNAME,
    password=PASSWORD
)
client.on_message = on_message
client.connect(BROKER, PORT)
client.subscribe(manifest_topic, qos=2)
client.subscribe(f"{chunk_topic}/+", qos=2)
try:
    client.loop_forever()
except KeyboardInterrupt:
    print("Stopping OTA client...")
    client.disconnect()
