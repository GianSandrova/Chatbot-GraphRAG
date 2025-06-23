# retrieval/context_builder.py

from retrieval.retrieval import vector_search_chunks_generator
from retrieval.traversal import find_info_chunk_id, get_full_context_from_info, get_neighboring_hadiths_in_bab

NEIGHBOR_LIMIT = 2

def build_chunk_context_interleaved(query_text, top_k=5, min_score=0.6):
    context = ""
    visited_info_ids = set()

    for record in vector_search_chunks_generator(query_text, top_k=top_k*3, min_score=min_score):
        if len(visited_info_ids) >= top_k:
            break

        try:
            # --- [MODIFIKASI 1] ---
            # Ambil detail dari chunk yang kena vector search (bukan info chunk)
            hit_node = record["node"]
            chunk_id = hit_node.element_id
            chunk_type = hit_node.get("source", "tidak diketahui") # cth: 'translation', 'tafsir', 'info'
            similarity = record["score"]
        except Exception as e:
            print(f"❌ Gagal memproses record: {e}")
            continue

        # --- [MODIFIKASI 2] ---
        # Log pertama: Tunjukkan chunk mana yang menjadi titik awal (kena vector search)
        print(f"🎯 Vector hit pada chunk '{chunk_type}' (ID: {chunk_id}) | Skor: {similarity:.4f}")

        # Traversal KE ATAS dari chunk yang kena (cth: dari 'translation' ke 'info')
        info_id = find_info_chunk_id(chunk_id)
        if not info_id:
            print(f"   ⚠️  Gagal traversal ke root 'info' dari chunk ID={chunk_id}")
            continue
        
        # Log kedua: Tunjukkan hasil traversal ke root 'info'
        print(f"   ⤴️  Traversal ke root info ID={info_id}")

        if info_id in visited_info_ids:
            print(f"   ℹ️  Info ID={info_id} sudah diproses, lanjut.")
            continue
        
        visited_info_ids.add(info_id)

        # Traversal KE BAWAH dari 'info' untuk mengambil konteks lengkap
        row = get_full_context_from_info(info_id)
        if not row:
            continue

        sumber = "❓ Sumber tidak diketahui"
        is_hadith = False
        if row.get("surah_name") and row.get("ayat_number"):
            sumber = f"📖 Surah: {row.get('surah_name')} | Ayat: {row.get('ayat_number')}"
        elif row.get("source_name") and row.get("hadith_number"):
            is_hadith = True
            sumber = (f"📘 Hadis {row.get('source_name')} No. {row.get('hadith_number')}\n"
                      f"Kitab: {row.get('kitab_name', '-')} | Bab: {row.get('bab_name', '-')}")

        # Log ketiga: Tunjukkan sumber konteks yang berhasil dibangun dari 'info' chunk
        sumber_formatted = sumber.replace('\n', ' ')
        print(f"   ✅ Konteks dibangun: {sumber_formatted}")

        # Tambahkan konteks utama ke hasil akhir
        context += f"""
{sumber}
Skor Similarity: {similarity:.4f}
➤ Info: {row.get('info_text') or '-'}
➤ Teks Arab: {row.get('text_text') or '-'}
➤ Terjemahan: {row.get('translation_text') or '-'}
➤ Tafsir: {row.get('tafsir_text') or '-'}
---
"""
        # Logika traversal hadis tetangga (tetap sama)
        if is_hadith:
            print(f"   ➡️  Melakukan traversal untuk hadis tetangga di Bab: '{row.get('bab_name')}'")
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
                
                neighbor_sumber = (f"📘 Hadis {neighbor_row.get('source_name')} No. {neighbor_row.get('hadith_number')}\n"
                                   f"Kitab: {neighbor_row.get('kitab_name', '-')} | Bab: {neighbor_row.get('bab_name', '-')}")
                
                # LOGGING BARU UNTUK TRAVERSAL
                print(f"      ↪️  Konteks tambahan dari traversal ID={neighbor_info_id}")
                neighbor_sumber_formatted = neighbor_sumber.replace('\n', ' ')
                print(f"         ✅ Konteks dibangun: {neighbor_sumber_formatted}")

                # Tambahkan konteks tetangga ke hasil akhir
                context += f"""
{neighbor_sumber}
Skor Similarity: N/A (Traversal)
➤ Info: {neighbor_row.get('info_text') or '-'}
➤ Teks Arab: {neighbor_row.get('text_text') or '-'}
➤ Terjemahan: {neighbor_row.get('translation_text') or '-'}
➤ Tafsir: {neighbor_row.get('tafsir_text') or '-'}
---
"""
    return context