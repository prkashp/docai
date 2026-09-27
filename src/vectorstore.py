import os
import re
import numpy as np
from langchain_core.embeddings import Embeddings
from langchain_milvus import Milvus
from dotenv import load_dotenv

load_dotenv()

COLLECTION_NAME = os.getenv("COLLECTION_NAME", "ocr_documents")
MILVUS_DB_PATH = os.getenv("MILVUS_DB_PATH", "./milvus_data")

class SimpleEmbeddings(Embeddings):
    """Hash-based embeddings for semantic search."""

    def __init__(self, dim=384):
        self.dim = dim

    def _tokenize(self, text):
        """Simple tokenization - split on word boundaries."""
        words = re.findall(r'\w+', text.lower())
        return words

    def _hash_to_vec(self, tokens):
        """Convert tokens to a normalized vector using consistent hashing."""
        vec = np.zeros(self.dim, dtype=np.float32)
        if not tokens:
            return vec
        for token in tokens:
            h = hash(token) % self.dim
            vec[h] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def embed_documents(self, texts):
        """Embed a list of texts."""
        vectors = []
        for text in texts:
            tokens = self._tokenize(text)
            vec = self._hash_to_vec(tokens)
            vectors.append(vec.tolist())
        return vectors

    def embed_query(self, text):
        """Embed a single query."""
        tokens = self._tokenize(text)
        vec = self._hash_to_vec(tokens)
        return vec.tolist()

def get_embeddings():
    return SimpleEmbeddings(dim=384)

def get_vectorstore():
    # Create Milvus data directory if it doesn't exist
    os.makedirs(MILVUS_DB_PATH, exist_ok=True)

    embeddings = get_embeddings()
    vectorstore = Milvus(
        embedding_function=embeddings,
        collection_name=COLLECTION_NAME,
        connection_args={
            "uri": f"{MILVUS_DB_PATH}/milvus.db",
        },
    )
    return vectorstore

if __name__ == "__main__":
    vs = get_vectorstore()
    print(f"Connected to Milvus Lite")
    print(f"Database path: {MILVUS_DB_PATH}")
    print(f"Collection: {COLLECTION_NAME}")
