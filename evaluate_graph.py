import json
import os
import sys
import re

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
            match = re.search(r'Hadis Jami` at-Tirmidzi No\.?\s*(\d+)', normalized)
            if match:
                return f"Hadis Jami` at-Tirmidzi No. {match.group(1)}"
        
        # Generic hadis pattern
        match = re.search(r'Hadis ([^N]+) No\.?\s*(\d+)', normalized)
        if match:
            collection = match.group(1).strip()
            number = match.group(2)
            return f"Hadis {collection} No. {number}"
    
    # For Quran, normalize format
    if "Surah:" in normalized:
        # Handle various Surah formats
        # "Surah: An-Nisa' | Ayat: 16" -> "Surah: An-Nisa' | Ayat: 16"
        # "Surah Al-A'raf Ayat 33" -> "Surah: Al-A'raf | Ayat: 33"
        
        if "Ayat:" in normalized:
            # Already in correct format
            return normalized
        elif "Ayat" in normalized:
            # Convert "Surah Al-A'raf Ayat 33" to "Surah: Al-A'raf | Ayat: 33"
            parts = normalized.split("Ayat")
            if len(parts) == 2:
                surah_part = parts[0].replace("Surah", "Surah:").strip()
                ayat_part = "Ayat:" + parts[1].strip()
                return f"{surah_part} | {ayat_part}"
    
    return normalized

def parse_retrieval_results_from_context(context_str: str) -> list[str]:
    """Parse hasil retrieval dari context string - fokus pada hasil traversal graph"""
    retrieved_sources = []
    
    if not context_str:
        return retrieved_sources
    
    lines = context_str.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Method 1: Parse dari "Konteks utama ditemukan →" (hasil traversal utama)
        if "Konteks utama ditemukan →" in line:
            source = line.split("→")[-1].strip()
            if source and source not in retrieved_sources:
                retrieved_sources.append(source)
                continue
        
        # Method 2: Parse dari "↪️  Tambahan konteks:" (hasil traversal tambahan/tetangga)
        if "↪️  Tambahan konteks:" in line:
            source = line.split(":")[-1].strip()
            if source and source not in retrieved_sources:
                retrieved_sources.append(source)
                continue
        
        # Method 3: Parse dari "      ↪️  Tambahan konteks:" (dengan indentasi)
        if "Tambahan konteks:" in line and ("Hadis" in line or "Surah" in line):
            # Split by : and take the last part that contains the source
            parts = line.split(":")
            if len(parts) >= 2:
                source = ":".join(parts[1:]).strip()
                if source and source not in retrieved_sources:
                    retrieved_sources.append(source)
                continue
    
    return retrieved_sources

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
    - Fokus apakah traversal berhasil mengambil node-node yang berelasi
    - Mengabaikan apakah hasil retrieval tepat atau tidak
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
        
        # Parse hasil context - fokus pada hasil traversal
        retrieved_sources = parse_retrieval_results_from_context(context_str)
        
        print(f"  📊 Hasil Traversal Graph:")
        print(f"    Total sources ditemukan: {len(retrieved_sources)}")
        for i, source in enumerate(retrieved_sources):
            print(f"      {i+1}. {source}")
        
        # Extract base identifiers untuk matching
        retrieved_base_ids = set()
        for source in retrieved_sources:
            base_id = extract_base_identifier(source)
            if base_id:  # Only add non-empty base IDs
                retrieved_base_ids.add(base_id)
        
        print(f"    Base IDs: {retrieved_base_ids}")
        
        # Check setiap expected chunk terhadap hasil traversal
        found_chunks = []
        missing_chunks = []
        
        for expected_chunk in expected_chunks:
            chunk_id = expected_chunk.get("chunk_id", "")
            expected_base_id = extract_base_identifier(chunk_id)
            
            print(f"  🎯 Mencari: '{expected_base_id}'")
            
            # Check exact match
            found = False
            matched_source = None
            
            for retrieved_base in retrieved_base_ids:
                if expected_base_id == retrieved_base:
                    found = True
                    matched_source = retrieved_base
                    break
                
                # Fallback: check similarity untuk hadis
                elif "Hadis" in expected_base_id and "Hadis" in retrieved_base:
                    # Extract numbers untuk hadis comparison
                    exp_num = re.search(r'No\.?\s*(\d+)', expected_base_id)
                    ret_num = re.search(r'No\.?\s*(\d+)', retrieved_base)
                    exp_collection = re.search(r'Hadis ([^N]+)', expected_base_id)
                    ret_collection = re.search(r'Hadis ([^N]+)', retrieved_base)
                    
                    if (exp_num and ret_num and exp_num.group(1) == ret_num.group(1) and
                        exp_collection and ret_collection and 
                        exp_collection.group(1).strip() == ret_collection.group(1).strip()):
                        found = True
                        matched_source = retrieved_base
                        break
                
                # Fallback: check similarity untuk Quran
                elif "Surah:" in expected_base_id and "Surah:" in retrieved_base:
                    # Extract surah name dan ayat number
                    exp_surah = re.search(r'Surah:\s*([^|]+)', expected_base_id)
                    ret_surah = re.search(r'Surah:\s*([^|]+)', retrieved_base)
                    exp_ayat = re.search(r'Ayat:\s*(\d+)', expected_base_id)
                    ret_ayat = re.search(r'Ayat:\s*(\d+)', retrieved_base)
                    
                    if (exp_surah and ret_surah and exp_ayat and ret_ayat):
                        exp_surah_name = exp_surah.group(1).strip()
                        ret_surah_name = ret_surah.group(1).strip()
                        
                        # Normalize surah names untuk comparison
                        exp_surah_normalized = exp_surah_name.replace("'", "").replace("-", "").lower()
                        ret_surah_normalized = ret_surah_name.replace("'", "").replace("-", "").lower()
                        
                        if (exp_surah_normalized == ret_surah_normalized and 
                            exp_ayat.group(1) == ret_ayat.group(1)):
                            found = True
                            matched_source = retrieved_base
                            break
            
            if found:
                found_chunks.append(expected_chunk)
                print(f"    ✅ DITEMUKAN oleh traversal: {matched_source}")
            else:
                missing_chunks.append(expected_chunk)
                print(f"    ❌ TIDAK ditemukan oleh traversal")
        
        success_rate = len(found_chunks) / len(expected_chunks) if expected_chunks else 0
        
        print(f"\n  📊 EVALUASI TRAVERSAL GRAPH:")
        print(f"     Success Rate: {success_rate:.2%}")
        print(f"     Berhasil ditraverse: {len(found_chunks)} / {len(expected_chunks)}")
        
        # Analisis traversal
        if success_rate == 1.0:
            print(f"     🎉 PERFECT! Traversal berhasil menemukan semua expected chunks")
        elif success_rate >= 0.5:
            print(f"     ✅ GOOD! Traversal berhasil menemukan sebagian besar chunks")
        else:
            print(f"     ⚠️  NEEDS IMPROVEMENT! Traversal perlu diperbaiki")
        
        results.append({
            "query": query,
            "success_rate": success_rate,
            "found_chunks": found_chunks,
            "missing_chunks": missing_chunks,
            "retrieved_sources": retrieved_sources,
            "traversal_analysis": {
                "total_sources_found": len(retrieved_sources),
                "expected_vs_found": f"{len(found_chunks)}/{len(expected_chunks)}"
            }
        })
    
    # Summary
    overall_success = sum(r["success_rate"] for r in results) / len(results) if results else 0
    print(f"\n🎯 HASIL EVALUASI GRAPH TRAVERSAL:")
    print(f"Overall Traversal Success Rate: {overall_success:.2%}")
    
    # Analisis detail
    perfect_count = sum(1 for r in results if r["success_rate"] == 1.0)
    good_count = sum(1 for r in results if 0.5 <= r["success_rate"] < 1.0)
    poor_count = sum(1 for r in results if r["success_rate"] < 0.5)
    
    print(f"📈 Breakdown:")
    print(f"   Perfect (100%): {perfect_count} queries")
    print(f"   Good (≥50%): {good_count} queries") 
    print(f"   Needs Work (<50%): {poor_count} queries")
    
    return results

def debug_context_parsing(context_str: str):
    """Debug function untuk melihat proses parsing"""
    print("🔧 DEBUG CONTEXT PARSING:")
    print("Raw context preview:")
    print(context_str[:1000] + "..." if len(context_str) > 1000 else context_str)
    print("\n" + "="*50)
    
    sources = parse_retrieval_results_from_context(context_str)
    print(f"Parsed sources ({len(sources)}):")
    for i, source in enumerate(sources):
        base_id = extract_base_identifier(source)
        print(f"  {i+1}. '{source}' -> Base: '{base_id}'")

if __name__ == "__main__":
    # Test normalisasi dulu
    print("🔧 Testing normalisasi:")
    test_cases = [
        "📘 Hadis Jami` at-Tirmidzi No. 1376 | Kitab: Hukum Hudud, Bab: Hukuman liwath (homoseksual)",
        "Hadis Jami` at-Tirmidzi No. 1376 | Kitab: Hukum Hudud, Bab: Hukuman liwath (homoseksual)",
        "📖 Surah: An-Nisa' | Ayat: 16",
        "Surah: An-Nur | Ayat: 2",
        "Surah Al-A'raf Ayat 33",  # Test format dari output
        "Surah Al-Isra' Ayat 32"
    ]
    
    for case in test_cases:
        base_id = extract_base_identifier(case)
        print(f"  '{case}' -> '{base_id}'")
    
    print("\n" + "="*60)
    
    # Load ground truth
    with open('ground_truth_graph.json', 'r', encoding='utf-8') as f:
        ground_truth = json.load(f)
    
    print("🎯 EVALUASI GRAPH TRAVERSAL")
    print("Focus: Mengevaluasi kemampuan traversal dalam mengambil node-node yang berelasi")
    print("=" * 60)
    
    # Evaluasi semua queries atau hanya single test
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--single":
        print("🧪 Mode: Single query test")
        test_data = ground_truth[:1]
    else:
        print("🧪 Mode: Full evaluation")
        test_data = ground_truth
    
    results = evaluate_traversal_quality(test_data)
    
    # Optional: Save results
    if len(sys.argv) > 1 and sys.argv[1] == "--save":
        import json
        with open('traversal_evaluation_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print("\n💾 Hasil disimpan ke 'traversal_evaluation_results.json'")