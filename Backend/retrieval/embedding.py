# retrieval/embedding.py

from groq_embedder import Embedder

def embed_query(text):
    return Embedder.embed_query(text)

def embed_combined(teks_pertanyaan, riwayat_chat):
    combined_text = f"Pertanyaan: {teks_pertanyaan}\nRiwayat Chat: {riwayat_chat}"
    return embed_query(combined_text)
