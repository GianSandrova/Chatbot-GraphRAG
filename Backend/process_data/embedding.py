# process_data/embedding.py
"""
Module for embedding text using a predefined embedding model.
"""

from Backend.config import DIMENSION
from Backend.groq_embedder import Embedder

def embed_chunk(text):
    """
    Generate a semantic embedding vector from given text.

    Args:
        text (str): Text to be embedded.

    Returns:
        list: Embedding vector.

    Raises:
        ValueError: If the embedding result is invalid.
    """
    vector = Embedder.embed_text(text)
    if not isinstance(vector, list) or len(vector) != DIMENSION:
        raise ValueError("❌ Invalid embedding vector")
    return vector
