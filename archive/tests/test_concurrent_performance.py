#!/usr/bin/env python3
"""
Performance test with concurrent users
Tests system under load with multiple simultaneous requests
"""

import asyncio
import httpx
import time
import statistics
from typing import List, Dict
import random

class PerformanceTester:
    def __init__(self):
        self.base_url = 'https://leafloaf-32905605817.us-central1.run.app'
        self.test_queries = [
            # Semantic searches
            "breakfast ideas",
            "healthy snacks", 
            "meal prep essentials",
            "ingredients for salad",
            
            # Hybrid searches
            "organic spinach",
            "fresh tomatoes",
            "gluten free bread",
            "dairy free milk",
            
            # Keyword searches
            "SP6BW1",
            "Oatly barista",
            "Baby Spinach",
            "12X5 Oz"
        ]
    
    async def single_request(self, query: str) -> Dict:
        """Execute a single search request"""
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f'{self.base_url}/api/v1/search',
                    json={'query': query}
                )
            
            elapsed = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'query': query,
                    'response_time': elapsed,
                    'execution_time': data.get('execution', {}).get('total_time_ms', 0),
                    'products_found': len(data.get('products', []))
                }
            else:
                return {
                    'success': False,
                    'query': query,
                    'response_time': elapsed,
                    'error': f'Status {response.status_code}'
                }
        except Exception as e:
            return {
                'success': False,
                'query': query,
                'response_time': (time.time() - start_time) * 1000,
                'error': str(e)
            }
    
    async def concurrent_users(self, num_users: int, requests_per_user: int = 5) -> List[Dict]:
        """Simulate concurrent users making requests"""
        print(f"\n🚀 Testing with {num_users} concurrent users ({requests_per_user} requests each)")
        
        all_tasks = []
        
        # Create tasks for each user
        for user_id in range(num_users):
            for req_id in range(requests_per_user):
                # Random query for each request
                query = random.choice(self.test_queries)
                task = self.single_request(query)
                all_tasks.append(task)
        
        # Execute all requests concurrently
        start_time = time.time()
        results = await asyncio.gather(*all_tasks)
        total_time = (time.time() - start_time) * 1000
        
        # Calculate statistics
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        
        if successful:
            response_times = [r['response_time'] for r in successful]
            avg_response = statistics.mean(response_times)
            median_response = statistics.median(response_times)
            p95_response = sorted(response_times)[int(len(response_times) * 0.95)] if len(response_times) > 20 else max(response_times)
            
            print(f"\n📊 Results for {num_users} concurrent users:")
            print(f"   Total requests: {len(results)}")
            print(f"   Successful: {len(successful)} ({len(successful)/len(results)*100:.1f}%)")
            print(f"   Failed: {len(failed)}")
            print(f"   Total test time: {total_time:.0f}ms")
            print(f"   Throughput: {len(results)/(total_time/1000):.1f} req/s")
            print(f"\n   Response times:")
            print(f"   - Average: {avg_response:.0f}ms")
            print(f"   - Median: {median_response:.0f}ms")
            print(f"   - 95th percentile: {p95_response:.0f}ms")
            print(f"   - Min: {min(response_times):.0f}ms")
            print(f"   - Max: {max(response_times):.0f}ms")
            
            # Check if meeting SLA
            under_300ms = len([r for r in response_times if r < 300])
            print(f"\n   SLA (<300ms): {under_300ms}/{len(response_times)} ({under_300ms/len(response_times)*100:.1f}%)")
        
        return results
    
    async def run_load_test(self):
        """Run complete load test with increasing concurrent users"""
        print("="*80)
        print("PERFORMANCE TEST WITH CONCURRENT USERS")
        print("="*80)
        
        # Warm up
        print("\n🔥 Warming up service...")
        await self.single_request("test query")
        await asyncio.sleep(1)
        
        # Test with increasing load
        user_counts = [1, 5, 10, 20]
        all_results = {}
        
        for num_users in user_counts:
            results = await self.concurrent_users(num_users)
            all_results[num_users] = results
            
            # Wait between tests
            if num_users < user_counts[-1]:
                await asyncio.sleep(2)
        
        # Summary
        self.print_summary(all_results)
    
    def print_summary(self, all_results: Dict):
        """Print load test summary"""
        print("\n" + "="*80)
        print("LOAD TEST SUMMARY")
        print("="*80)
        
        print("\nPerformance by concurrent users:")
        print(f"{'Users':>6} | {'Avg Response':>12} | {'P95 Response':>12} | {'Success Rate':>12} | {'Throughput':>12}")
        print("-" * 70)
        
        for num_users, results in sorted(all_results.items()):
            successful = [r for r in results if r['success']]
            if successful:
                response_times = [r['response_time'] for r in successful]
                avg_response = statistics.mean(response_times)
                p95_response = sorted(response_times)[int(len(response_times) * 0.95)] if len(response_times) > 20 else max(response_times)
                success_rate = len(successful) / len(results) * 100
                
                # Calculate throughput
                total_time = max(response_times) - min([r['response_time'] for r in results])
                throughput = len(results) / (total_time / 1000) if total_time > 0 else 0
                
                print(f"{num_users:>6} | {avg_response:>10.0f}ms | {p95_response:>10.0f}ms | {success_rate:>10.1f}% | {throughput:>10.1f}/s")
        
        print("\n🎯 Performance Analysis:")
        
        # Check scalability
        if len(all_results) >= 2:
            user_counts = sorted(all_results.keys())
            first_avg = statistics.mean([r['response_time'] for r in all_results[user_counts[0]] if r['success']])
            last_avg = statistics.mean([r['response_time'] for r in all_results[user_counts[-1]] if r['success']])
            
            degradation = ((last_avg - first_avg) / first_avg) * 100
            
            print(f"   Response time degradation from {user_counts[0]} to {user_counts[-1]} users: {degradation:.1f}%")
            
            if degradation < 50:
                print("   ✅ Good scalability - system handles load well")
            elif degradation < 100:
                print("   ⚠️  Moderate scalability - some performance impact under load")
            else:
                print("   ❌ Poor scalability - significant performance degradation")

async def main():
    """Run all performance tests"""
    
    # First run search mode tests
    print("\n" + "="*100)
    print("STEP 1: TESTING SEARCH MODES")
    print("="*100)
    from test_search_modes import SearchModeTester
    search_tester = SearchModeTester()
    await search_tester.run_all_tests()
    
    # Wait a bit
    await asyncio.sleep(2)
    
    # Then run integration tests
    print("\n" + "="*100)
    print("STEP 2: RUNNING INTEGRATION TESTS")
    print("="*100)
    print("(Skipping for now - focus on search and performance)")
    
    # Finally run performance tests
    print("\n" + "="*100)
    print("STEP 3: PERFORMANCE TESTING")
    print("="*100)
    perf_tester = PerformanceTester()
    await perf_tester.run_load_test()

if __name__ == "__main__":
    asyncio.run(main())