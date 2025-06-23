# process_data/chunking.py
"""
Module for processing religious texts, including the Quran and Hadith,
and structuring them as a graph in Neo4j.
"""

from uuid import uuid4
from process_data.embedding import embed_chunk

def chunk_text(text, max_tokens=8192, overlap=128):
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + max_tokens, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += max_tokens - overlap
    return chunks

def extract_ayah_number(ayah_key: str) -> int:
    try:
        return int(''.join(filter(str.isdigit, ayah_key)))
    except Exception:
        raise ValueError(f"❌ Gagal parsing ayat: {ayah_key}")

def process_hadith_source(data, source_name, session):
    """
    - Membuat node :Kitab dan :Bab dengan embeddingnya sendiri.
    - Untuk setiap hadis, membuat rantai Chunk: (:Chunk {source:info})->(:Chunk {source:text})->(:Chunk {source:translation})
    - Node info hadis terhubung ke node :Bab.
    """
    # 1. Pastikan Node Puncak :Hadis ada
    session.run("MERGE (:Hadis {name: 'Hadis'})")

    # 2. Buat atau temukan Node :HadithSource
    session.run("""
        MATCH (h_root:Hadis {name: 'Hadis'})
        MERGE (s:HadithSource {name: $source_name})
        MERGE (h_root)-[:HAS_SOURCE]->(s)
    """, source_name=source_name)
    print(f"✅ Node Sumber '{source_name}' berhasil di-MERGE.")

    for kitab_item in data:
        kitab_name = kitab_item['kitab']
        kitab_embedding = embed_chunk(f"Kitab {kitab_name} dari {source_name}")

        # 3. Buat Node :Kitab dengan embedding
        # Kita tidak membuat ini sebagai Chunk agar modelnya bersih
        session.run("""
            MATCH (s:HadithSource {name: $source_name})
            MERGE (k:Kitab {name: $kitab_name, source_name: $source_name})
            SET k.embedding = $embedding
            MERGE (s)-[:HAS_KITAB]->(k)
        """, source_name=source_name, kitab_name=kitab_name, embedding=kitab_embedding)
        print(f"  [+] Kitab '{kitab_name}' dari {source_name} di-MERGE.")

        for bab_item in kitab_item['bab']:
            bab_name = bab_item['bab']
            bab_embedding = embed_chunk(f"Bab tentang '{bab_name}' dalam Kitab {kitab_name}.")

            # 4. Buat Node :Bab dengan embedding
            session.run("""
                MATCH (k:Kitab {name: $kitab_name, source_name: $source_name})
                MERGE (b:Bab {name: $bab_name, kitab_name: $kitab_name, source_name: $source_name})
                SET b.embedding = $embedding
                MERGE (k)-[:HAS_BAB]->(b)
            """, source_name=source_name, kitab_name=kitab_name, bab_name=bab_name, embedding=bab_embedding)

            for hadith_item in bab_item['hadiths']:
                tx = session.begin_transaction()
                try:
                    hadith_number = hadith_item['hadith_number']
                    arabic_text = hadith_item.get('arabic_text', "")
                    translation_text = hadith_item.get('translation', "")

                    # 5. Buat rantai CHUNK untuk setiap Hadis, mirip struktur Al-Quran
                    
                    # 5.1. Buat Chunk 'info'
                    info_id = str(uuid4())
                    info_text = (
                        f"[INFO {source_name} No. {hadith_number}] "
                        f"Konteks hadis dari Kitab {kitab_name}, Bab tentang '{bab_name}'."
                    )
                    info_embedding = embed_chunk(info_text)
                    
                    tx.run("""
                        MATCH (b:Bab {name: $bab_name, kitab_name: $kitab_name, source_name: $source_name})
                        CREATE (c_info:Chunk {
                            id: $id,
                            text: $text,
                            embedding: $embedding,
                            source: 'info',
                            hadith_number: $hadith_number,
                            source_name: $source_name,
                            kitab_name: $kitab_name,
                            bab_name: $bab_name
                        })
                        CREATE (b)-[:CONTAINS_HADITH_CHUNK]->(c_info)
                    """, {
                        "id": info_id, "text": info_text, "embedding": info_embedding,
                        "hadith_number": hadith_number, "source_name": source_name,
                        "kitab_name": kitab_name, "bab_name": bab_name
                    })

                    # 5.2. Buat Chunk 'text' (Arab) dan hubungkan dari 'info'
                    parent_chunk_id = info_id
                    if arabic_text:
                        text_id = str(uuid4())
                        chunk_arab_text = f"[Teks Arab {source_name} No. {hadith_number}]: {arabic_text}"
                        embedding_arab = embed_chunk(chunk_arab_text)
                        
                        tx.run("""
                            MATCH (c_info:Chunk {id: $parent_id})
                            CREATE (c_text:Chunk {
                                id: $id, text: $text, embedding: $embedding, source: 'text',
                                hadith_number: $hadith_number, source_name: $source_name
                            })
                            CREATE (c_info)-[:HAS_CHUNK]->(c_text)
                        """, {
                            "id": text_id, "parent_id": parent_chunk_id,
                            "text": chunk_arab_text, "embedding": embedding_arab,
                            "hadith_number": hadith_number, "source_name": source_name
                        })
                        parent_chunk_id = text_id # Update parent untuk terjemahan

                    # 5.3. Buat Chunk 'translation' dan hubungkan dari 'text'
                    if translation_text:
                        trans_id = str(uuid4())
                        chunk_trans_text = f"[Terjemahan {source_name} No. {hadith_number}]: {translation_text}"
                        embedding_trans = embed_chunk(chunk_trans_text)
                        
                        tx.run("""
                            MATCH (c_parent:Chunk {id: $parent_id})
                            CREATE (c_trans:Chunk {
                                id: $id, text: $text, embedding: $embedding, source: 'translation',
                                hadith_number: $hadith_number, source_name: $source_name
                            })
                            CREATE (c_parent)-[:HAS_CHUNK]->(c_trans)
                        """, {
                            "id": trans_id, "parent_id": parent_chunk_id,
                            "text": chunk_trans_text, "embedding": embedding_trans,
                            "hadith_number": hadith_number, "source_name": source_name
                        })
                    
                    tx.commit()
                except Exception as e:
                    print(f"      ❌ Gagal memproses hadis #{hadith_item.get('hadith_number')}. Rollback. Error: {e}")
                    tx.rollback()

def process_surah_chunks(surah, session):
    # KODE ANDA UNTUK SURAH DI SINI (TIDAK PERLU DIUBAH)
    # ... (biarkan fungsi ini seperti adanya) ...
    from uuid import uuid4
    from process_data.embedding import embed_chunk

    surah_id = int(surah["number"])
    surah_name = surah["name"]
    surah_name_latin = surah["name_latin"]
    number_of_ayah = int(surah["number_of_ayah"])

    # Insert Surah node
    session.run(
        """
        MATCH (q:Quran {name: 'Al-Quran'})
        CREATE (s:Surah {
            number: $number,
            name: $name,
            name_latin: $name_latin,
            number_of_ayah: $number_of_ayah
        })
        CREATE (q)-[:HAS_SURAH]->(s)
        """, {
            "number": surah_id,
            "name": surah_name,
            "name_latin": surah_name_latin,
            "number_of_ayah": number_of_ayah
        }
    )

    for ayah_key, ayah_text in surah["text"].items():
        try:
            ayah_num = extract_ayah_number(ayah_key)
        except ValueError as e:
            print(str(e))
            continue

        translation = surah.get("translations", {}).get("id", {}).get("text", {}).get(ayah_key, "")
        tafsir = surah.get("tafsir", {}).get("id", {}).get("kemenag", {}).get("text", {}).get(ayah_key, "")

        # Insert Ayat node
        session.run(
            """
            MATCH (s:Surah {number: $surah_number})
            CREATE (a:Ayat {
                number: $number,
                text: $text,
                translation: $translation,
                tafsir: $tafsir
            })
            CREATE (s)-[:HAS_AYAT]->(a)
            """, {
                "surah_number": surah_id,
                "number": ayah_num,
                "text": ayah_text,
                "translation": translation,
                "tafsir": tafsir
            }
        )

        # === 1. Chunk Info Surah ===
        info_text = f"[INFO {surah_name_latin}:{ayah_num}] Surah {surah_name_latin} Ayat {ayah_num}"
        info_embedding = embed_chunk(info_text)
        info_id = str(uuid4())

        session.run(
            """
            MATCH (s:Surah {number: $surah_number})-[:HAS_AYAT]->(a:Ayat {number: $ayat_number})
            CREATE (c_info:Chunk {
                id: $id,
                text: $text,
                embedding: $embedding,
                source: 'info',
                ayat_number: $ayat_number,
                surah_name: $surah_name_latin,
                surah_number: $surah_id
            })
            CREATE (a)-[:HAS_CHUNK]->(c_info)
            """, {
                "id": info_id,
                "text": info_text,
                "embedding": info_embedding,
                "ayat_number": ayah_num,
                "surah_number": surah_id
            }
        )
        parent_chunk_id = info_id
        text_id = info_id

        # === 2. Chunk Text ===
        if ayah_text.strip():
            for chunk in chunk_text(ayah_text):
                chunk_text_full = f"[text {surah_name_latin}:{ayah_num}] {chunk}"
                text_embedding = embed_chunk(chunk_text_full)
                text_id = str(uuid4())

                session.run(
                    """
                    MATCH (c_info:Chunk {id: $parent_id})
                    CREATE (c_text:Chunk {
                        id: $id,
                        text: $text,
                        embedding: $embedding,
                        source: 'text',
                        ayat_number: $ayat_number,
                        surah_name: $surah_name_latin,
                        surah_number: $surah_id
                    })
                    CREATE (c_info)-[:HAS_CHUNK]->(c_text)
                    """, {
                        "id": text_id,
                        "parent_id": parent_chunk_id,
                        "text": chunk_text_full,
                        "embedding": text_embedding,
                        "ayat_number": ayah_num,
                        "surah_number": surah_id
                    }
                )
                parent_chunk_id = text_id
        # === 3. Chunk Translation ===
        if translation.strip():
            for t_chunk in chunk_text(translation):
                chunk_trans_full = f"[translation {surah_name_latin}:{ayah_num}] {t_chunk}"
                trans_embedding = embed_chunk(chunk_trans_full)
                trans_id = str(uuid4())

                session.run(
                    """
                    MATCH (c_text:Chunk {id: $parent_id})
                    CREATE (c_trans:Chunk {
                        id: $id,
                        text: $text,
                        embedding: $embedding,
                        source: 'translation',
                        ayat_number: $ayat_number,
                        surah_name: $surah_name_latin,
                        surah_number: $surah_id
                    })
                    CREATE (c_text)-[:HAS_CHUNK]->(c_trans)
                    """, {
                        "id": trans_id,
                        "parent_id": parent_chunk_id,
                        "text": chunk_trans_full,
                        "embedding": trans_embedding,
                        "ayat_number": ayah_num,
                        "surah_number": surah_id
                    }
                )
                parent_chunk_id = trans_id

        # === 4. Chunk Tafsir ===
        if tafsir.strip():
            for taf_chunk in chunk_text(tafsir):
                chunk_taf_full = f"[tafsir {surah_name_latin}:{ayah_num}] {taf_chunk}"
                taf_embedding = embed_chunk(chunk_taf_full)
                taf_id = str(uuid4())

                session.run(
                    """
                    MATCH (c_trans:Chunk {id: $parent_id})
                    CREATE (c_tafsir:Chunk {
                        id: $id,
                        text: $text,
                        embedding: $embedding,
                        source: 'tafsir',
                        ayat_number: $ayat_number,
                        surah_name: $surah_name_latin,
                        surah_number: $surah_id
                    })
                    CREATE (c_trans)-[:HAS_CHUNK]->(c_tafsir)
                    """, {
                        "id": taf_id,
                        "parent_id": parent_chunk_id,
                        "text": chunk_taf_full,
                        "embedding": taf_embedding,
                        "ayat_number": ayah_num,
                        "surah_number": surah_id
                    }
                )