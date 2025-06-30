import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), 'Backend'))

from retrieval.parser import parse_hadith_query
from retrieval.retrieval import keyword_search_hadith_by_number
from retrieval.context_builder import build_chunk_context_interleaved
from retrieval.traversal import get_full_context_from_info

def normalize_id(source_id: str) -> str:
    """Normalize format ID untuk matching yang konsisten"""
    if not source_id:
        return ""
    
    # Remove emoji
    normalized = source_id.replace("📘", "").replace("📖", "").strip()
    
    # Standardize delimiter patterns
    # Convert "No. X | Kitab:" to "No. X Kitab:"
    if " | Kitab:" in normalized:
        normalized = normalized.replace(" | Kitab:", " Kitab:")
    
    # Convert "No. X, Kitab:" to "No. X Kitab:"  
    if ", Kitab:" in normalized:
        normalized = normalized.replace(", Kitab:", " Kitab:")
        
    # Standardize "| Bab:" to "| Bab:"
    if ", Bab:" in normalized:
        normalized = normalized.replace(", Bab:", " | Bab:")
        
    return normalized.strip()

def get_source_from_context_string(context_part: str) -> str | None:
    header_lines = []
    for line in context_part.strip().split('\n'):
        if "Skor Similarity:" in line:
            break
        if line.strip():
            header_lines.append(line.strip())
    return ' '.join(header_lines) if header_lines else None

def run_retrieval_for_query(query: str, history: list = []) -> list[str]:
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
                sumber = f"📘 Hadis {row.get('source_name')} No. {row.get('hadith_number')} Kitab: {row.get('kitab_name', '-')} | Bab: {row.get('bab_name', '-')}"
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

def evaluate_precision_recall(ground_truth_data: list[dict]):
    all_recalls = []
    debug_info = []

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

        # Normalize untuk comparison
        retrieved_set = set(normalize_id(rid) for rid in retrieved_ids)
        expected_set = set(normalize_id(eid) for eid in expected_ids)
        
        true_positives = expected_set.intersection(retrieved_set)

        recall = len(true_positives) / len(expected_set) if expected_set else 0
        all_recalls.append(recall)

        print(f"\n🔍 Query: {query or queries[-1]}")
        print(f"  - Recall: {recall:.4f}")
        print(f"  - True Positives: {len(true_positives)} / {len(expected_set)}")
        
        # Debug info
        if recall < 1.0:
            print(f"  - Retrieved: {retrieved_ids}")
            print(f"  - Expected: {list(expected_ids)}")
            print(f"  - Retrieved (normalized): {list(retrieved_set)}")
            print(f"  - Expected (normalized): {list(expected_set)}")
            print(f"  - Missing: {expected_set - retrieved_set}")

    avg_recall = sum(all_recalls) / len(all_recalls) if all_recalls else 0
    print("\n📊 Rata-rata Recall:")
    print(f"Recall: {avg_recall:.4f}")

if __name__ == "__main__":
    with open('ground_truth_graph.json', 'r', encoding='utf-8') as f:
        ground_truth = json.load(f)

    evaluate_precision_recall(ground_truth)