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
    # Handle "Hadis X No. Y | Kitab: Z, Bab: W" -> "Hadis X No. Y"
    if " | Kitab:" in normalized or " Kitab:" in normalized:
        # Extract hanya sampai nomor hadis
        if "Hadis" in normalized and "No." in normalized:
            parts = normalized.split("No.")
            if len(parts) >= 2:
                hadis_part = parts[0].strip() + " No." + parts[1].split()[0]
                normalized = hadis_part.strip()
    
    # Handle ", Kitab:" -> extract only the main part
    if ", Kitab:" in normalized:
        normalized = normalized.split(", Kitab:")[0].strip()
    
    # Handle Surah format - extract main identifier
    if "Surah:" in normalized and "Ayat:" in normalized:
        # Keep format "Surah: X | Ayat: Y"
        pass
    
    return normalized.strip()

def extract_base_identifier(full_source: str) -> str:
    """Extract base identifier for matching"""
    normalized = normalize_id(full_source)
    
    # For Hadis, extract just "Hadis [Collection] No. [Number]"
    if "Hadis" in normalized and "No." in normalized:
        # Extract collection and number
        if "Jami` at-Tirmidzi" in normalized:
            import re
            match = re.search(r'Hadis Jami` at-Tirmidzi No\. (\d+)', normalized)
            if match:
                return f"Hadis Jami` at-Tirmidzi No. {match.group(1)}"
    
    # For Quran, keep as is
    if "Surah:" in normalized:
        return normalized
    
    return normalized

def get_source_from_context_string(context_part: str) -> str | None:
    """Extract source ID dari context string"""
    header_lines = []
    for line in context_part.strip().split('\n'):
        if "Skor Similarity:" in line:
            break
        if line.strip():
            header_lines.append(line.strip())
    return ' '.join(header_lines) if header_lines else None

def convert_ground_truth_format(ground_truth_data: list[dict]) -> list[dict]:
    """Convert ground truth dari format lama ke format baru"""
    converted = []
    
    for item in ground_truth_data:
        query = item.get("query")
        expected_answers = item.get("expected_answers", [])
        
        # Convert expected_answers to expected_chunks format
        expected_chunks = []
        for answer in expected_answers:
            chunk_id = answer.get("id", "")
            must_have = answer.get("must_have", [])
            context = answer.get("context", {})
            
            expected_chunks.append({
                "chunk_id": chunk_id,
                "must_have": must_have,
                "context": context
            })
        
        converted.append({
            "query": query,
            "expected_chunks": expected_chunks,
            "category": item.get("category", "")
        })
    
    return converted

def evaluate_traversal_quality(ground_truth_data: list[dict]):
    """
    Evaluasi khusus untuk traversal:
    - Mengabaikan hasil retrieval yang salah
    - Fokus apakah traversal bisa menghasilkan expected chunks
    """
    # Convert format jika perlu
    if ground_truth_data and "expected_answers" in ground_truth_data[0]:
        ground_truth_data = convert_ground_truth_format(ground_truth_data)
    
    results = []
    
    for item in ground_truth_data:
        query = item.get("query")
        expected_chunks = item.get("expected_chunks", [])
        
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
        
        # Method: Parse dari debug output
        lines = context_str.split('\n')
        for line in lines:
            if "Konteks utama ditemukan →" in line:
                # Extract source dari line seperti: "Konteks utama ditemukan → Hadis Jami` at-Tirmidzi No. 1376 | Kitab: Hukum Hudud, Bab: Hukuman liwath (homoseksual)"
                source = line.split("→")[-1].strip()
                if source and source not in retrieved_sources:
                    retrieved_sources.append(source)
            elif "Tambahan konteks:" in line:
                # Handle additional context sources
                source = line.split(":")[-1].strip()
                if source and source not in retrieved_sources:
                    retrieved_sources.append(source)
        
        print(f"  Retrieved sources count: {len(retrieved_sources)}")
        for i, source in enumerate(retrieved_sources):
            print(f"    {i+1}. {source}")
        
        # Extract base identifiers untuk matching
        retrieved_base_ids = set()
        for source in retrieved_sources:
            base_id = extract_base_identifier(source)
            retrieved_base_ids.add(base_id)
        
        # Check setiap expected chunk
        found_chunks = []
        missing_chunks = []
        
        for expected_chunk in expected_chunks:
            chunk_id = expected_chunk.get("chunk_id", "")
            expected_base_id = extract_base_identifier(chunk_id)
            
            # Check exact match atau partial match untuk base identifier
            found = False
            for retrieved_base in retrieved_base_ids:
                if expected_base_id == retrieved_base:
                    found = True
                    break
                # Fallback: check if base identifier is contained
                elif expected_base_id in retrieved_base or retrieved_base in expected_base_id:
                    # Additional check untuk memastikan ini bukan false positive
                    if "Hadis" in expected_base_id and "Hadis" in retrieved_base:
                        # Extract numbers untuk hadis comparison
                        import re
                        exp_num = re.search(r'No\. (\d+)', expected_base_id)
                        ret_num = re.search(r'No\. (\d+)', retrieved_base)
                        if exp_num and ret_num and exp_num.group(1) == ret_num.group(1):
                            found = True
                            break
                    elif "Surah:" in expected_base_id and "Surah:" in retrieved_base:
                        found = True
                        break
            
            if found:
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
            print(f"  🔍 Debug - Retrieved base IDs:")
            for base_id in sorted(retrieved_base_ids):
                print(f"     - '{base_id}'")
            print(f"  🔍 Debug - Expected base IDs:")
            for expected_chunk in expected_chunks:
                base_id = extract_base_identifier(expected_chunk.get("chunk_id", ""))
                print(f"     - '{base_id}'")
            
            # Check exact matches
            print(f"  🔍 Debug - Match analysis:")
            for expected_chunk in expected_chunks:
                expected_base = extract_base_identifier(expected_chunk.get("chunk_id", ""))
                matches = [r for r in retrieved_base_ids if r == expected_base]
                if matches:
                    print(f"     ✅ '{expected_base}' -> Found exact match: {matches[0]}")
                else:
                    print(f"     ❌ '{expected_base}' -> Not found")
                    # Check partial matches
                    partial = [r for r in retrieved_base_ids if expected_base in r or r in expected_base]
                    if partial:
                        print(f"        🔍 Partial matches: {partial}")
        
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
        base_id = extract_base_identifier(case)
        print(f"  '{case}' -> '{base_id}'")
    
    print("\n" + "="*50)
    
    # Load ground truth
    with open('ground_truth_graph.json', 'r', encoding='utf-8') as f:
        ground_truth = json.load(f)
    
    # Print structure ground truth untuk debug
    print("🔧 Ground truth structure:")
    for i, item in enumerate(ground_truth[:1]):  # Just first item
        print(f"  Item {i}:")
        print(f"    query: {item.get('query', 'N/A')}")
        print(f"    has expected_chunks: {'expected_chunks' in item}")
        print(f"    has expected_answers: {'expected_answers' in item}")
        if 'expected_answers' in item:
            print(f"    expected_answers count: {len(item['expected_answers'])}")
            for j, answer in enumerate(item['expected_answers']):
                print(f"      {j}: {answer.get('id', 'N/A')}")
    
    print("\n" + "="*50)
    
    # Evaluasi traversal
    results = evaluate_traversal_quality(ground_truth)