"""
Comprehensive test suite for LeafLoaf LangGraph API with latency tracking
Tests 10 scenarios across search, add, update, and confirm operations
"""
import asyncio
import httpx
import json
import time
from typing import Dict, List
from datetime import datetime

# API base URL - update to ngrok URL if testing webhooks
API_BASE = "http://localhost:8080/api/v1"

class TestScenarios:
    def __init__(self):
        self.session_id = "test-session-001"
        self.user_id = "test-user-001"
        self.results = []
        
    async def run_test(self, name: str, endpoint: str, payload: Dict) -> Dict:
        """Run a single test and return results with timing"""
        print(f"\n{'='*60}")
        print(f"TEST: {name}")
        print(f"{'='*60}")
        print(f"Endpoint: {endpoint}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(endpoint, json=payload)
                
                end_time = time.time()
                latency = (end_time - start_time) * 1000  # Convert to ms
                
                print(f"Status: {response.status_code}")
                print(f"Latency: {latency:.2f}ms")
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"Response: {json.dumps(result, indent=2)[:500]}...")
                    
                    test_result = {
                        "name": name,
                        "success": True,
                        "latency_ms": latency,
                        "status_code": response.status_code,
                        "data": result
                    }
                else:
                    print(f"Error: {response.text}")
                    test_result = {
                        "name": name,
                        "success": False,
                        "latency_ms": latency,
                        "status_code": response.status_code,
                        "error": response.text
                    }
                
                self.results.append(test_result)
                return test_result
                    
        except Exception as e:
            end_time = time.time()
            latency = (end_time - start_time) * 1000
            
            print(f"Exception: {str(e)}")
            test_result = {
                "name": name,
                "success": False,
                "latency_ms": latency,
                "error": str(e)
            }
            self.results.append(test_result)
            return test_result
    
    async def run_all_tests(self):
        """Run all test scenarios"""
        print("Starting comprehensive API tests with latency tracking...")
        print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Test 1: Basic product search
        await self.run_test(
            "1. Basic Search - Organic Oat Milk",
            f"{API_BASE}/search",
            {
                "query": "organic oat milk",
                "session_id": self.session_id,
                "user_id": self.user_id
            }
        )
        
        # Test 2: Brand-specific search
        await self.run_test(
            "2. Brand Search - Oatly Barista Edition",
            f"{API_BASE}/search",
            {
                "query": "Oatly barista edition",
                "session_id": self.session_id,
                "user_id": self.user_id
            }
        )
        
        # Test 3: Category search
        await self.run_test(
            "3. Category Search - Breakfast Items",
            f"{API_BASE}/search",
            {
                "query": "breakfast cereals organic",
                "session_id": self.session_id,
                "user_id": self.user_id
            }
        )
        
        # Test 4: Add single item to cart
        await self.run_test(
            "4. Add to Cart - Single Item",
            f"{API_BASE}/search",
            {
                "query": "add 2 cartons of organic oat milk to my cart",
                "session_id": self.session_id,
                "user_id": self.user_id
            }
        )
        
        # Test 5: Add multiple items
        await self.run_test(
            "5. Add to Cart - Multiple Items",
            f"{API_BASE}/search",
            {
                "query": "add organic bananas, almond milk, and whole grain bread",
                "session_id": self.session_id,
                "user_id": self.user_id
            }
        )
        
        # Test 6: View cart
        await self.run_test(
            "6. View Cart",
            f"{API_BASE}/search",
            {
                "query": "show me what's in my cart",
                "session_id": self.session_id,
                "user_id": self.user_id
            }
        )
        
        # Test 7: Update quantity
        await self.run_test(
            "7. Update Quantity",
            f"{API_BASE}/search",
            {
                "query": "change the oat milk quantity to 3",
                "session_id": self.session_id,
                "user_id": self.user_id
            }
        )
        
        # Test 8: Remove item
        await self.run_test(
            "8. Remove Item",
            f"{API_BASE}/search",
            {
                "query": "remove bananas from my cart",
                "session_id": self.session_id,
                "user_id": self.user_id
            }
        )
        
        # Test 9: Confirm order
        await self.run_test(
            "9. Confirm Order",
            f"{API_BASE}/search",
            {
                "query": "confirm my order",
                "session_id": self.session_id,
                "user_id": self.user_id
            }
        )
        
        # Test 10: Complex conversational flow
        await self.run_test(
            "10. Complex Query - Dietary Preferences",
            f"{API_BASE}/search",
            {
                "query": "I need gluten-free pasta and dairy-free cheese for dinner",
                "session_id": self.session_id,
                "user_id": self.user_id
            }
        )
        
        print(f"\n{'='*60}")
        print("ALL TESTS COMPLETED")
        print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        self.generate_report()
    
    def generate_report(self):
        """Generate comprehensive test report"""
        report = []
        report.append("\n" + "="*80)
        report.append("LEAFLOAF LANGGRAPH API TEST REPORT")
        report.append("="*80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Summary statistics
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r.get("success", False))
        failed_tests = total_tests - successful_tests
        
        latencies = [r["latency_ms"] for r in self.results if "latency_ms" in r]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        min_latency = min(latencies) if latencies else 0
        max_latency = max(latencies) if latencies else 0
        
        report.append("SUMMARY")
        report.append("-" * 40)
        report.append(f"Total Tests: {total_tests}")
        report.append(f"Successful: {successful_tests} ({successful_tests/total_tests*100:.1f}%)")
        report.append(f"Failed: {failed_tests} ({failed_tests/total_tests*100:.1f}%)")
        report.append("")
        report.append("LATENCY METRICS")
        report.append("-" * 40)
        report.append(f"Average Latency: {avg_latency:.2f}ms")
        report.append(f"Min Latency: {min_latency:.2f}ms")
        report.append(f"Max Latency: {max_latency:.2f}ms")
        report.append("")
        
        # Detailed results
        report.append("DETAILED RESULTS")
        report.append("-" * 40)
        
        for i, result in enumerate(self.results, 1):
            report.append(f"\n{i}. {result['name']}")
            report.append(f"   Status: {'✅ PASS' if result.get('success') else '❌ FAIL'}")
            report.append(f"   Latency: {result.get('latency_ms', 0):.2f}ms")
            
            if result.get('success'):
                # Extract key information from response
                data = result.get('data', {})
                if 'result' in data:
                    if 'products' in data['result']:
                        report.append(f"   Products Found: {len(data['result']['products'])}")
                    if 'message' in data['result']:
                        report.append(f"   Message: {data['result']['message']}")
                    if 'order' in data['result']:
                        order = data['result']['order']
                        report.append(f"   Order Items: {len(order.get('items', []))}")
                        report.append(f"   Total: ${order.get('total', 0):.2f}")
            else:
                report.append(f"   Error: {result.get('error', 'Unknown error')}")
        
        # Performance analysis
        report.append("\n" + "="*40)
        report.append("PERFORMANCE ANALYSIS")
        report.append("="*40)
        
        # Group by latency ranges
        fast = sum(1 for l in latencies if l < 1000)
        medium = sum(1 for l in latencies if 1000 <= l < 3000)
        slow = sum(1 for l in latencies if l >= 3000)
        
        report.append(f"Fast (<1s): {fast} requests")
        report.append(f"Medium (1-3s): {medium} requests")
        report.append(f"Slow (>3s): {slow} requests")
        
        # Recommendations
        report.append("\n" + "="*40)
        report.append("RECOMMENDATIONS")
        report.append("="*40)
        
        if avg_latency > 2000:
            report.append("⚠️  Average latency is high (>2s). Consider:")
            report.append("   - Caching frequently searched products")
            report.append("   - Optimizing LLM calls with smaller models")
            report.append("   - Using Redis for session memory")
        
        if failed_tests > 0:
            report.append(f"⚠️  {failed_tests} tests failed. Review error logs.")
        
        if successful_tests == total_tests:
            report.append("✅ All tests passed successfully!")
        
        # Save report
        report_text = "\n".join(report)
        
        with open("test_report.txt", "w") as f:
            f.write(report_text)
        
        print(report_text)
        print("\n📄 Report saved to: test_report.txt")

async def main():
    tester = TestScenarios()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())