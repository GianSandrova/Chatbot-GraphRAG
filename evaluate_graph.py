import json
import re
import os
import sys
from typing import Dict, List, Set, Tuple, Any


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'Backend')))

# ==============================================================================
# == BAGIAN 1: IMPORT DARI SISTEM RETRIEVAL ANDA                             ==
# ==============================================================================
try:
    from retrieval.context_builder import build_chunk_context_interleaved
except ImportError as e:
    print(f"❌ Gagal mengimpor modul 'build_chunk_context_interleaved': {e}")
    sys.exit(1)

# ==============================================================================
# == BAGIAN 2: FUNGSI HELPER DAN FUNGSI RETRIEVAL UTAMA                      ==
# ==============================================================================

def extract_retrieval_results(context_str: str) -> Dict[str, Any]:
    """
    (VERSI BARU) Mengekstrak main_id dan coverage_ids dari string konteks mentah.
    Fungsi ini sekarang lebih cerdas dan tidak bergantung pada baris log "Konteks utama ditemukan".
    """
    if not context_str:
        return {"main_id": None, "coverage_ids": set()}

    # 1. Ekstrak semua ID cakupan dari seluruh konteks terlebih dahulu
    all_coverage_ids = set(re.findall(r'\[\w+\s+[^\]]+\]', context_str))

    # 2. Simpulkan ID Utama dari chunk pertama (paling relevan)
    main_id = None
    first_chunk = context_str.split('---')[0]
    
    # Cari ID semantik pertama di dalam chunk pertama
    first_id_match = re.search(r'\[\w+\s+(.*?)(?:\sNo\.)?:\s*(\d+)\]', first_chunk)
    
    if first_id_match:
        source_name = first_id_match.group(1).replace("Shahih ", "").strip()
        number = first_id_match.group(2)
        # Konversi ke format MRR ID. Ini adalah asumsi berdasarkan pola umum.
        # Anda mungkin perlu menyesuaikannya jika formatnya berbeda.
        if "Bukhari" in source_name or "Tirmidzi" in source_name:
             # Placeholder untuk nama kitab dan bab karena tidak ada di ID
            main_id = f"Hadis {source_name} No. {number} | Kitab: ... | Bab: ..."
            # NOTE: Karena info Kitab/Bab tidak ada di ID, perbandingan MRR mungkin
            # memerlukan penyesuaian. Cara paling mudah adalah menyederhanakan MRR ID
            # di ground truth menjadi "Hadis Shahih Bukhari No. 7", dll.
            # Untuk sekarang, kita fokus membuat ini tidak None.
            # Alternatif paling sederhana:
            main_id = f"Hadis {source_name} No. {number}"
        else: # Asumsi ini untuk Surah
            main_id = f"Surah: {source_name} | Ayat: {number}"

    # Jika parsing gagal, coba metode lama sebagai fallback (walaupun kemungkinan gagal)
    if not main_id:
        old_main_id_match = re.search(r"Konteks utama ditemukan → (.*?)(?: \| Kitab:.*)?\n", context_str)
        if old_main_id_match:
            main_id = old_main_id_match.group(1).strip()

    return {"main_id": main_id, "coverage_ids": all_coverage_ids}

def run_full_retrieval(query: str) -> Dict[str, Any]:
    """
    Menjalankan alur retrieval dan mengembalikan DICTIONARY yang berisi
    main_id (untuk MRR) dan coverage_ids (untuk Graph Coverage).
    """
    print(f"\n---> Menjalankan retrieval untuk query: '{query}'")
    
    # Panggil fungsi inti untuk mendapatkan seluruh blok konteks
    context_str = build_chunk_context_interleaved(query, top_k=5, min_score=0.6)

    # Ekstrak hasilnya menggunakan fungsi helper baru
    return extract_retrieval_results(context_str)

# ==============================================================================
# == BAGIAN 3: KALKULASI METRIK GABUNGAN (MRR & COVERAGE)                    ==
# ==============================================================================

def calculate_combined_metrics(ground_truth_data: List[Dict]):
    """
    Menghitung MRR dan metrik Graph Coverage (Recall, Precision, F1) secara bersyarat.
    """
    mrr_scores = []
    # Inisialisasi list untuk skor coverage yang valid (tidak di-skip)
    valid_recalls = []
    valid_precisions = []
    valid_f1s = []
    
    for i, item in enumerate(ground_truth_data):
        query = item["query"]
        retrieval_result = run_full_retrieval(query)
        retrieved_main_id = retrieval_result["main_id"]
        retrieved_coverage_ids = retrieval_result["coverage_ids"]

        print(f"Hasil Retrieval Utama: {retrieved_main_id}")

        # Inisialisasi default
        rank = 0
        target_coverage_ids = set()
        is_mrr_hit = False

        # --- LOGIKA BARU UNTUK MENDUKUNG DUA JENIS GROUND TRUTH ---
        if "valid_retrievals" in item:  # Tipe Multi-Answer
            print("Tipe Ground Truth: Multi-Answer")
            # Cek apakah hasil retrieval cocok dengan salah satu jawaban valid
            for valid_answer in item["valid_retrievals"]:
                if retrieved_main_id == valid_answer["mrr_id"]:
                    rank = 1  # Asumsi top-1 hit
                    is_mrr_hit = True
                    target_coverage_ids = set(valid_answer["coverage_ids"])
                    print(f"✅ MRR Hit (Multi-Answer): Cocok dengan '{valid_answer['mrr_id']}'")
                    break
        else:  # Tipe Single-Answer
            print("Tipe Ground Truth: Single-Answer")
            expected_mrr_id = item.get("expected_mrr_id")
            if retrieved_main_id == expected_mrr_id:
                rank = 1
                is_mrr_hit = True
                target_coverage_ids = set(item.get("expected_graph_coverage_ids", []))
                print(f"✅ MRR Hit (Single-Answer): Cocok dengan '{expected_mrr_id}'")

        # --- KALKULASI SKOR ---
        reciprocal_rank = 1 / rank if rank > 0 else 0
        mrr_scores.append(reciprocal_rank)
        
        if not is_mrr_hit:
            print("❌ MRR Miss.")

        # --- EVALUASI COVERAGE SECARA BERSYARAT ---
        if is_mrr_hit:
            print("↳ Melanjutkan ke evaluasi Graph Coverage...")
            print(f"  - Diharapkan ({len(target_coverage_ids)}): {list(target_coverage_ids)}")
            print(f"  - Diambil ({len(retrieved_coverage_ids)}): {list(retrieved_coverage_ids)}")
            
            true_positives = len(retrieved_coverage_ids.intersection(target_coverage_ids))
            
            recall = true_positives / len(target_coverage_ids) if len(target_coverage_ids) > 0 else 0
            precision = true_positives / len(retrieved_coverage_ids) if len(retrieved_coverage_ids) > 0 else 0
            f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            valid_recalls.append(recall)
            valid_precisions.append(precision)
            valid_f1s.append(f1_score)
            
            print(f"  ↳ Skor Coverage -> Recall: {recall:.2f}, Precision: {precision:.2f}, F1: {f1_score:.2f}")
        else:
            print("↳ Melewati evaluasi Graph Coverage karena MRR Miss.")
        
        print("-" * 50)

    # Hitung rata-rata akhir
    avg_mrr = sum(mrr_scores) / len(mrr_scores) if mrr_scores else 0
    avg_recall = sum(valid_recalls) / len(valid_recalls) if valid_recalls else 0
    avg_precision = sum(valid_precisions) / len(valid_precisions) if valid_precisions else 0
    avg_f1 = sum(valid_f1s) / len(valid_f1s) if valid_f1s else 0
    
    return {
        "avg_mrr": avg_mrr,
        "avg_recall": avg_recall,
        "avg_precision": avg_precision,
        "avg_f1": avg_f1,
        "coverage_evaluated_count": len(valid_recalls)
    }

if __name__ == "__main__":
    GT_FILE = 'ground_truth_coverage.json' # Pastikan nama file sesuai
    print("=" * 50)
    print("== Memulai Evaluasi Gabungan (MRR & Graph Coverage) ==")
    print("=" * 50)
    
    try:
        with open(GT_FILE, 'r', encoding='utf-8') as f:
            ground_truth = json.load(f)
    except FileNotFoundError:
        print(f"❌ ERROR: File '{GT_FILE}' tidak ditemukan.")
        sys.exit(1)
        
    results = calculate_combined_metrics(ground_truth)
    
    print("\n" + "=" * 50)
    print("== HASIL AKHIR EVALUASI ==")
    total_queries = len(ground_truth)
    coverage_count = results['coverage_evaluated_count']
    print(f"== Jumlah Query Total         : {total_queries}")
    print(f"== Skor MRR Rata-rata         : {results['avg_mrr']:.4f}")
    print("-" * 50)
    print(f"== Evaluasi Coverage Dilakukan  : {coverage_count} dari {total_queries} query ({coverage_count/total_queries:.1%})")
    print(f"== Rata-rata Recall           : {results['avg_recall']:.4f}")
    print("=" * 50)