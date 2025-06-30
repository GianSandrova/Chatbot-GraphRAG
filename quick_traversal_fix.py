# quick_traversal_fix.py
# Solusi cepat untuk memperbaiki evaluasi traversal Anda

from Backend.config import driver
from retrieval.traversal import find_info_chunk_id, get_full_context_from_info

def check_traversal_completeness(chunk_id, source_id, score):
    """
    Function untuk mengecek kelengkapan traversal satu source
    Returns: dict dengan informasi lengkap tentang traversal
    """
    print(f"\n🎯 Vector hit → Chunk '{chunk_id}' (ID: {chunk_id}) | Skor: {score:.4f}")
    
    # Step 1: Find info chunk
    print(f"   → Traversal ke info ID...")
    info_id = find_info_chunk_id(chunk_id)
    
    if not info_id:
        print(f"   ❌ TRAVERSAL FAILED: Info chunk tidak ditemukan")
        return {
            'success': False,
            'error': 'Info chunk not found',
            'source_id': source_id,
            'components': {}
        }
    
    print(f"   → Info ID ditemukan: {info_id}")
    
    # Step 2: Get full context
    context = get_full_context_from_info(info_id)
    
    if not context:
        print(f"   ❌ TRAVERSAL FAILED: Context tidak dapat diambil")
        return {
            'success': False,
            'error': 'Context retrieval failed',
            'source_id': source_id,
            'components': {}
        }
    
    # Step 3: Check components based on source type
    source_type = 'quran' if 'Surah:' in source_id else 'hadith'
    
    expected_components = {
        'quran': ['info_text', 'text_text', 'translation_text', 'tafsir_text'],
        'hadith': ['info_text', 'text_text', 'translation_text']
    }
    
    required = expected_components.get(source_type, [])
    components_status = {}
    missing_components = []
    
    print(f"   Konteks utama ditemukan → {source_id}")
    print(f"   Potongan isi:")
    
    for component in required:
        value = getattr(context, component, None)
        is_present = value is not None and str(value).strip() != ''
        
        components_status[component] = {
            'present': is_present,
            'value': value,
            'length': len(str(value)) if value else 0
        }
        
        if not is_present:
            missing_components.append(component)
        
        # Print dengan format yang sama seperti log Anda
        component_labels = {
            'info_text': 'Info       ',
            'text_text': 'Teks Arab  ',
            'translation_text': 'Terjemahan ',
            'tafsir_text': 'Tafsir     '
        }
        
        label = component_labels.get(component, component)
        if is_present:
            preview = str(value)[:70] + '...' if len(str(value)) > 70 else str(value)
            print(f"      {label}: {preview}")
        else:
            print(f"      {label}: ❌ MISSING")
    
    # Calculate completion rate
    total_required = len(required)
    found_count = len(required) - len(missing_components)
    completion_rate = (found_count / total_required * 100) if total_required > 0 else 0
    
    success = len(missing_components) == 0
    
    if success:
        print(f"   ✅ TRAVERSAL SUCCESSFUL: All components found ({found_count}/{total_required})")
    else:
        print(f"   ⚠️  TRAVERSAL INCOMPLETE: Missing {len(missing_components)} components")
        print(f"       Missing: {', '.join(missing_components)}")
    
    print(f"   📊 Completion Rate: {completion_rate:.1f}%")
    
    return {
        'success': success,
        'source_id': source_id,
        'source_type': source_type,
        'chunk_id': chunk_id,
        'info_id': info_id,
        'completion_rate': completion_rate,
        'components': components_status,
        'missing_components': missing_components,
        'found_count': found_count,
        'total_required': total_required
    }

def evaluate_all_retrievals(retrieved_sources):
    """
    Evaluate traversal untuk semua sources yang di-retrieve
    
    Args:
        retrieved_sources: List of tuples (chunk_id, source_id, score)
    
    Returns:
        Dict dengan summary lengkap
    """
    print(f"\n🔄 EVALUATING TRAVERSAL FOR {len(retrieved_sources)} SOURCES")
    print("=" * 70)
    
    results = []
    successful_traversals = 0
    total_completion = 0
    
    for i, (chunk_id, source_id, score) in enumerate(retrieved_sources, 1):
        print(f"\n--- Source {i}/{len(retrieved_sources)} ---")
        
        result = check_traversal_completeness(chunk_id, source_id, score)
        results.append(result)
        
        if result['success']:
            successful_traversals += 1
        
        total_completion += result['completion_rate']
    
    # Calculate summary statistics
    total_sources = len(retrieved_sources)
    success_rate = (successful_traversals / total_sources * 100) if total_sources > 0 else 0
    average_completion = total_completion / total_sources if total_sources > 0 else 0
    
    # Count missing components across all sources
    all_missing = {}
    for result in results:
        for missing in result['missing_components']:
            all_missing[missing] = all_missing.get(missing, 0) + 1
    
    # Print summary
    print(f"\n📊 TRAVERSAL EVALUATION SUMMARY")
    print("=" * 50)
    print(f"Total sources tested: {total_sources}")
    print(f"Successful traversals: {successful_traversals}")
    print(f"Failed traversals: {total_sources - successful_traversals}")
    print(f"Success rate: {success_rate:.1f}%")
    print(f"Average completion rate: {average_completion:.1f}%")
    
    if all_missing:
        print(f"\n⚠️  Most common missing components:")
        for component, count in sorted(all_missing.items(), key=lambda x: x[1], reverse=True):
            print(f"   - {component}: missing in {count} sources")
    
    # Print component-wise success rates
    component_success = {}
    for result in results:
        for component, status in result['components'].items():
            if component not in component_success:
                component_success[component] = {'found': 0, 'total': 0}
            component_success[component]['total'] += 1
            if status['present']:
                component_success[component]['found'] += 1
    
    print(f"\n📋 Component Success Rates:")
    for component, stats in component_success.items():
        rate = (stats['found'] / stats['total'] * 100) if stats['total'] > 0 else 0
        status_icon = "✅" if rate >= 80 else "⚠️" if rate >= 60 else "❌"
        print(f"   {status_icon} {component}: {rate:.1f}% ({stats['found']}/{stats['total']})")
    
    return {
        'total_sources': total_sources,
        'successful_traversals': successful_traversals,
        'success_rate': success_rate,
        'average_completion_rate': average_completion,
        'results': results,
        'missing_components_summary': all_missing,
        'component_success_rates': component_success
    }

# Integration dengan script evaluasi Anda yang sudah ada
def integrate_with_existing_evaluation():
    """
    Function ini untuk mengintegrasikan dengan script evaluate_graph.py Anda
    Ganti bagian evaluasi di script Anda dengan function ini
    """
    
    # Data dari log Anda
    retrieved_sources = [
        ("4:61faf3a3-1e44-4b2f-a051-c46cc91c49bc:61229", 
         "Hadis Jami` at-Tirmidzi No. 1376 | Kitab: Hukum Hudud, Bab: Hukuman liwath (homoseksual)", 
         0.7783),
        ("4:61faf3a3-1e44-4b2f-a051-c46cc91c49bc:13989", 
         "Surah: An-Nur | Ayat: 2", 
         0.7771),
        ("4:61faf3a3-1e44-4b2f-a051-c46cc91c49bc:4942", 
         "Surah: Al-A'raf | Ayat: 33", 
         0.7744),
        ("4:61faf3a3-1e44-4b2f-a051-c46cc91c49bc:10322", 
         "Surah: Al-Isra' | Ayat: 32", 
         0.7733),
        ("4:61faf3a3-1e44-4b2f-a051-c46cc91c49bc:10321", 
         "Surah: Al-Isra' | Ayat: 32", 
         0.7692)
    ]
    
    # Run evaluasi
    summary = evaluate_all_retrievals(retrieved_sources)
    
    return summary

# Main function untuk testing
if __name__ == "__main__":
    print("🚀 TESTING TRAVERSAL COMPLETENESS")
    
    # Run integrated evaluation
    results = integrate_with_existing_evaluation()
    
    # Save results jika diperlukan
    import json
    with open('traversal_completeness_report.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n💾 Detailed results saved to 'traversal_completeness_report.json'")
    
    # Generate recommendations
    print(f"\n🔧 RECOMMENDATIONS:")
    if results['success_rate'] < 80:
        print("   ⚠️  Low traversal success rate - check graph structure and relationships")
    
    if results['average_completion_rate'] < 90:
        print("   ⚠️  Low completion rate - some components are frequently missing")
        
        # Suggest specific fixes
        missing_summary = results['missing_components_summary']
        if missing_summary:
            most_missing = max(missing_summary.items(), key=lambda x: x[1])
            print(f"   🔧 Focus on fixing: {most_missing[0]} (missing in {most_missing[1]} cases)")
    
    if results['success_rate'] >= 90 and results['average_completion_rate'] >= 95:
        print("   ✅ Traversal system working well!")
    
    print(f"\n✅ Evaluation complete!")