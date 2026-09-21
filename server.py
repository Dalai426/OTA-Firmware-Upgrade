import math
import sys
from MerkleTree import build_merkle_tree
import json
from pathlib import Path

with open("firmware.txt", "rb") as file:
    data: bytes = file.read()

chunks = []
chunk_size_base = math.floor(len(data)/4)
chunk_size = 4

extra_bytes  = len(data) % chunk_size

if not len(data) >= chunk_size:
    print("Firmware file must contain at least 4 bytes.")
    sys.exit(1)

head = 0
tail = 0

# preparing 4 ordered, non-empty bytes chunks
for i in range(chunk_size):
    extra_byte = 0
    if i < extra_bytes:
        extra_byte = 1

    # If the file size is not divisible by four, the extra bytes are distributed among the first chunks one by one.
    tail = head + chunk_size_base + extra_byte
    chunks.append(data[head:tail])
    head = tail

# creating merkle tree
chunk_count = len(chunks)
tree_height = math.log2(chunk_count)
merkle_tree_root = build_merkle_tree(int(tree_height), 0, chunks)



data_folder = Path("data/")
data_folder.mkdir(parents=True, exist_ok=True)

for i, chunk in enumerate(chunks):
    with open(data_folder / f"chunk_{i}.bin", "wb") as file:
        file.write(chunk)

# Creating manifest file
firmware_version = "1.0.0"
manifest = {
    "version": firmware_version,
    "size": len(data),
    "chunk_count": len(chunks),
    "root": merkle_tree_root.hash,
    "chunks": [
        {
            "index": i,
            "filename": str(data_folder / f"chunk_{i}.bin")
        }
        for i in range(len(chunks))
    ]
}

with open(data_folder / "manifest.json", "w") as file:
    json.dump(manifest, file, indent=4)