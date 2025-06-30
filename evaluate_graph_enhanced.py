# evaluate_graph_enhanced.py
# Perbaikan untuk script evaluate_graph.py Anda

import json
from config import driver
from retrieval.traversal import find_info_chunk_id, get_full_context_from_info, get_neighboring_hadiths_in_bab

def normalize_id(text):
    """Normalisasi ID untuk matching"""
    return text.replace('📘 ', '').replace('📖 ', '').strip()

class EnhancedGraphEvaluator:
    def __init__(self):
        self.traversal_stats = {
            'total_traversals': 0,
            'successful_traversals': 0,
            'component_success': {
                'info_text': 0,
                'text_text': 0,
                'translation_text': 0,
                'tafsir_text': 0
            },
            'traversal_issues': []
        }
    
    def get_expected_components(self, source_type):
        """Get komponen yang diharapkan berdasarkan tipe sumber"""
        if source_type == 'quran':
            return ['info_text', 'text_text', 'translation_text', 'tafsir_text']
        elif source_type == 'hadith':
            return ['info_text', 'text_text', 'translation_text']
        return []
    
    def detect_source_type(self, source_id):
        """Deteksi tipe sumber"""
        if 'Surah:' in source_id and 'Ayat:' in source_id:
            return 'quran'
        elif any(keyword in source_id for keyword in ['Hadis', 'Kitab:', 'Bab:']):
            return 'hadith'
        return 'unknown'
    
    def evaluate_single_traversal(self, chunk_id, source_id, retrieval_score):
        """
        Evaluasi traversal untuk satu chunk dengan detail lengkap
        """
        print(f"\n🎯 Vector hit → Chunk '{chunk_id}' | Skor: {retrieval_score:.4f}")
        
        traversal_result = {
            'chunk_id': chunk_id,
            'source_id': source_id,
            'retrieval_score': retrieval_score,
            'info_id': None,
            'context_retrieved': False,
            'components_found': {},
            'component_completion_rate': 0,
            'source_type': self.detect_source_type(source_id),
            'traversal_success': False,
            'issues': []
        }
        
        # Step 1: Find info chunk
        print(f"   → Traversal ke info chunk...")
        info_id = find_info_chunk_id(chunk_id)
        
        if not info_id:
            traversal_result['issues'].append("Info chunk tidak ditemukan")
            print(f"   ❌ Info chunk tidak ditemukan untuk {chunk_id}")
            return traversal_result
        
        traversal_result['info_id'] = info_id
        print(f"   ✅ Info chunk ditemukan: {info_id}")
        
        # Step 2: Get full context
        context = get_full_context_from_info(info_id)
        
        if not context:
            traversal_result['issues'].append("Context tidak dapat di-retrieve")
            print(f"   ❌ Context tidak dapat di-retrieve")
            return traversal_result
        
        traversal_result['context_retrieved'] = True
        
        # Step 3: Check komponen yang ditemukan
        expected_components = self.get_expected_components(traversal_result['source_type'])
        components_found = 0
        
        print(f"   Konteks utama ditemukan → {source_id}")
        print(f"   Potongan isi:")
        
        for component in expected_components:
            value = getattr(context, component, None)
            is_present = value is not None and str(value).strip() != ''
            
            traversal_result['components_found'][component] = {
                'present': is_present,
                'preview': str(value)[:100] + '...' if value and len(str(value)) > 100 else str(value),
                'length': len(str(value)) if value else 0
            }
            
            if is_present:
                components_found += 1
                self.traversal_stats['component_success'][component] += 1
            
            # Print component status
            status = "✅" if is_present else "❌"
            component_label = {
                'info_text': 'Info',
                'text_text': 'Teks Arab',
                'translation_text': 'Terjemahan',
                'tafsir_text': 'Tafsir'
            }.get(component, component)
            
            if is_present:
                preview = str(value)[:50] + '...' if len(str(value)) > 50 else str(value)
                print(f"      {component_label:<12} : {preview}")
            else:
                print(f"      {component_label:<12} : ❌ MISSING")
        
        # Calculate completion rate
        total_expected = len(expected_components)
        traversal_result['component_completion_rate'] = (components_found / total_expected * 100) if total_expected > 0 else 0
        traversal_result['traversal_success'] = components_found == total_expected
        
        # Update global stats
        self.traversal_stats['total_traversals'] += 1
        if traversal_result['traversal_success']:
            self.traversal_stats['successful_traversals'] += 1
        else:
            missing_components = [comp for comp, data in traversal_result['components_found'].items() if not data['present']]
            traversal_result['issues'].append(f"Missing components: {', '.join(missing_components)}")
            self.traversal_stats['traversal_issues'].append({
                'source_id': source_id,
                'missing': missing_components
            })
        
        # Check for neighboring content (for hadits)
        if traversal_result['source_type'] == 'hadith' and context.bab_name:
            print(f"   ➡️ Mencari hadis tetangga dari Bab '{context.bab_name}'")
            try:
                neighbors = get_neighboring_hadiths_in_bab(
                    context.bab_name,
                    context.kitab_name or '',
                    context.source_name or '',
                    context.hadith_number or 0,
                    limit=2
                )
                if neighbors:
                    print(f"      ↪️  Tambahan konteks: {len(neighbors)} hadis tetangga ditemukan")
                    # Optionally process neighbor contexts
                    for neighbor_id in neighbors:
                        neighbor_context = get_full_context_from_info(neighbor_id)
                        if neighbor_context:
                            neighbor_source = f"Hadis {neighbor_context.source_name or ''} No. {neighbor_context.hadith_number or ''}"
                            print(f"         {neighbor_source}")
            except Exception as e:
                print(f"      ⚠️  Error mencari tetangga: {e}")
        
        print(f"   📊 Completion Rate: {traversal_result['component_completion_rate']:.1f}% ({components_found}/{total_expected})")
        
        return traversal_result
    
    def evaluate_query_traversal(self, query, retrieved_sources, expected_sources=None):
        """
        Evaluasi traversal untuk satu query dengan semua sources yang di-retrieve
        
        Args:
            query: Query string
            retrieved_sources: List of (chunk_id, source_id, score) tuples
            expected_sources: List of expected source IDs (optional)
        """
        print(f"\n🔍 Query: {query}")
        
        if expected_sources:
            print(f"  Expected sources count: {len(expected_sources)}")
            for i, exp_source in enumerate(expected_sources, 1):
                print(f"    {i}. {exp_source}")
        
        query_results = {
            'query': query,
            'expected_sources': expected_sources or [],
            'retrieved_sources': [],
            'traversal_results': [],
            'traversal_success_rate': 0,
            'average_completion_rate': 0,
            'issues_summary': []
        }
        
        # Process each retrieved source
        total_completion = 0
        successful_traversals = 0
        
        for chunk_id, source_id, score in retrieved_sources:
            # Perform traversal evaluation
            traversal_result = self.evaluate_single_traversal(chunk_id, source_id, score)
            query_results['traversal_results'].append(traversal_result)
            query_results['retrieved_sources'].append(source_id)
            
            total_completion += traversal_result['component_completion_rate']
            if traversal_result['traversal_success']:
                successful_traversals += 1
        
        # Calculate query-level metrics
        total_sources = len(retrieved_sources)
        if total_sources > 0:
            query_results['traversal_success_rate'] = (successful_traversals / total_sources) * 100
            query_results['average_completion_rate'] = total_completion / total_sources
        
        # Collect issues
        for result in query_results['traversal_results']:
            if result['issues']:
                query_results['issues_summary'].extend(result['issues'])
        
        # Print query summary
        print(f"\n  📊 Query Traversal Summary:")
        print(f"    Retrieved sources: {total_sources}")
        print(f"    Successful traversals: {successful_traversals}")
        print(f"    Traversal success rate: {query_results['traversal_success_rate']:.1f}%")
        print(f"    Average completion rate: {query_results['average_completion_rate']:.1f}%")
        
        if query_results['issues_summary']:
            print(f"    ⚠️  Issues found: {len(query_results['issues_summary'])}")
        
        return query_results
    
    def run_comprehensive_evaluation(self, ground_truth_data):
        """
        Run evaluasi komprehensif untuk semua queries
        """
        print("🚀 COMPREHENSIVE TRAVERSAL EVALUATION")
        print("=" * 60)
        
        evaluation_results = {
            'total_queries': len(ground_truth_data),
            'query_results': [],
            'global_traversal_stats': {},
            'recommendations': []
        }
        
        for item in ground_truth_data:
            query = item['query']
            expected_sources = item.get('expected_ids', [])
            
            # Simulate retrieved sources (replace with actual retrieval)
            # Format: (chunk_id, source_id, score)
            simulated_retrieved = self.simulate_retrieval_results(query)
            
            # Evaluate traversal for this query
            query_result = self.evaluate_query_traversal(query, simulated_retrieved, expected_sources)
            evaluation_results['query_results'].append(query_result)
        
        # Calculate global statistics
        evaluation_results['global_traversal_stats'] = self.calculate_global_stats(evaluation_results['query_results'])
        
        # Generate recommendations
        evaluation_results['recommendations'] = self.generate_recommendations()
        
        # Print final summary
        self.print_final_summary(evaluation_results)
        
        return evaluation_results
    
    def simulate_retrieval_results(self, query):
        """
        Simulate retrieval results based on query
        Replace this with actual retrieval from your system
        """
        # Example based on your log
        if "liwath" in query.lower():
            return [
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
        
        # Default empty result
        return []
    
    def calculate_global_stats(self, query_results):
        """Calculate global statistics across all queries"""
        total_sources = sum(len(qr['retrieved_sources']) for qr in query_results)
        total_successful = sum(
            sum(1 for tr in qr['traversal_results'] if tr['traversal_success'])
            for qr in query_results
        )
        
        all_completion_rates = [
            tr['component_completion_rate']
            for qr in query_results
            for tr in qr['traversal_results']
        ]
        
        return {
            'total_sources_tested': total_sources,
            'total_successful_traversals': total_successful,
            'overall_success_rate': (total_successful / total_sources * 100) if total_sources > 0 else 0,
            'average_completion_rate': sum(all_completion_rates) / len(all_completion_rates) if all_completion_rates else 0,
            'component_success_rates': {
                comp: (count / self.traversal_stats['total_traversals'] * 100) if self.traversal_stats['total_traversals'] > 0 else 0
                for comp, count in self.traversal_stats['component_success'].items()
            }
        }
    
    def generate_recommendations(self):
        """Generate recommendations based on traversal results"""
        recommendations = []
        
        # Check for common missing components
        component_success = self.traversal_stats['component_success']
        total_traversals = self.traversal_stats['total_traversals']
        
        if total_traversals > 0:
            for component, success_count in component_success.items():
                success_rate = (success_count / total_traversals) * 100
                if success_rate < 80:
                    recommendations.append(
                        f"⚠️  {component} has low success rate ({success_rate:.1f}%) - check graph relationships"
                    )
        
        # Check for traversal failures
        if self.traversal_stats['traversal_issues']:
            common_missing = {}
            for issue in self.traversal_stats['traversal_issues']:
                for missing in issue['missing']:
                    common_missing[missing] = common_missing.get(missing, 0) + 1
            
            if common_missing:
                most_common = max(common_missing.items(), key=lambda x: x[1])
                recommendations.append(
                    f"🔧 Most common missing component: {most_common[0]} (missing in {most_common[1]} cases)"
                )
        
        return recommendations
    
    def print_final_summary(self, evaluation_results):
        """Print comprehensive final summary"""
        print(f"\n📊 FINAL TRAVERSAL EVALUATION RESULTS")
        print("=" * 60)
        
        stats = evaluation_results['global_traversal_stats']
        print(f"Total queries tested: {evaluation_results['total_queries']}")
        print(f"Total sources tested: {stats['total_sources_tested']}")
        print(f"Successful traversals: {stats['total_successful_traversals']}")
        print(f"Overall success rate: {stats['overall_success_rate']:.1f}%")
        print(f"Average completion rate: {stats['average_completion_rate']:.1f}%")
        
        print(f"\n📋 Component Success Rates:")
        for component, rate in stats['component_success_rates'].items():
            status = "✅" if rate >= 80 else "⚠️" if rate >= 60 else "❌"
            component_label = {
                'info_text': 'Info Text',
                'text_text': 'Arabic Text',
                'translation_text': 'Translation',
                'tafsir_text': 'Tafsir'
            }.get(component, component)
            print(f"  {status} {component_label}: {rate:.1f}%")
        
        if evaluation_results['recommendations']:
            print(f"\n🔧 RECOMMENDATIONS:")
            for rec in evaluation_results['recommendations']:
                print(f"  {rec}")

# Usage
def main():
    """Main function untuk menjalankan evaluasi"""
    evaluator = EnhancedGraphEvaluator()
    
    # Load ground truth
    ground_truth = [
        {
            "query": "bagaimana islam memandang perbuatan liwath?",
            "expected_ids": [
                "📘 Hadis Jami` at-Tirmidzi No. 1376 Kitab: Hukum Hudud | Bab: Hukuman liwath (homoseksual)",
                "📖 Surah: An-Nisa' | Ayat: 16"
            ]
        }
    ]
    
    # Run evaluation
    results = evaluator.run_comprehensive_evaluation(ground_truth)
    
    # Save results
    with open('enhanced_traversal_evaluation.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n💾 Results saved to 'enhanced_traversal_evaluation.json'")
    
    return results

if __name__ == "__main__":
    main()