# retrieval/retrieval.py

from config import driver
from retrieval.embedding import embed_query

def vector_search_chunks_generator(query_text, top_k=10, min_score=0.6):
    """
    Menggunakan nama indeks 'chunk_embeddings' yang konsisten.
    """
    vector = embed_query(query_text)
    if not vector:
        print("❌ Gagal membuat embedding untuk query.")
        return

    result = driver.execute_query(
        """
        CALL db.index.vector.queryNodes('chunk_embeddings', $top_k, $query_vector)
        YIELD node, score
        RETURN node, score
        """,
        {"query_vector": vector, "top_k": top_k}
    )
    for record in result.records:
        if record["score"] >= min_score:
            yield record

def keyword_search_hadith_by_number(hadith_number: int):
    """
    Mencari :Chunk {source:'info'} berdasarkan nomor hadis.
    """
    print(f"Executing keyword search for Hadith No. {hadith_number}.")
    
    result = driver.execute_query(
        """
        MATCH (info_chunk:Chunk {source: 'info', hadith_number: $nomor_hadis})
        RETURN elementId(info_chunk) AS info_id
        LIMIT 1
        """,
        {"nomor_hadis": hadith_number}
    )
    
    record = result.records[0] if result.records else None
    if record and record["info_id"]:
        info_id = record["info_id"]
        print(f"✅ Keyword search found a matching info_chunk. Element ID: {info_id}")
        return info_id
    
    print(f"❌ Keyword search did not find a match for Hadith No. {hadith_number}")
    return None