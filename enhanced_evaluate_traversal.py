# enhanced_evaluate_traversal.py

from config import driver
from retrieval.traversal import find_info_chunk_id, get_full_context_from_info, get_neighboring_hadiths_in_bab
import json

def normalize_source_id(source_id: str) -> str:
    """Normalize source ID untuk matching yang konsisten"""
    # Remove emoji dan normalize format
    normalized = source_id.replace('📘 ', '').replace('📖 ', '')
    
    # Standardize separator untuk hadis
    if 'Kitab:' in normalized and 'Bab:' in normalized:
        parts = normalized.split('|')
        if len(parts) >= 2:
            hadis_part = parts[0].strip()
            detail_part = parts[1].strip()
            # Ensure consistent format: "Hadis ... | Kitab: ..., Bab: ..."
            if ', Bab:' in detail_part:
                detail_part = detail_part.replace(', Bab:', ' | Bab:')
            normalized = f"{hadis_part} Kitab: {detail_part}"
    
    return normalized

def evaluate_traversal_completeness(source_type: str, context_data: dict) -> dict:
    """
    Evaluasi kelengkapan traversal berdasarkan tipe sumber
    
    Args:
        source_type: 'quran' atau 'hadith'
        context_data: Dictionary hasil traversal dari get_full_context_from_info
    
    Returns:
        Dictionary dengan status kelengkapan untuk setiap komponen
    """
    required_components = {
        'quran': ['info_text', 'text_text', 'translation_text', 'tafsir_text'],
        'hadith': ['info_text', 'text_text', 'translation_text']  # hadits tidak ada tafsir
    }
    
    completeness = {}
    required = required_components.get(source_type, [])
    
    for component in required:
        value = getattr(context_data, component, None) if hasattr(context_data, component) else context_data.get(component)
        completeness[component] = {
            'present': value is not None and value.strip() != '',
            'value': value[:100] + '...' if value and len(value) > 100 else value
        }
    
    # Calculate completion percentage
    total_required = len(required)
    found_count = sum(1 for comp in completeness.values() if comp['present'])
    completion_rate = (found_count / total_required * 100) if total_required > 0 else 0
    
    return {
        'completion_rate': completion_rate,
        'total_required': total_required,
        'found_count': found_count,
        'components': completeness,
        'missing_components': [comp for comp, data in completeness.items() if not data['present']]
    }

def detect_source_type(source_id: str) -> str:
    """Detect apakah source adalah Al-Quran atau Hadits"""
    if 'Surah:' in source_id and 'Ayat:' in source_id:
        return 'quran'
    elif 'Hadis' in source_id or 'Kitab:' in source_id:
        return 'hadith'
    else:
        return 'unknown'

def perform_traversal_test(retrieved_sources: list, expected_sources: list = None) -> dict:
    """
    Test traversal untuk semua sources yang di-retrieve
    
    Args:
        retrieved_sources: List of tuples (chunk_id, source_identifier, score)
        expected_sources: List of expected source identifiers (optional)
    
    Returns:
        Detailed traversal test results
    """
    results = {
        'total_sources': len(retrieved_sources),
        'successful_traversals': 0,
        'failed_traversals': 0,
        'traversal_details': [],
        'overall_completion_rate': 0,
        'issues_found': []
    }
    
    total_completion = 0
    
    for i, (chunk_id, source_id, score) in enumerate(retrieved_sources):
        print(f"\n🔍 Testing traversal for source {i+1}: {source_id}")
        
        # Step 1: Find info chunk
        info_id = find_info_chunk_id(chunk_id)
        if not info_id:
            results['failed_traversals'] += 1
            results['issues_found'].append(f"No info chunk found for {source_id}")
            continue
        
        # Step 2: Get full context
        context = get_full_context_from_info(info_id)
        if not context:
            results['failed_traversals'] += 1
            results['issues_found'].append(f"No context retrieved for {source_id}")
            continue
        
        # Step 3: Detect source type and evaluate completeness
        source_type = detect_source_type(source_id)
        completeness = evaluate_traversal_completeness(source_type, context)
        
        # Step 4: Check for neighboring content (for hadits)
        neighbor_info = []
        if source_type == 'hadith' and hasattr(context, 'bab_name') and context.bab_name:
            neighbors = get_neighboring_hadiths_in_bab(
                context.bab_name, 
                context.kitab_name or '', 
                context.source_name or '',
                context.hadith_number or 0,
                limit=2
            )
            neighbor_info = [f"Found {len(neighbors)} neighboring hadits"]
        
        traversal_detail = {
            'source_id': source_id,
            'source_type': source_type,
            'chunk_id': chunk_id,
            'info_id': info_id,
            'retrieval_score': score,
            'completeness': completeness,
            'neighbor_info': neighbor_info,
            'raw_context': {
                'info_text': getattr(context, 'info_text', None),
                'text_text': getattr(context, 'text_text', None),
                'translation_text': getattr(context, 'translation_text', None),
                'tafsir_text': getattr(context, 'tafsir_text', None) if source_type == 'quran' else None
            }
        }
        
        results['traversal_details'].append(traversal_detail)
        total_completion += completeness['completion_rate']
        
        if completeness['completion_rate'] >= 80:  # Threshold untuk successful traversal
            results['successful_traversals'] += 1
        else:
            results['failed_traversals'] += 1
            results['issues_found'].append(
                f"{source_id}: Missing {', '.join(completeness['missing_components'])}"
            )
        
        # Print detailed results
        print(f"   Source Type: {source_type}")
        print(f"   Completion Rate: {completeness['completion_rate']:.1f}%")
        print(f"   Components found: {completeness['found_count']}/{completeness['total_required']}")
        if completeness['missing_components']:
            print(f"   ❌ Missing: {', '.join(completeness['missing_components'])}")
        else:
            print(f"   ✅ All components present")
    
    # Calculate overall completion rate
    results['overall_completion_rate'] = total_completion / len(retrieved_sources) if retrieved_sources else 0
    
    return results

def run_enhanced_evaluation(ground_truth_file: str = None, sample_queries: list = None):
    """
    Run enhanced evaluation dengan focus pada traversal quality
    """
    if ground_truth_file:
        with open(ground_truth_file, 'r', encoding='utf-8') as f:
            ground_truth = json.load(f)
    else:
        # Sample data untuk testing
        ground_truth = [
            {
                "query": "bagaimana islam memandang perbuatan liwath?",
                "expected_ids": [
                    "📘 Hadis Jami` at-Tirmidzi No. 1376 Kitab: Hukum Hudud | Bab: Hukuman liwath (homoseksual)",
                    "📖 Surah: An-Nisa' | Ayat: 16"
                ]
            }
        ]
    
    print("🚀 ENHANCED TRAVERSAL EVALUATION")
    print("=" * 60)
    
    overall_results = {
        'queries_tested': 0,
        'total_traversals': 0,
        'successful_traversals': 0,
        'average_completion_rate': 0,
        'query_results': []
    }
    
    for item in ground_truth:
        query = item['query']
        print(f"\n🔍 Query: {query}")
        
        # Simulate retrieved sources (replace with actual retrieval results)
        # Format: (chunk_id, source_identifier, score)
        simulated_retrieved = [
            ("4:61faf3a3-1e44-4b2f-a051-c46cc91c49bc:61229", 
             "Hadis Jami` at-Tirmidzi No. 1376 | Kitab: Hukum Hudud, Bab: Hukuman liwath (homoseksual)", 
             0.7783),
            ("4:61faf3a3-1e44-4b2f-a051-c46cc91c49bc:13989", 
             "Surah: An-Nur | Ayat: 2", 
             0.7771)
        ]
        
        # Perform traversal test
        traversal_results = perform_traversal_test(simulated_retrieved, item.get('expected_ids'))
        
        query_result = {
            'query': query,
            'traversal_results': traversal_results
        }
        
        overall_results['query_results'].append(query_result)
        overall_results['queries_tested'] += 1
        overall_results['total_traversals'] += traversal_results['total_sources']
        overall_results['successful_traversals'] += traversal_results['successful_traversals']
        
        print(f"\n📊 Query Results:")
        print(f"   Total sources: {traversal_results['total_sources']}")
        print(f"   Successful traversals: {traversal_results['successful_traversals']}")
        print(f"   Overall completion rate: {traversal_results['overall_completion_rate']:.1f}%")
        
        if traversal_results['issues_found']:
            print(f"   ⚠️  Issues found:")
            for issue in traversal_results['issues_found']:
                print(f"      - {issue}")
    
    # Calculate overall metrics
    if overall_results['total_traversals'] > 0:
        overall_results['traversal_success_rate'] = (
            overall_results['successful_traversals'] / overall_results['total_traversals'] * 100
        )
        
        total_completion = sum(
            qr['traversal_results']['overall_completion_rate'] 
            for qr in overall_results['query_results']
        )
        overall_results['average_completion_rate'] = total_completion / overall_results['queries_tested']
    
    print(f"\n🎯 OVERALL TRAVERSAL EVALUATION RESULTS")
    print("=" * 60)
    print(f"Queries tested: {overall_results['queries_tested']}")
    print(f"Total traversals: {overall_results['total_traversals']}")
    print(f"Successful traversals: {overall_results['successful_traversals']}")
    print(f"Traversal success rate: {overall_results.get('traversal_success_rate', 0):.1f}%")
    print(f"Average completion rate: {overall_results['average_completion_rate']:.1f}%")
    
    return overall_results

if __name__ == "__main__":
    # Run the enhanced evaluation
    results = run_enhanced_evaluation()
    
    # Optionally save results to file
    with open('traversal_evaluation_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)