# embedder.py

import os
import requests
from neo4j_graphrag.embeddings.base import Embedder as BaseEmbedder

class OllamaEmbedder(BaseEmbedder):
    def __init__(self, model_name="gte-qwen2-7b-instruct"):
        """
        Initializes the OllamaEmbedder.
        It retrieves the OLLAMA_HOST from environment variables.
        If not found, it defaults to http://localhost:11434 for local testing.
        """
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

        self.model = model_name
        self.host = ollama_host
        self.max_tokens = 8192
        self.chunk_overlap = 128
        print(f"--- Ollama Embedder initialized to connect to {self.host} ---") # Log untuk debugging

    def _embed(self, text: str):
        """Helper function to get embeddings from the Ollama API."""
        try:
            response = requests.post(
                f"{self.host}/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": text
                }
            )
            response.raise_for_status()  # This will raise an exception for HTTP errors (4xx or 5xx)
            return response.json()["embedding"]
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to Ollama at {self.host}: {e}")
            # Re-raise the exception to be handled by the calling code
            raise

    def embed_text(self, text: str):
        """Embeds a single piece of text."""
        return self._embed(text)

    def embed_query(self, query: str):
        """Embeds a single query."""
        return self._embed(query)

# Instantiate the embedder to be used across the application
Embedder = OllamaEmbedder()