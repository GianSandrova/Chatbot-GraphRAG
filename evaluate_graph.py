import json
import re
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), 'Backend'))


# ========================================================================
# == IMPORT DARI SISTEM RETRIEVAL ANDA (PASTIKAN SESUAI STRUKTUR PROYEK) ==
# ========================================================================
try:
    from retrieval.parser import parse_hadith_query
    from retrieval.retrieval import keyword_search_hadith_by_number
    from retrieval.context_builder import build_chunk_context_interleaved
    from retrieval.traversal import get_full_context_from_info
except ImportError as e:
    print(f"❌ Gagal mengimpor modul dari package 'retrieval': {e}")
    print("Pastikan skrip ini dijalankan dari root direktori proyek Anda.")
    sys.exit(1)

# ==========================================================
# == FUNGSI PEMBANTU UNTUK MENGEKSTRAK SUMBER DARI KONTEKS ==
# ==========================================================
def get_source_from_context_string(context_part: str) -> str | None:
    header_lines = []
    for line in context_part.strip().split('\n'):
        if "Skor Similarity:" in line:
            break
        if line.strip():
            header_lines.append(line.strip())
    return ' '.join(header_lines) if header_lines else None

# ===================================================
# == FUNGSI INTI UNTUK MENJALANKAN RETRIEVAL SYSTEM ==
# ===================================================
def run_retrieval_for_query(query: str, history: list = []) -> list[str]:
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

    context_str = build_chunk_context_interleaved(combined_query, top_k=5, min_score=0.6)
    if not context_str:
        return []

    context_parts = context_str.strip().split('---')
    retrieved_ids = []
    for part in context_parts:
        if part.strip():
            source_id = get_source_from_context_string(part)
            if source_id:
                retrieved_ids.append(source_id)
    return retrieved_ids

# ======================================================
# == EVALUASI METRIK: MRR (MEAN RECIPROCAL RANK)      ==
# ======================================================
def calculate_mrr(ground_truth_data: list[dict]):
    reciprocal_ranks = []

    for item in ground_truth_data:
        query = item.get("query")
        queries = item.get("queries")
        expected_ids = item.get("expected_ids", [])

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

        rank = 0
        for i, retrieved_id in enumerate(retrieved_ids):
            if retrieved_id in expected_ids:
                rank = i + 1
                break

        reciprocal_rank = 1 / rank if rank > 0 else 0
        reciprocal_ranks.append(reciprocal_rank)

        print(f"Rank ditemukan: {rank}")
        print(f"Reciprocal Rank (RR): {reciprocal_rank:.4f}")
        print("-" * 40)

    mrr_score = sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0
    return mrr_score

# ======================================================
# == EVALUASI METRIK: PRECISION / RECALL / F1 SCORE   ==
# ======================================================
def evaluate_precision_recall(ground_truth_data: list[dict]):
    all_precisions = []
    all_recalls = []
    all_f1s = []

    for item in ground_truth_data:
        query = item.get("query")
        queries = item.get("queries")
        expected_ids = set(item.get("expected_ids", []))

        retrieved_ids = []
        if query:
            retrieved_ids = run_retrieval_for_query(query)
        elif queries:
            chat_history = []
            for i, q in enumerate(queries):
                if i < len(queries) - 1:
                    chat_history.append((q, "jawaban dummy"))
                else:
                    retrieved_ids = run_retrieval_for_query(q, history=chat_history)

        retrieved_set = set(retrieved_ids)
        true_positives = expected_ids.intersection(retrieved_set)

        precision = len(true_positives) / len(retrieved_set) if retrieved_set else 0
        recall = len(true_positives) / len(expected_ids) if expected_ids else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        all_precisions.append(precision)
        all_recalls.append(recall)
        all_f1s.append(f1)

        print(f"\n📌 Query: {query or queries[-1]}")
        print(f"🔹 Precision: {precision:.4f}")
        print(f"🔹 Recall   : {recall:.4f}")
        print(f"🔹 F1-score : {f1:.4f}")
        print("-" * 30)

    avg_precision = sum(all_precisions) / len(all_precisions) if all_precisions else 0
    avg_recall = sum(all_recalls) / len(all_recalls) if all_recalls else 0
    avg_f1 = sum(all_f1s) / len(all_f1s) if all_f1s else 0

    return avg_precision, avg_recall, avg_f1

# ======================================================
# == ENTRY POINT: MENJALANKAN EVALUASI                ==
# ======================================================
if __name__ == "__main__":
    print("==============================================")
    print("== Memulai Evaluasi Sistem Retrieval ==")
    print("==============================================")

    try:
        with open('ground_truth.json', 'r', encoding='utf-8') as f:
            ground_truth = json.load(f)
    except FileNotFoundError:
        print("❌ ERROR: File 'ground_truth.json' tidak ditemukan.")
        sys.exit(1)

    mrr_value = calculate_mrr(ground_truth)

    print("\n==============================================")
    print("== HASIL AKHIR: METRIK RETRIEVAL ==")
    print(f"== Jumlah Query      : {len(ground_truth)}")
    print(f"== Skor MRR Total    : {mrr_value:.4f}")

    avg_precision, avg_recall, avg_f1 = evaluate_precision_recall(ground_truth)

    print("\n==============================================")
    print("== METRIK PRECISION / RECALL / F1 ==")
    print(f"== Avg Precision     : {avg_precision:.4f}")
    print(f"== Avg Recall        : {avg_recall:.4f}")
    print(f"== Avg F1-score      : {avg_f1:.4f}")
    print("==============================================")

    print("\nInterpretasi Skor MRR:")
    print("  - Skor mendekati 1.0: Sangat Baik.")
    print("  - Skor di atas 0.8 : Baik.")
    print("  - Skor 0.5–0.7     : Layak, tapi bisa ditingkatkan.")
    print("  - Skor < 0.5       : Perlu perbaikan retrieval.")
