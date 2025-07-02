#!/usr/bin/env python3
"""
Test all search modes: Semantic, Hybrid, and Keyword (BM25 fallback)
Verify alpha calculation by LLM and proper fusion weighting
"""

import asyncio
import httpx
import json
from typing import List, Dict, Any

class SearchModeTester:
    def __init__(self):
        self.base_url = 'https://leafloaf-32905605817.us-central1.run.app'
        self.results = []
    
    async def test_query(self, query: str, expected_mode: str, expected_alpha_range: tuple) -> Dict:
        """Test a single query and analyze results"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f'{self.base_url}/api/v1/search',
                json={'query': query}
            )
        
        if response.status_code != 200:
            return {'error': f'Failed with status {response.status_code}'}
        
        data = response.json()
        
        # Extract key information
        result = {
            'query': query,
            'expected_mode': expected_mode,
            'expected_alpha_range': expected_alpha_range,
            'products_found': len(data.get('products', [])),
            'execution_time': data.get('execution', {}).get('total_time_ms', 0),
            'reasoning': data.get('execution', {}).get('reasoning_steps', []),
            'success': data.get('success', False)
        }
        
        # Try to extract alpha from reasoning
        alpha_value = None
        for step in result['reasoning']:
            if 'Alpha:' in step:
                try:
                    alpha_str = step.split('Alpha:')[1].strip()
                    alpha_value = float(alpha_str.split()[0])
                    result['actual_alpha'] = alpha_value
                except:
                    pass
        
        # Check if alpha is in expected range
        if alpha_value is not None:
            min_alpha, max_alpha = expected_alpha_range
            result['alpha_correct'] = min_alpha <= alpha_value <= max_alpha
        else:
            result['alpha_correct'] = False
            result['actual_alpha'] = 'Not found'
        
        # Get sample products
        result['sample_products'] = [
            {
                'name': p.get('product_name', ''),
                'sku': p.get('sku', ''),
                'price': p.get('price', 0)
            }
            for p in data.get('products', [])[:3]
        ]
        
        return result
    
    async def run_all_tests(self):
        """Run comprehensive search mode tests"""
        
        print("=" * 80)
        print("TESTING ALL SEARCH MODES: SEMANTIC, HYBRID, AND KEYWORD (BM25)")
        print("=" * 80)
        
        # Define test cases
        test_cases = [
            # SEMANTIC SEARCH (alpha 0.7-1.0) - Abstract concepts
            ("breakfast ideas", "semantic", (0.7, 1.0)),
            ("healthy snacks", "semantic", (0.7, 1.0)),
            ("ingredients for salad", "semantic", (0.7, 1.0)),
            ("summer BBQ essentials", "semantic", (0.7, 1.0)),
            ("meal prep vegetables", "semantic", (0.7, 1.0)),
            
            # HYBRID SEARCH (alpha 0.4-0.6) - Specific + context
            ("organic spinach", "hybrid", (0.4, 0.6)),
            ("fresh tomatoes", "hybrid", (0.4, 0.6)),
            ("gluten free pasta", "hybrid", (0.4, 0.6)),
            ("dairy free milk", "hybrid", (0.4, 0.6)),
            ("whole grain bread", "hybrid", (0.4, 0.6)),
            
            # KEYWORD SEARCH (alpha 0.0-0.3) - Exact matches
            ("SP6BW1", "keyword", (0.0, 0.3)),  # SKU search
            ("Oatly barista", "keyword", (0.0, 0.3)),  # Brand + specific
            ("Baby Spinach 2X2", "keyword", (0.0, 0.3)),  # Exact product
            ("12X5 Oz", "keyword", (0.0, 0.3)),  # Package size
            ("SALADSF04", "keyword", (0.0, 0.3)),  # Another SKU
        ]
        
        # Run all tests
        for query, mode, alpha_range in test_cases:
            print(f"\n{'='*60}")
            print(f"Testing: '{query}'")
            print(f"Expected: {mode} search (alpha {alpha_range[0]}-{alpha_range[1]})")
            
            result = await self.test_query(query, mode, alpha_range)
            self.results.append(result)
            
            if result.get('error'):
                print(f"❌ Error: {result['error']}")
                continue
            
            # Display results
            print(f"Alpha: {result.get('actual_alpha', 'N/A')}")
            print(f"Products found: {result['products_found']}")
            print(f"Response time: {result['execution_time']:.0f}ms")
            
            # Check if alpha is correct
            if result.get('alpha_correct'):
                print(f"✅ Alpha value correct for {mode} search")
            else:
                print(f"⚠️  Alpha value unexpected: {result.get('actual_alpha')}")
            
            # Show sample products
            if result['sample_products']:
                print("\nSample results:")
                for i, product in enumerate(result['sample_products'], 1):
                    print(f"  {i}. {product['name']} (SKU: {product['sku']}) - ${product['price']:.2f}")
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("SEARCH MODE TEST SUMMARY")
        print("="*80)
        
        # Count by mode
        mode_counts = {
            'semantic': {'total': 0, 'correct': 0},
            'hybrid': {'total': 0, 'correct': 0},
            'keyword': {'total': 0, 'correct': 0}
        }
        
        for result in self.results:
            if 'error' not in result:
                mode = result['expected_mode']
                mode_counts[mode]['total'] += 1
                if result.get('alpha_correct', False):
                    mode_counts[mode]['correct'] += 1
        
        # Display results
        print("\nAlpha Calculation Accuracy:")
        for mode, counts in mode_counts.items():
            if counts['total'] > 0:
                accuracy = (counts['correct'] / counts['total']) * 100
                print(f"  {mode.capitalize()}: {counts['correct']}/{counts['total']} ({accuracy:.0f}%)")
        
        # Overall statistics
        total_queries = len([r for r in self.results if 'error' not in r])
        avg_time = sum(r.get('execution_time', 0) for r in self.results if 'error' not in r) / total_queries if total_queries > 0 else 0
        
        print(f"\nTotal queries tested: {total_queries}")
        print(f"Average response time: {avg_time:.0f}ms")
        
        # Check if all modes are working
        modes_working = {
            'semantic': any(r.get('alpha_correct') and r['expected_mode'] == 'semantic' for r in self.results),
            'hybrid': any(r.get('alpha_correct') and r['expected_mode'] == 'hybrid' for r in self.results),
            'keyword': any(r.get('alpha_correct') and r['expected_mode'] == 'keyword' for r in self.results)
        }
        
        print("\nSearch Modes Status:")
        for mode, working in modes_working.items():
            status = "✅ Working" if working else "❌ Not working"
            print(f"  {mode.capitalize()}: {status}")
        
        # Fusion algorithm check
        print("\n" + "="*80)
        print("HYBRID SEARCH FUSION VERIFICATION")
        print("="*80)
        print("According to Weaviate's fusion algorithms:")
        print("- Alpha closer to 0 = More keyword weight (BM25)")
        print("- Alpha closer to 1 = More semantic weight (vector)")
        print("- Alpha 0.5 should favor semantic (not 50/50 split)")
        
        # Check if hybrid searches have correct alpha
        hybrid_results = [r for r in self.results if r['expected_mode'] == 'hybrid' and 'actual_alpha' in r and r['actual_alpha'] != 'Not found']
        if hybrid_results:
            avg_hybrid_alpha = sum(r['actual_alpha'] for r in hybrid_results) / len(hybrid_results)
            print(f"\nAverage alpha for hybrid searches: {avg_hybrid_alpha:.2f}")
            if 0.4 <= avg_hybrid_alpha <= 0.6:
                print("✅ Hybrid search correctly balanced")
            else:
                print("⚠️  Hybrid search may need adjustment")

if __name__ == "__main__":
    tester = SearchModeTester()
    asyncio.run(tester.run_all_tests())