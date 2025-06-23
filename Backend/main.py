# backend/main.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Tuple

# Import fungsi inti Anda dari folder retrieval
from retrieval.query_processor import process_user_query

app = FastAPI(title="Chatbot RAG Backend")

# Definisikan model data untuk menerima request
class QueryRequest(BaseModel):
    question: str
    history: List[Tuple[str, str]] = [] # Format: [(user_msg, bot_msg), ...]

# Definisikan endpoint API
@app.post("/ask")
def ask_question(request: QueryRequest):
    """
    Endpoint utama untuk memproses pertanyaan dari frontend.
    Menerima pertanyaan dan riwayat chat, lalu mengembalikan jawaban.
    """
    # Panggil fungsi logika inti Anda dengan data dari request
    answer = process_user_query(request.question, request.history)
    return {"answer": answer}