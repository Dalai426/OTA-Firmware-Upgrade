import json
import paho.mqtt.client as mqtt
import sys
from pathlib import Path

manifest_topic='ota/manifest'
chunk_topic='ota/chunk'
status_topic='client/status'

BROKER = "localhost"
PORT = 1883

class OtaUpdate:
    def __init__(self, version:str, root:str, chunk_count:int,manifest_path:str):
        self.version = version
        self.root = root
        self.chunk_count = chunk_count
        manifest_path=manifest_path
        chunks = {}
        for i in range(chunk_count):
            chunks[i].status = "pending"
            chunks[i].path=f"{version}/data/chunk_{i}.bin"
        self.chunks=chunks
    
otaUpdate:OtaUpdate

def receive_manifest(payload:bytes):
    global otaUpdate
    try:
        data = json.loads(payload.decode("utf-8"))
        root = data['root']
        version=data['version']
        chunk_count:int=data['chunk_count']
        otaUpdate = OtaUpdate(version, root, chunk_count,f"{version}/data/manifest.json")
        returningStatus = {
            "status": "PendingChunks",
            "version": version
        }
        client.publish(status_topic, payload=json.dumps(returningStatus).encode("utf-8"), qos=2)
        print("Ready for receiving chunks")
    except Exception as e:
        print(f"Error occurred while sending status information: {e}")
        sys.exit(1)

def receive_chunks(payload:bytes):
    global otaUpdate
    # Separate metadata and chunk data
    json_data, chunk_data = payload.split(b"\n", 1)
    meta_data=json.loads(json_data.decode("utf-8"))
    if(meta_data.version!=otaUpdate.version):
        print("Ignoring chunk: version mismatch")
        return
    if otaUpdate is None:
        return
    chunk=otaUpdate.chunks[meta_data["chunk_index"]]
    # writing chunk into file.
    if chunk is not None and chunk.status=='pending':
        chunk_file = chunk.path
        with open(chunk_file, "wb") as f:
            f.write(chunk_data)
        chunk.status="received"
        
    if all(
    status == "received"
    for status in otaUpdate.chunks.values()
    ):
        client.publish(status_topic, payload=json.dumps({
            "status": "SuccessfullyDelivered",
            "version": otaUpdate.version
        }).encode("utf-8"), qos=2)
        

def on_message(client, userdata, message):
    print("Topic:", message.topic)
    print("Received", len(message.payload), "bytes")
    if message.topic == manifest_topic:
        receive_manifest(message.payload)
    elif message.topic.startsWith(chunk_topic):
        receive_chunks(message.payload)



client = mqtt.Client()

client.on_message = on_message

client.connect(BROKER, PORT)
client.subscribe(status_topic, qos=2)
try:
    client.loop_forever()
except KeyboardInterrupt:
    print("Stopping OTA client...")
    client.disconnect()
