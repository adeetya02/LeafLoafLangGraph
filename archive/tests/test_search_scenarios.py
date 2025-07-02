#!/usr/bin/env python3
"""
Comprehensive search testing for LeafLoaf with different alpha values
Tests semantic, hybrid, and keyword search across various query types
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Any
import httpx
from tabulate import tabulate

# Test configuration
BASE_URL = "https://leafloaf-32905605817.northamerica-northeast1.run.app"
LOCAL_URL = "http://localhost:8000"

# Use GCP deployment by default
API_URL = BASE_URL

# Test scenarios with recommended alpha values
SEARCH_SCENARIOS = [
    # Brand/Product Specific (Low alpha - keyword focused)
    {
        "category": "Brand Specific",
        "queries": [
            ("Oatly barista edition", 0.2),
            ("Horizon organic milk", 0.2),
            ("Nature's Path cereal", 0.2),
        ]
    },
    
    # Product + Attributes (Balanced)
    {
        "category": "Product + Attributes",
        "queries": [
            ("organic spinach", 0.5),
            ("gluten free bread", 0.5),
            ("low fat yogurt", 0.5),
            ("fresh basil", 0.5),
        ]
    },
    
    # Category Searches (Semantic leaning)
    {
        "category": "Category Search",
        "queries": [
            ("leafy greens", 0.7),
            ("root vegetables", 0.7),
            ("fresh herbs", 0.7),
            ("citrus fruits", 0.7),
        ]
    },
    
    # Exploratory/Semantic (High alpha)
    {
        "category": "Exploratory/Semantic",
        "queries": [
            ("healthy breakfast options", 0.85),
            ("ingredients for pasta salad", 0.85),
            ("sustainable produce choices", 0.85),
            ("iron rich vegetables", 0.85),
        ]
    },
    
    # Pure Semantic (Alpha = 1.0)
    {
        "category": "Pure Semantic",
        "queries": [
            ("foods that boost immunity", 1.0),
            ("mediterranean diet essentials", 1.0),
            ("plant based protein sources", 1.0),
        ]
    },
    
    # Pure Keyword (Alpha = 0.0)
    {
        "category": "Pure Keyword",
        "queries": [
            ("tomato", 0.0),
            ("apple", 0.0),
            ("lettuce", 0.0),
        ]
    }
]

# Cart and Order Agent test scenarios
AGENT_SCENARIOS = [
    # Add to cart tests
    {
        "category": "Add to Cart",
        "endpoint": "/api/v1/order",
        "queries": [
            "add 2 bunches of organic spinach to my cart",
            "I need 5 pounds of tomatoes",
            "add organic bananas and strawberries",
            "put 3 bell peppers in my order",
        ]
    },
    
    # Cart management tests
    {
        "category": "Cart Management",
        "endpoint": "/api/v1/order",
        "queries": [
            "show my cart",
            "what's in my order?",
            "remove spinach from cart",
            "update tomatoes to 3 pounds",
            "clear my cart",
        ]
    },
    
    # Order confirmation tests
    {
        "category": "Order Confirmation",
        "endpoint": "/api/v1/order",
        "queries": [
            "confirm my order",
            "checkout please",
            "finalize my shopping",
        ]
    }
]

class SearchTester:
    def __init__(self, api_url: str = API_URL):
        self.api_url = api_url
        self.session_id = f"test-session-{int(time.time())}"
        self.results = []
        
    async def test_search(self, query: str, alpha: float) -> Dict[str, Any]:
        """Test a single search query with specified alpha"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                start_time = time.time()
                
                # Prepare request
                payload = {
                    "query": query,
                    "alpha": alpha,
                    "session_id": self.session_id
                }
                
                # Make request
                response = await client.post(
                    f"{self.api_url}/api/v1/search",
                    json=payload
                )
                
                elapsed_ms = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    data = response.json()
                    
                    result = {
                        "query": query,
                        "alpha": alpha,
                        "success": data.get("success", False),
                        "product_count": len(data.get("products", [])),
                        "products": data.get("products", [])[:3],  # First 3 products
                        "latency_ms": elapsed_ms,
                        "search_type": data.get("metadata", {}).get("search_config", {}).get("search_type", "hybrid"),
                        "error": data.get("error"),
                        "trace_url": data.get("langsmith_trace_url")
                    }
                else:
                    result = {
                        "query": query,
                        "alpha": alpha,
                        "success": False,
                        "product_count": 0,
                        "products": [],
                        "latency_ms": elapsed_ms,
                        "error": f"HTTP {response.status_code}: {response.text[:200]}"
                    }
                
                return result
                
            except Exception as e:
                return {
                    "query": query,
                    "alpha": alpha,
                    "success": False,
                    "product_count": 0,
                    "products": [],
                    "latency_ms": 0,
                    "error": str(e)
                }
    
    async def test_agent(self, query: str, endpoint: str) -> Dict[str, Any]:
        """Test agent endpoints (order/cart management)"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                start_time = time.time()
                
                payload = {
                    "query": query,
                    "session_id": self.session_id
                }
                
                response = await client.post(
                    f"{self.api_url}{endpoint}",
                    json=payload
                )
                
                elapsed_ms = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "query": query,
                        "success": data.get("success", False),
                        "message": data.get("message", ""),
                        "cart_items": len(data.get("cart", {}).get("items", [])),
                        "latency_ms": elapsed_ms,
                        "agent_used": data.get("execution", {}).get("agent_timings", {})
                    }
                else:
                    return {
                        "query": query,
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                        "latency_ms": elapsed_ms
                    }
                    
            except Exception as e:
                return {
                    "query": query,
                    "success": False,
                    "error": str(e),
                    "latency_ms": 0
                }
    
    async def run_all_tests(self):
        """Run all search and agent tests"""
        print(f"\n🧪 Testing LeafLoaf Search & Agents at {self.api_url}")
        print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔑 Session ID: {self.session_id}\n")
        
        # Test search scenarios
        print("=" * 80)
        print("SEARCH TESTS - Testing Different Alpha Values")
        print("=" * 80)
        
        all_search_results = []
        
        for scenario in SEARCH_SCENARIOS:
            print(f"\n📊 {scenario['category']}")
            print("-" * 40)
            
            results = []
            for query, alpha in scenario['queries']:
                result = await self.test_search(query, alpha)
                results.append(result)
                
                # Display result
                status = "✅" if result['success'] and result['product_count'] > 0 else "❌"
                print(f"{status} '{query}' (α={alpha}): {result['product_count']} products, {result['latency_ms']:.0f}ms")
                
                if result['products']:
                    for p in result['products'][:2]:
                        print(f"   - {p.get('name', 'Unknown')}")
                
                if result.get('error'):
                    print(f"   ⚠️ Error: {result['error']}")
            
            all_search_results.extend(results)
        
        # Test agent scenarios
        print("\n" + "=" * 80)
        print("AGENT TESTS - Cart and Order Management")
        print("=" * 80)
        
        all_agent_results = []
        
        for scenario in AGENT_SCENARIOS:
            print(f"\n🛒 {scenario['category']}")
            print("-" * 40)
            
            for query in scenario['queries']:
                result = await self.test_agent(query, scenario['endpoint'])
                all_agent_results.append(result)
                
                status = "✅" if result['success'] else "❌"
                print(f"{status} '{query}': {result['latency_ms']:.0f}ms")
                
                if result.get('message'):
                    print(f"   → {result['message'][:100]}")
                if result.get('cart_items'):
                    print(f"   🛒 Cart items: {result['cart_items']}")
                if result.get('error'):
                    print(f"   ⚠️ Error: {result['error']}")
        
        # Save results
        self.save_results(all_search_results, all_agent_results)
        
        # Display summary
        self.display_summary(all_search_results, all_agent_results)
    
    def save_results(self, search_results: List[Dict], agent_results: List[Dict]):
        """Save test results to file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"search_test_results_{timestamp}.json"
        
        data = {
            "test_date": datetime.now().isoformat(),
            "api_url": self.api_url,
            "session_id": self.session_id,
            "search_results": search_results,
            "agent_results": agent_results,
            "summary": {
                "total_searches": len(search_results),
                "successful_searches": sum(1 for r in search_results if r['success'] and r['product_count'] > 0),
                "avg_search_latency": sum(r['latency_ms'] for r in search_results) / len(search_results) if search_results else 0,
                "total_agent_tests": len(agent_results),
                "successful_agent_tests": sum(1 for r in agent_results if r['success']),
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\n💾 Results saved to: {filename}")
    
    def display_summary(self, search_results: List[Dict], agent_results: List[Dict]):
        """Display test summary"""
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        # Search summary
        total_searches = len(search_results)
        successful_searches = sum(1 for r in search_results if r['success'] and r['product_count'] > 0)
        avg_latency = sum(r['latency_ms'] for r in search_results) / total_searches if total_searches > 0 else 0
        
        print(f"\n🔍 Search Tests:")
        print(f"   Total: {total_searches}")
        print(f"   Successful: {successful_searches} ({successful_searches/total_searches*100:.1f}%)")
        print(f"   Average Latency: {avg_latency:.0f}ms")
        
        # Alpha performance analysis
        alpha_groups = {}
        for r in search_results:
            alpha = r['alpha']
            if alpha not in alpha_groups:
                alpha_groups[alpha] = {'count': 0, 'success': 0, 'total_products': 0}
            alpha_groups[alpha]['count'] += 1
            if r['success'] and r['product_count'] > 0:
                alpha_groups[alpha]['success'] += 1
                alpha_groups[alpha]['total_products'] += r['product_count']
        
        print("\n📈 Performance by Alpha Value:")
        headers = ["Alpha", "Tests", "Success Rate", "Avg Products"]
        rows = []
        for alpha in sorted(alpha_groups.keys()):
            group = alpha_groups[alpha]
            success_rate = group['success'] / group['count'] * 100 if group['count'] > 0 else 0
            avg_products = group['total_products'] / group['success'] if group['success'] > 0 else 0
            rows.append([alpha, group['count'], f"{success_rate:.1f}%", f"{avg_products:.1f}"])
        
        print(tabulate(rows, headers=headers, tablefmt="grid"))
        
        # Agent summary
        total_agent_tests = len(agent_results)
        successful_agent_tests = sum(1 for r in agent_results if r['success'])
        
        print(f"\n🤖 Agent Tests:")
        print(f"   Total: {total_agent_tests}")
        print(f"   Successful: {successful_agent_tests} ({successful_agent_tests/total_agent_tests*100:.1f}%)")
        
        print("\n✅ Test run complete!")

async def main():
    """Run all tests"""
    tester = SearchTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())