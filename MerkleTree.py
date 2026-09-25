import math
import hashlib

class Merkle_Node:
    def __init__(
        self,
        hash: str,
        left: "Merkle_Node | None" = None,
        right: "Merkle_Node | None" = None
    ):
        self.hash: str = hash
        self.left: Merkle_Node | None = left
        self.right: Merkle_Node | None = right

def build_merkle_tree(tree_height: int, chunk_index: int, chunks: list):
    if tree_height == 0:
        node = Merkle_Node(hashlib.sha256(chunks[chunk_index]).hexdigest())
        return node

    left_node = build_merkle_tree(tree_height - 1, chunk_index * 2, chunks)
    right_node = build_merkle_tree(tree_height - 1, chunk_index * 2 + 1, chunks)

    parent_hash = hashlib.sha256((left_node.hash + right_node.hash).encode()).hexdigest()
    parent_node = Merkle_Node(parent_hash, left_node, right_node)
    return parent_node
