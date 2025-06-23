# retrieval/search.py

from retrieval.query_processor import process_user_query

def search_and_respond(teks_pertanyaan):
    return process_user_query(teks_pertanyaan)
