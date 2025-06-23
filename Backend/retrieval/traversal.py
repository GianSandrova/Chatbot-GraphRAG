# retrieval/traversal.py

from config import driver

def find_info_chunk_id(chunk_id: str):
    """
    Fungsi ini sekarang bersifat universal.
    Dari chunk manapun (text, translation, dll.), cari node :Chunk {source: 'info'}
    yang menjadi akarnya dengan menelusuri balik relasi :HAS_CHUNK.
    """
    result = driver.execute_query(
        """
        MATCH (c:Chunk) WHERE elementId(c) = $cid
        MATCH (c)<-[:HAS_CHUNK*0..5]-(info:Chunk {source: 'info'})
        RETURN elementId(info) AS info_id
        LIMIT 1
        """, {"cid": chunk_id}
    )
    return result.records[0]["info_id"] if result.records else None

def get_full_context_from_info(info_id: str):
    """
    Fungsi traversal universal yang cerdas.
    - Mengambil rantai chunk info->text->translation->tafsir.
    - Secara opsional, mengambil konteks hirarki (Surah/Ayat atau Bab/Kitab).
    """
    traversal = driver.execute_query(
        """
        MATCH (info:Chunk {source: 'info'})
        WHERE elementId(info) = $info_id

        OPTIONAL MATCH (info)-[:HAS_CHUNK]->(text:Chunk {source: 'text'})
        OPTIONAL MATCH (text)-[:HAS_CHUNK]->(translation:Chunk {source: 'translation'})
        OPTIONAL MATCH (translation)-[:HAS_CHUNK]->(tafsir:Chunk {source: 'tafsir'}) 
        
        OPTIONAL MATCH (ayat:Ayat)-[:HAS_CHUNK]->(info)
        OPTIONAL MATCH (surah:Surah)-[:HAS_AYAT]->(ayat)

        OPTIONAL MATCH (bab:Bab)-[:CONTAINS_HADITH_CHUNK]->(info)
        OPTIONAL MATCH (kitab:Kitab)-[:HAS_BAB]->(bab)

        RETURN 
            info.text AS info_text,
            text.text AS text_text,
            translation.text AS translation_text,
            tafsir.text AS tafsir_text,
            
            info.surah_name AS surah_name,
            info.ayat_number AS ayat_number,
            info.hadith_number AS hadith_number,
            
            bab.name AS bab_name,
            kitab.name AS kitab_name,
            info.source_name AS source_name
        LIMIT 1
        """, {"info_id": info_id}
    )
    return traversal.records[0] if traversal.records else None


# =====================================================================
# == FUNGSI BARU UNTUK MENGAMBIL HADIS TETANGGA ==
# =====================================================================
def get_neighboring_hadiths_in_bab(bab_name: str, kitab_name: str, source_name: str, exclude_hadith_number: int, limit: int = 1):
    """
    NEW: Mencari hadis lain dalam Bab yang sama.
    - Mengambil hadis tetangga untuk memperkaya konteks.
    - Mengecualikan hadis yang sudah ditemukan oleh vector search.
    """
    neighbor_ids = driver.execute_query(
        """
        // 1. Temukan Bab yang tepat berdasarkan nama, kitab, dan sumber
        MATCH (b:Bab {name: $bab_name, kitab_name: $kitab_name, source_name: $source_name})
        
        // 2. Temukan semua info chunk hadis di dalam bab tersebut
        MATCH (b)-[:CONTAINS_HADITH_CHUNK]->(info:Chunk {source:'info'})
        
        // 3. Kecualikan hadis yang nomornya sama dengan yang sudah kita temukan
        WHERE info.hadith_number <> $exclude_hadith_number
        
        // 4. Kembalikan elementId dan batasi jumlahnya
        RETURN elementId(info) AS info_id
        LIMIT $limit
        """, {
            "bab_name": bab_name,
            "kitab_name": kitab_name,
            "source_name": source_name,
            "exclude_hadith_number": exclude_hadith_number,
            "limit": limit
        }
    )
    return [record["info_id"] for record in neighbor_ids.records]