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
    
    # Standardize berbagai variasi format
    # Handle "Hadis X No. Y | Kitab: Z, Bab: W" -> "Hadis X No. Y Kitab: Z | Bab: W"
    if " | Kitab:" in normalized:
        normalized = normalized.replace(" | Kitab:", " Kitab:")
    
    # Handle "Hadis X No. Y, Kitab: Z | Bab: W" -> "Hadis X No. Y Kitab: Z | Bab: W"  
    if ", Kitab:" in normalized:
        normalized = normalized.replace(", Kitab:", " Kitab:")
    
    # Handle ", Bab:" -> " | Bab:"
    if ", Bab:" in normalized:
        normalized = normalized.replace(", Bab:", " | Bab:")
    
    # Handle case untuk Surah (jika ada format aneh)
    # "Surah: X | Ayat: Y" -> "Surah: X | Ayat: Y" (keep as is)
    
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
        
        # Handle both old format (expected_ids) and new format (expected_chunks)
        expected_chunks = item.get("expected_chunks", [])
        if not expected_chunks and "expected_ids" in item:
            # Convert old format to new format for compatibility
            expected_chunks = [{"chunk_id": chunk_id} for chunk_id in item["expected_ids"]]
        
        print(f"\n🔍 Query: {query}")
        print(f"  Expected chunks count: {len(expected_chunks)}")
        
        # Debug: Print expected chunks
        for i, chunk in enumerate(expected_chunks):
            chunk_id = chunk.get("chunk_id", "")
            print(f"    {i+1}. {chunk_id}")
        
        # Jalankan retrieval + traversal
        context_str = build_chunk_context_interleaved(query, top_k=5, min_score=0.5)
        
        if not context_str:
            print("  ❌ Tidak ada context yang ditemukan")
            results.append({
                "query": query,
                "success_rate": 0.0,
                "found_chunks": [],
                "missing_chunks": expected_chunks
            })
            continue
        
        # Parse hasil context - lebih robust parsing
        retrieved_sources = []
        
        # Method 1: Split by "---"
        context_parts = context_str.strip().split('---')
        for part in context_parts:
            if part.strip():
                source_id = get_source_from_context_string(part)
                if source_id:
                    retrieved_sources.append(source_id)
        
        # Method 2: Parse dari debug output jika ada
        lines = context_str.split('\n')
        for line in lines:
            if "Konteks utama ditemukan →" in line:
                # Extract source dari line seperti: "Konteks utama ditemukan → Hadis Jami` at-Tirmidzi No. 1376 | Kitab: Hukum Hudud, Bab: Hukuman liwath (homoseksual)"
                source = line.split("→")[-1].strip()
                if source and source not in retrieved_sources:
                    retrieved_sources.append(source)
        
        print(f"  Retrieved sources count: {len(retrieved_sources)}")
        for i, source in enumerate(retrieved_sources):
            print(f"    {i+1}. {source}")
        
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
        
        # Debug info detail
        if missing_chunks or success_rate < 1.0:
            print(f"  🔍 Debug - Retrieved normalized:")
            for norm in sorted(retrieved_normalized):
                print(f"     - '{norm}'")
            print(f"  🔍 Debug - Expected normalized:")
            for expected_chunk in expected_chunks:
                norm = normalize_id(expected_chunk.get("chunk_id", ""))
                print(f"     - '{norm}'")
            
            # Check exact matches
            print(f"  🔍 Debug - Exact match check:")
            for expected_chunk in expected_chunks:
                expected_norm = normalize_id(expected_chunk.get("chunk_id", ""))
                matches = [r for r in retrieved_normalized if r == expected_norm]
                if matches:
                    print(f"     ✅ '{expected_norm}' -> Found")
                else:
                    print(f"     ❌ '{expected_norm}' -> Not found")
                    # Check closest matches
                    closest = [r for r in retrieved_normalized if expected_norm.lower() in r.lower() or r.lower() in expected_norm.lower()]
                    if closest:
                        print(f"        🔍 Possible matches: {closest}")
        
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
    # Test normalisasi dulu
    print("🔧 Testing normalisasi:")
    test_cases = [
        "📘 Hadis Jami` at-Tirmidzi No. 1376 Kitab: Hukum Hudud | Bab: Hukuman liwath (homoseksual)",
        "Hadis Jami` at-Tirmidzi No. 1376 | Kitab: Hukum Hudud, Bab: Hukuman liwath (homoseksual)",
        "📖 Surah: An-Nisa' | Ayat: 16",
        "Surah: An-Nur | Ayat: 2"
    ]
    
    for case in test_cases:
        normalized = normalize_id(case)
        print(f"  '{case}' -> '{normalized}'")
    
    print("\n" + "="*50)
    
    # Load ground truth
    with open('ground_truth_graph.json', 'r', encoding='utf-8') as f:
        ground_truth = json.load(f)
    
    # Print structure ground truth untuk debug
    print("🔧 Ground truth structure:")
    for i, item in enumerate(ground_truth[:2]):  # Just first 2 items
        print(f"  Item {i}:")
        print(f"    query: {item.get('query', 'N/A')}")
        print(f"    has expected_chunks: {'expected_chunks' in item}")
        print(f"    has expected_ids: {'expected_ids' in item}")
        if 'expected_chunks' in item:
            print(f"    expected_chunks count: {len(item['expected_chunks'])}")
            for j, chunk in enumerate(item['expected_chunks'][:2]):
                print(f"      {j}: {chunk.get('chunk_id', 'N/A')}")
        if 'expected_ids' in item:
            print(f"    expected_ids: {item['expected_ids']}")
    
    print("\n" + "="*50)
    
    # Evaluasi traversal
    results = evaluate_traversal_quality(ground_truth)
    
    # Evaluasi detail (opsional)
    # evaluate_specific_chunk_requirements(ground_truth)