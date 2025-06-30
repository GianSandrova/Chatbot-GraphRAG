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
    
    # Remove emoji dan whitespace berlebih
    normalized = source_id.replace("📘", "").replace("📖", "").strip()
    
    # Standardize semua variasi delimiter
    # Pattern 1: "No. X | Kitab:" -> "No. X Kitab:"
    if " | Kitab:" in normalized:
        normalized = normalized.replace(" | Kitab:", " Kitab:")
    
    # Pattern 2: "No. X, Kitab:" -> "No. X Kitab:"  
    if ", Kitab:" in normalized:
        normalized = normalized.replace(", Kitab:", " Kitab:")
    
    # Pattern 3: ", Bab:" -> " | Bab:"
    if ", Bab:" in normalized:
        normalized = normalized.replace(", Bab:", " | Bab:")
    
    # Pattern 4: "| Bab:" -> "| Bab:" (sudah benar)
    
    return normalized.strip()

def get_source_from_context_string(context_part: str) -> str | None:
    """Extract source ID dari context string"""
    header_lines = []
    for line in context_part.strip().split('\n'):
        if "Skor Similarity:" in line:
            break
        if line.strip():
            header_lines.append(line.strip())
    return ' '.join(header_lines) if header_lines else None

def evaluate_traversal_quality(ground_truth_data: list[dict]):
    """
    Evaluasi khusus untuk traversal:
    - Mengabaikan hasil retrieval yang salah
    - Fokus apakah traversal bisa menghasilkan expected chunks
    """
    results = []
    
    for item in ground_truth_data:
        query = item.get("query")
        expected_chunks = item.get("expected_chunks", [])
        
        print(f"\n🔍 Query: {query}")
        
        # Jalankan retrieval + traversal
        context_str = build_chunk_context_interleaved(query, top_k=10, min_score=0.5)
        
        if not context_str:
            print("  ❌ Tidak ada context yang ditemukan")
            results.append({
                "query": query,
                "success_rate": 0.0,
                "found_chunks": [],
                "missing_chunks": expected_chunks
            })
            continue
        
        # Parse hasil context
        context_parts = context_str.strip().split('---')
        retrieved_sources = []
        
        for part in context_parts:
            if part.strip():
                source_id = get_source_from_context_string(part)
                if source_id:
                    retrieved_sources.append(source_id)
        
        # Normalize untuk comparison
        retrieved_normalized = set(normalize_id(source) for source in retrieved_sources)
        
        # Check setiap expected chunk
        found_chunks = []
        missing_chunks = []
        
        for expected_chunk in expected_chunks:
            chunk_id = expected_chunk.get("chunk_id", "")
            expected_normalized = normalize_id(chunk_id)
            
            if expected_normalized in retrieved_normalized:
                found_chunks.append(expected_chunk)
                print(f"  ✅ Found: {chunk_id}")
            else:
                missing_chunks.append(expected_chunk)
                print(f"  ❌ Missing: {chunk_id}")
        
        success_rate = len(found_chunks) / len(expected_chunks) if expected_chunks else 0
        
        print(f"  📊 Traversal Success Rate: {success_rate:.2%}")
        print(f"     Found: {len(found_chunks)} / {len(expected_chunks)}")
        
        # Debug info jika ada yang missing
        if missing_chunks:
            print(f"  🔍 Debug - Retrieved sources:")
            for source in retrieved_sources:
                print(f"     - {source}")
            print(f"  🔍 Debug - Retrieved normalized:")
            for norm in retrieved_normalized:
                print(f"     - {norm}")
            print(f"  🔍 Debug - Expected normalized:")
            for expected_chunk in expected_chunks:
                norm = normalize_id(expected_chunk.get("chunk_id", ""))
                print(f"     - {norm}")
        
        results.append({
            "query": query,
            "success_rate": success_rate,
            "found_chunks": found_chunks,
            "missing_chunks": missing_chunks
        })
    
    # Summary
    overall_success = sum(r["success_rate"] for r in results) / len(results) if results else 0
    print(f"\n📊 HASIL EVALUASI TRAVERSAL:")
    print(f"Overall Success Rate: {overall_success:.2%}")
    
    return results

def evaluate_specific_chunk_requirements(ground_truth_data: list[dict]):
    """
    Evaluasi lebih detail untuk memastikan chunk memenuhi syarat 'must_have'
    """
    print("\n🔍 EVALUASI DETAIL CHUNK REQUIREMENTS:")
    
    for item in ground_truth_data:
        query = item.get("query")
        expected_chunks = item.get("expected_chunks", [])
        
        print(f"\n Query: {query}")
        
        for expected_chunk in expected_chunks:
            chunk_id = expected_chunk.get("chunk_id")
            should_resolve_to_info = expected_chunk.get("should_resolve_to_info", False)
            must_have = expected_chunk.get("must_have", [])
            context_info = expected_chunk.get("context", {})
            
            print(f"  Chunk: {chunk_id}")
            print(f"    Should resolve to info: {should_resolve_to_info}")
            print(f"    Must have: {must_have}")
            print(f"    Context: {context_info}")
            
            # TODO: Implementasi pengecekan apakah chunk benar-benar memiliki
            # komponen yang dibutuhkan (info_text, text_text, translation_text)
            # Ini memerlukan akses ke database atau hasil traversal yang detail

if __name__ == "__main__":
    # Load ground truth
    with open('ground_truth_graph.json', 'r', encoding='utf-8') as f:
        ground_truth = json.load(f)
    
    # Evaluasi traversal
    results = evaluate_traversal_quality(ground_truth)
    
    # Evaluasi detail (opsional)
    # evaluate_specific_chunk_requirements(ground_truth)