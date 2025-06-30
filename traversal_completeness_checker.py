# traversal_completeness_checker.py

from config import driver
from retrieval.traversal import find_info_chunk_id, get_full_context_from_info
import json
from typing import Dict, List, Tuple, Any

class TraversalCompletenessChecker:
    """
    Class untuk menguji kelengkapan traversal pada sistem GraphRAG
    Focus pada memastikan semua komponen yang dibutuhkan ter-retrieve dengan benar
    """
    
    def __init__(self):
        self.expected_components = {
            'quran': {
                'required': ['info_text', 'text_text', 'translation_text', 'tafsir_text'],
                'optional': ['surah_name', 'ayat_number']
            },
            'hadith': {
                'required': ['info_text', 'text_text', 'translation_text'],
                'optional': ['hadith_number', 'bab_name', 'kitab_name', 'source_name']
            }
        }
    
    def identify_source_type(self, source_id: str) -> str:
        """Identifikasi tipe sumber berdasarkan ID"""
        if 'Surah:' in source_id and 'Ayat:' in source_id:
            return 'quran'
        elif any(keyword in source_id for keyword in ['Hadis', 'Kitab:', 'Bab:']):
            return 'hadith'
        return 'unknown'
    
    def check_component_completeness(self, context_data: Any, source_type: str) -> Dict:
        """
        Check kelengkapan setiap komponen untuk tipe sumber tertentu
        
        Returns:
            Dict dengan informasi kelengkapan setiap komponen
        """
        if source_type not in self.expected_components:
            return {'error': f'Unknown source type: {source_type}'}
        
        expected = self.expected_components[source_type]
        result = {
            'source_type': source_type,
            'required_components': {},
            'optional_components': {},
            'completion_summary': {}
        }
        
        # Check required components
        required_found = 0
        for component in expected['required']:
            value = getattr(context_data, component, None) if hasattr(context_data, component) else None
            is_present = value is not None and str(value).strip() != ''
            
            result['required_components'][component] = {
                'present': is_present,
                'value_preview': str(value)[:50] + '...' if value and len(str(value)) > 50 else str(value),
                'value_length': len(str(value)) if value else 0
            }
            
            if is_present:
                required_found += 1
        
        # Check optional components
        optional_found = 0
        for component in expected['optional']:
            value = getattr(context_data, component, None) if hasattr(context_data, component) else None
            is_present = value is not None and str(value).strip() != ''
            
            result['optional_components'][component] = {
                'present': is_present,
                'value': str(value) if value else None
            }
            
            if is_present:
                optional_found += 1
        
        # Completion summary
        total_required = len(expected['required'])
        total_optional = len(expected['optional'])
        
        result['completion_summary'] = {
            'required_completion_rate': (required_found / total_required * 100) if total_required > 0 else 0,
            'optional_completion_rate': (optional_found / total_optional * 100) if total_optional > 0 else 0,
            'required_found': required_found,
            'required_total': total_required,
            'optional_found': optional_found,
            'optional_total': total_optional,
            'is_complete': required_found == total_required,
            'missing_required': [
                comp for comp, data in result['required_components'].items() 
                if not data['present']
            ]
        }
        
        return result
    
    def test_single_source_traversal(self, chunk_id: str, source_id: str, retrieval_score: float = None) -> Dict:
        """
        Test traversal untuk satu source dan return detailed analysis
        """
        print(f"\n🔍 Testing traversal for: {source_id}")
        print(f"   Chunk ID: {chunk_id}")
        if retrieval_score:
            print(f"   Retrieval Score: {retrieval_score:.4f}")
        
        result = {
            'source_id': source_id,
            'chunk_id': chunk_id,
            'retrieval_score': retrieval_score,
            'traversal_status': 'unknown',
            'error': None,
            'info_id': None,
            'context_data': None,
            'completeness_check': None
        }
        
        try:
            # Step 1: Find info chunk
            print("   🔄 Step 1: Finding info chunk...")
            info_id = find_info_chunk_id(chunk_id)
            
            if not info_id:
                result['traversal_status'] = 'failed'
                result['error'] = 'No info chunk found'
                print("   ❌ Failed: No info chunk found")
                return result
            
            result['info_id'] = info_id
            print(f"   ✅ Info chunk found: {info_id}")
            
            # Step 2: Get full context
            print("   🔄 Step 2: Retrieving full context...")
            context = get_full_context_from_info(info_id)
            
            if not context:
                result['traversal_status'] = 'failed'
                result['error'] = 'No context data retrieved'
                print("   ❌ Failed: No context data retrieved")
                return result
            
            result['context_data'] = context
            print("   ✅ Context data retrieved")
            
            # Step 3: Check completeness
            print("   🔄 Step 3: Checking component completeness...")
            source_type = self.identify_source_type(source_id)
            completeness = self.check_component_completeness(context, source_type)
            result['completeness_check'] = completeness
            
            # Determine overall status
            if completeness['completion_summary']['is_complete']:
                result['traversal_status'] = 'success'
                print(f"   ✅ Traversal successful: {completeness['completion_summary']['required_completion_rate']:.1f}% complete")
            else:
                result['traversal_status'] = 'incomplete'
                print(f"   ⚠️  Traversal incomplete: {completeness['completion_summary']['required_completion_rate']:.1f}% complete")
                print(f"       Missing: {', '.join(completeness['completion_summary']['missing_required'])}")
            
            # Print component details
            print("   📋 Component Status:")
            for comp, data in completeness['required_components'].items():
                status = "✅" if data['present'] else "❌"
                print(f"      {status} {comp}: {data['value_preview']}")
            
        except Exception as e:
            result['traversal_status'] = 'error'
            result['error'] = str(e)
            print(f"   💥 Error during traversal: {e}")
        
        return result
    
    def test_multiple_sources(self, sources: List[Tuple[str, str, float]]) -> Dict:
        """
        Test traversal untuk multiple sources
        
        Args:
            sources: List of (chunk_id, source_id, retrieval_score)
        """
        print(f"\n🚀 TESTING TRAVERSAL FOR {len(sources)} SOURCES")
        print("=" * 60)
        
        results = {
            'total_sources': len(sources),
            'successful_traversals': 0,
            'incomplete_traversals': 0,
            'failed_traversals': 0,
            'error_traversals': 0,
            'source_results': [],
            'summary': {}
        }
        
        for i, (chunk_id, source_id, score) in enumerate(sources, 1):
            print(f"\n--- Source {i}/{len(sources)} ---")
            
            source_result = self.test_single_source_traversal(chunk_id, source_id, score)
            results['source_results'].append(source_result)
            
            # Count by status
            status = source_result['traversal_status']
            if status == 'success':
                results['successful_traversals'] += 1
            elif status == 'incomplete':
                results['incomplete_traversals'] += 1
            elif status == 'failed':
                results['failed_traversals'] += 1
            elif status == 'error':
                results['error_traversals'] += 1
        
        # Generate summary
        results['summary'] = {
            'success_rate': (results['successful_traversals'] / len(sources) * 100) if sources else 0,
            'completion_rates': [
                sr['completeness_check']['completion_summary']['required_completion_rate']
                for sr in results['source_results'] 
                if sr.get('completeness_check')
            ]
        }
        
        if results['summary']['completion_rates']:
            results['summary']['average_completion_rate'] = sum(results['summary']['completion_rates']) / len(results['summary']['completion_rates'])
        else:
            results['summary']['average_completion_rate'] = 0
        
        # Print summary
        print(f"\n📊 TRAVERSAL TEST SUMMARY")
        print("=" * 40)
        print(f"Total sources tested: {results['total_sources']}")
        print(f"✅ Successful: {results['successful_traversals']}")
        print(f"⚠️  Incomplete: {results['incomplete_traversals']}")
        print(f"❌ Failed: {results['failed_traversals']}")
        print(f"💥 Errors: {results['error_traversals']}")
        print(f"📈 Success rate: {results['summary']['success_rate']:.1f}%")
        print(f"📊 Average completion: {results['summary']['average_completion_rate']:.1f}%")
        
        return results
    
    def analyze_common_issues(self, test_results: Dict) -> List[str]:
        """
        Analyze common issues from test results
        """
        issues = []
        
        # Count missing components
        missing_components = {}
        for source_result in test_results['source_results']:
            if source_result.get('completeness_check'):
                for missing in source_result['completeness_check']['completion_summary']['missing_required']:
                    missing_components[missing] = missing_components.get(missing, 0) + 1
        
        if missing_components:
            issues.append("Most common missing components:")
            for component, count in sorted(missing_components.items(), key=lambda x: x[1], reverse=True):
                issues.append(f"  - {component}: missing in {count} sources")
        
        # Count traversal failures
        failures = [sr for sr in test_results['source_results'] if sr['traversal_status'] in ['failed', 'error']]
        if failures:
            issues.append(f"Traversal failures ({len(failures)} sources):")
            for failure in failures[:3]:  # Show first 3
                issues.append(f"  - {failure['source_id']}: {failure['error']}")
        
        return issues

# Usage example and test function
def main():
    """Main function untuk testing"""
    checker = TraversalCompletenessChecker()
    
    # Example sources dari log Anda
    test_sources = [
        ("4:61faf3a3-1e44-4b2f-a051-c46cc91c49bc:61229", 
         "Hadis Jami` at-Tirmidzi No. 1376 | Kitab: Hukum Hudud, Bab: Hukuman liwath (homoseksual)", 
         0.7783),
        ("4:61faf3a3-1e44-4b2f-a051-c46cc91c49bc:13989", 
         "Surah: An-Nur | Ayat: 2", 
         0.7771),
        ("4:61faf3a3-1e44-4b2f-a051-c46cc91c49bc:4942", 
         "Surah: Al-A'raf | Ayat: 33", 
         0.7744)
    ]
    
    # Run traversal test
    results = checker.test_multiple_sources(test_sources)
    
    # Analyze issues
    issues = checker.analyze_common_issues(results)
    if issues:
        print(f"\n🔍 ISSUE ANALYSIS")
        print("=" * 30)
        for issue in issues:
            print(issue)
    
    # Save results
    with open('traversal_completeness_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n💾 Results saved to 'traversal_completeness_results.json'")
    
    return results

if __name__ == "__main__":
    main()