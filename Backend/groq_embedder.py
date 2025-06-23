# embedder.py
import requests
from neo4j_graphrag.embeddings.base import Embedder as BaseEmbedder

class OllamaEmbedder(BaseEmbedder):
    def __init__(self, model_name="gte-qwen2-7b-instruct", host="http://localhost:11434"):
        self.model = model_name
        self.host = host
        self.max_tokens = 8192
        self.chunk_overlap = 128

    def _embed(self, text: str):
        response = requests.post(
            f"{self.host}/api/embeddings",
            json={
                "model": self.model,
                "prompt": text
            }
        )
        response.raise_for_status()
        return response.json()["embedding"]

    def embed_text(self, text: str):
        return self._embed(text)

    def embed_query(self, query: str):
        return self._embed(query)

Embedder = OllamaEmbedder()