import json
import re
import os
import sys

# Tambahkan path proyek ke sys.path agar bisa mengimpor dari package 'retrieval'
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# ==============================================================================
# == BAGIAN 1: IMPORT DARI SISTEM RETRIEVAL ANDA                              ==
# ==============================================================================
try:
    from retrieval.parser import parse_hadith_query
    from retrieval.retrieval import keyword_search_hadith_by_number
    from retrieval.context_builder import build_chunk_context_interleaved
    from retrieval.traversal import get_full_context_from_info
except ImportError as e:
    print(f"❌ Gagal mengimpor modul dari package 'retrieval': {e}")
    print("Pastikan skrip ini dijalankan dari root direktori proyek Anda.")
    sys.exit(1)

# ==============================================================================
# == BAGIAN 2: FUNGSI HELPER DAN FUNGSI RETRIEVAL UTAMA                       ==
# ==============================================================================

# =============================================================================
# == FUNGSI INI DIGANTI DENGAN VERSI V2 YANG LEBIH STABIL ==
# =============================================================================
def get_source_from_context_string(context_part: str) -> str | None:
    """Membaca teks baris demi baris untuk menemukan header sumber (Versi 2)."""
    header_lines = []
    # Membaca setiap baris dari potongan konteks
    for line in context_part.strip().split('\n'):
        # Jika bertemu baris "Skor Similarity", hentikan pembacaan header
        if "Skor Similarity:" in line:
            break
        # Jika baris tidak kosong, tambahkan ke header
        if line.strip():
            header_lines.append(line.strip())
    
    # Jika header ditemukan, gabungkan menjadi satu string
    if header_lines:
        return ' '.join(header_lines)
    return None
# =============================================================================

def run_retrieval_for_query(query: str, history: list = []) -> list[str]:
    """
    Menjalankan alur retrieval dan memastikan SEMUA hasil dokumen diproses menjadi daftar.
    """
    print(f"\n---> Menjalankan retrieval untuk query: '{query}'")
    
    combined_query = ""
    for q, a in history:
        combined_query += f"User: {q}\nAssistant: {a}\n"
    combined_query += f"User: {query}"

    hadith_request = parse_hadith_query(query)
    if hadith_request and hadith_request.get("number"):
        info_id = keyword_search_hadith_by_number(hadith_request["number"])
        if info_id:
            row = get_full_context_from_info(info_id)
            if row:
                sumber_text = f"Hadis {row.get('source_name')} No. {row.get('hadith_number')}"
                kitab_text = f"Kitab: {row.get('kitab_name', '-')}"
                bab_text = f"Bab: {row.get('bab_name', '-')}"
                sumber = f"📘 {sumber_text} | {kitab_text} | {bab_text}"
                print(f"✅ Keyword match found: {sumber}")
                return [sumber]

    # Panggil fungsi inti untuk mendapatkan seluruh blok konteks
    context_str = build_chunk_context_interleaved(combined_query, top_k=5, min_score=0.6)

    if not context_str:
        return []

    # Memecah string panjang menjadi daftar bagian-bagian dokumen
    context_parts = context_str.strip().split('---')
    
    retrieved_ids = []
    # Loop ini akan memproses SEMUA bagian di dalam context_parts
    for part in context_parts:
        if part.strip():
            # Memanggil fungsi get_source_from_context_string (versi V2 yang baru)
            source_id = get_source_from_context_string(part)
            if source_id:
                retrieved_ids.append(source_id)
    
    # Return dieksekusi SETELAH loop selesai, sehingga mengembalikan daftar lengkap
    return retrieved_ids

# ==============================================================================
# == BAGIAN 3: KALKULASI MRR (LOGIKA BARU)                                    ==
# ==============================================================================

def calculate_mrr(ground_truth_data: list[dict]):
    """Menghitung Mean Reciprocal Rank (MRR) dengan daftar jawaban yang valid."""
    reciprocal_ranks = []
    
    for item in ground_truth_data:
        query = item.get("query")
        queries = item.get("queries")
        expected_ids = item.get("expected_ids", []) # Ambil daftar jawaban
        
        retrieved_ids = []
        if query:
            retrieved_ids = run_retrieval_for_query(query)
        elif queries:
            print(f"\n---> Menjalankan retrieval MULTITURN")
            chat_history = []
            for i, q in enumerate(queries):
                if i < len(queries) - 1:
                    chat_history.append((q, "jawaban dummy"))
                else:
                    retrieved_ids = run_retrieval_for_query(q, history=chat_history)

        print(f"Hasil retrieval: {retrieved_ids}")
        print(f"Jawaban diharapkan (salah satunya): {expected_ids}")
        
        # --- LOGIKA BARU UNTUK MENEMUKAN RANK ---
        rank = 0
        for i, retrieved_id in enumerate(retrieved_ids):
            # Cek apakah hasil retrieval ada DI DALAM daftar jawaban yang valid
            if retrieved_id in expected_ids:
                rank = i + 1  # Rank adalah index + 1
                break # Hentikan pencarian setelah menemukan yang pertama
        # ----------------------------------------
            
        reciprocal_rank = 1 / rank if rank > 0 else 0
        reciprocal_ranks.append(reciprocal_rank)
        
        print(f"Rank ditemukan: {rank}")
        print(f"Reciprocal Rank (RR) untuk query ini: {reciprocal_rank:.4f}")
        print("-" * 40)

    mrr_score = sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0
    return mrr_score

if __name__ == "__main__":
    print("==============================================")
    print("== Memulai Evaluasi Sistem Retrieval (MRR) ==")
    print("==============================================")
    
    try:
        with open('ground_truth.json', 'r', encoding='utf-8') as f:
            ground_truth = json.load(f)
    except FileNotFoundError:
        print("❌ ERROR: File 'ground_truth.json' tidak ditemukan.")
        sys.exit(1)
        
    mrr_value = calculate_mrr(ground_truth)
    
    print("\n==============================================")
    print("== HASIL AKHIR EVALUASI ==")
    print(f"== Jumlah Query      : {len(ground_truth)}")
    print(f"== Skor MRR Total    : {mrr_value:.4f}")
    print("==============================================")
    print("\nInterpretasi Skor MRR:")
    print("  - Skor mendekati 1.0: Sangat Baik.")
    print("  - Skor di atas 0.8: Baik.")
    print("  - Skor sekitar 0.5 - 0.7: Cukup/Layak.")
    print("  - Skor di bawah 0.5: Perlu Peningkatan.")