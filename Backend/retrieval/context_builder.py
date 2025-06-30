from retrieval.retrieval import vector_search_chunks_generator
from retrieval.traversal import find_info_chunk_id, get_full_context_from_info, get_neighboring_hadiths_in_bab

NEIGHBOR_LIMIT = 2

def preview(text, max_len=80):
    return (text[:max_len] + "...") if text and len(text) > max_len else (text or "-")

def build_chunk_context_interleaved(query_text, top_k=5, min_score=0.6):
    context = ""
    visited_info_ids = set()

    for record in vector_search_chunks_generator(query_text, top_k=top_k*3, min_score=min_score):
        if len(visited_info_ids) >= top_k:
            break

        try:
            hit_node = record["node"]
            chunk_id = hit_node.element_id
            chunk_type = hit_node.get("source", "tidak diketahui")
            similarity = record["score"]
        except Exception as e:
            print(f"  Gagal memproses record: {e}")
            continue

        print(f"\n🎯 Vector hit → Chunk '{chunk_type}' (ID: {chunk_id}) | Skor: {similarity:.4f}")

        info_id = find_info_chunk_id(chunk_id)
        if not info_id:
            print(f"   Tidak bisa temukan info root dari chunk ID={chunk_id}")
            continue

        print(f"   → Traversal ke info ID={info_id}")

        if info_id in visited_info_ids:
            print(f"   Info ID={info_id} sudah diproses.")
            continue
        visited_info_ids.add(info_id)

        row = get_full_context_from_info(info_id)
        if not row:
            continue

        is_hadith = False
        if row.get("surah_name") and row.get("ayat_number"):
            sumber = f"Surah: {row.get('surah_name')} | Ayat: {row.get('ayat_number')}"
        elif row.get("source_name") and row.get("hadith_number"):
            is_hadith = True
            sumber = (f"Hadis {row.get('source_name')} No. {row.get('hadith_number')} | "
                      f"Kitab: {row.get('kitab_name', '-')}, Bab: {row.get('bab_name', '-')}")

        print(f"   Konteks utama ditemukan → {sumber}")
        print("   Potongan isi:")
        print(f"      Info       : {preview(row.get('info_text'))}")
        print(f"      Teks Arab  : {preview(row.get('text_text'))}")
        print(f"      Terjemahan : {preview(row.get('translation_text'))}")
        if not is_hadith:
            print(f"      Tafsir     : {preview(row.get('tafsir_text'))}")

        context += f"""\n{sumber}
Skor Similarity: {similarity:.4f}
➤ Info: {row.get('info_text') or '-'}
➤ Teks Arab: {row.get('text_text') or '-'}
➤ Terjemahan: {row.get('translation_text') or '-'}
"""
        if not is_hadith:
            context += f"➤ Tafsir: {row.get('tafsir_text') or '-'}\n"
        context += "---\n"

        if is_hadith:
            print(f"   ➡️ Mencari hadis tetangga dari Bab '{row.get('bab_name')}'")
            neighbor_ids = get_neighboring_hadiths_in_bab(
                bab_name=row.get('bab_name'),
                kitab_name=row.get('kitab_name'),
                source_name=row.get('source_name'),
                exclude_hadith_number=row.get('hadith_number'),
                limit=NEIGHBOR_LIMIT
            )

            for neighbor_info_id in neighbor_ids:
                if len(visited_info_ids) >= top_k: break
                if neighbor_info_id in visited_info_ids: continue

                neighbor_row = get_full_context_from_info(neighbor_info_id)
                if not neighbor_row: continue

                visited_info_ids.add(neighbor_info_id)

                neighbor_sumber = (f"Hadis {neighbor_row.get('source_name')} No. {neighbor_row.get('hadith_number')} | "
                                   f"Kitab: {neighbor_row.get('kitab_name', '-')}, Bab: {neighbor_row.get('bab_name', '-')}")

                print(f"      ↪️  Tambahan konteks: {neighbor_sumber}")
                print(f"         Info: {preview(neighbor_row.get('info_text'))}")

                context += f"""\n{neighbor_sumber}
Skor Similarity: N/A (Tetangga)
➤ Info: {neighbor_row.get('info_text') or '-'}
➤ Teks Arab: {neighbor_row.get('text_text') or '-'}
➤ Terjemahan: {neighbor_row.get('translation_text') or '-'}
---\n"""
    return context
