import json
import paho.mqtt.client as mqtt
import sys

manifest_topic='ota/manifest'
chunk_topic='ota/chunk'
status_topic='client/status'

BROKER = "localhost"
PORT = 1883

version:str
chunks={}

def send_manifest():
    global version, chunks
    try:
        with open("data/manifest.json", "r") as file:
            data = json.load(file)
            if data is None:
                print("Manifest data is empty.")
                raise Exception("Manifest data is empty.")
        version=data['version']
        if version is None:
            print("Version is missing in the manifest.")
            raise Exception("Version is missing in the manifest.")
        chunks = {
            i: "pending"
            for i in range(data["chunk_count"])
        }
        # MQTT's payload is fundamentally bytes.
        # Using UTF-8 encoding to convert the JSON string to bytes.
        payload = json.dumps(data).encode("utf-8")
        client.publish(manifest_topic, payload=payload, qos=2)
        print("Manifest Published")
    except Exception as e:
        print(f"Error occurred while sending manifest: {e}")
        sys.exit(1)

def send_chunks(path:str, version:str, chunk_index:int):
    try:
        with open(path, "rb") as file:
            chunk_data = file.read()
        metadata = {
            "version": version,
            "chunk_index": chunk_index
        }
        json_data = json.dumps(metadata).encode("utf-8")
        payload = json_data + b"\n" + chunk_data
        print(f"Sending chunk {chunk_index}")
        print(f"{chunk_topic}/{version}")
        client.publish(f"{chunk_topic}/{version}", payload=payload, qos=2)
        chunks[chunk_index] = "sent"
        print(f"Sent chunk {chunk_index}")
    except Exception as e:
        print(f"Error occurred while sending chunk {chunk_index}: {e}")
        sys.exit(1)


def on_message(client, userdata, message):
    print("Topic:", message.topic)
    print("Received", len(message.payload), "bytes")
    data = json.loads(message.payload.decode("utf-8"))
    print("Status Data:", data)
    if version != data.get("version"):
        print(f"Mismatching Firmware Version")
        raise Exception("Mismatching Firmware Version")
            
    if message.topic == status_topic:
        try:
            status=data.get("status")
            if status == 'PendingChunks':
                for index, chunk_status in chunks.items():
                    if chunk_status == "pending":
                        path = f"./data/chunk_{index}.bin"
                        send_chunks(path, version, index)
            elif status == 'SuccessfullyDelivered':
                sys.exit(0)
            else:    
                print(f"Firmware Update Failed")
                raise Exception("Firmware Update Failed")         
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON message from client: {e}")
            sys.exit(1)



client = mqtt.Client()

client.on_message = on_message

client.connect(BROKER, PORT)

client.subscribe(status_topic, qos=2)
send_manifest()
try:
    client.loop_forever()
except KeyboardInterrupt:
    print("Stopping OTA publisher...")
    client.disconnect()
