#\!/usr/bin/env python3
"""
Detailed performance test showing alpha values and component breakdown
"""
import asyncio
import aiohttp
import time
import json
from typing import Dict, List, Any
from datetime import datetime

BASE_URL = "https://leafloaf-v2srnrkkhq-uc.a.run.app"

# Test queries with expected behaviors
TEST_QUERIES = [
    # Brand-specific (should use low alpha 0.1-0.3)
    {"query": "oatly barista", "type": "brand_specific", "expected_alpha": 0.1},
    {"query": "horizon organic", "type": "brand_specific", "expected_alpha": 0.1},
    
    # Product-specific (should use medium alpha 0.4-0.6)
    {"query": "organic milk", "type": "product_category", "expected_alpha": 0.5},
    {"query": "bell peppers", "type": "product_category", "expected_alpha": 0.5},
    {"query": "spinach", "type": "product_single", "expected_alpha": 0.5},
    
    # Exploratory (should use high alpha 0.7-0.9)
    {"query": "breakfast ideas", "type": "exploratory", "expected_alpha": 0.8},
    {"query": "healthy snacks", "type": "exploratory", "expected_alpha": 0.8},
    
    # Cart operations (no alpha needed)
    {"query": "add to cart", "type": "cart_add", "expected_alpha": 0},
    {"query": "show my cart", "type": "cart_list", "expected_alpha": 0},
    {"query": "remove that", "type": "cart_remove", "expected_alpha": 0},
    
    # Complex queries
    {"query": "organic oatly milk for coffee", "type": "complex_brand", "expected_alpha": 0.1},
    {"query": "what vegetables do you have", "type": "complex_exploratory", "expected_alpha": 0.7},
]

async def test_query(session: aiohttp.ClientSession, query_info: Dict[str, Any]) -> Dict[str, Any]:
    """Test a single query and return detailed metrics"""
    query = query_info["query"]
    
    headers = {"Content-Type": "application/json"}
    data = {
        "query": query,
        "session_id": f"perf-test-{int(time.time())}"
    }
    
    start_time = time.time()
    
    try:
        async with session.post(
            f"{BASE_URL}/api/v1/search",
            json=data,
            headers=headers
        ) as response:
            network_time = (time.time() - start_time) * 1000
            result = await response.json()
            
            # Extract key metrics
            execution = result.get("execution", {})
            metadata = result.get("metadata", {})
            conversation = result.get("conversation", {})
            
            agent_timings = execution.get("agent_timings", {})
            actual_alpha = metadata.get("search_config", {}).get("alpha", 0)
            intent = conversation.get("intent", "unknown")
            
            # Component breakdown
            supervisor_time = agent_timings.get("supervisor", 0)
            search_time = agent_timings.get("product_search", 0)
            order_time = agent_timings.get("order_agent", 0)
            compiler_time = agent_timings.get("response_compiler", 0)
            
            total_server_time = execution.get("total_time_ms", 0)
            network_overhead = network_time - total_server_time
            
            return {
                "query": query,
                "type": query_info["type"],
                "expected_alpha": query_info["expected_alpha"],
                "actual_alpha": actual_alpha,
                "intent": intent,
                "total_latency": network_time,
                "server_time": total_server_time,
                "network_overhead": network_overhead,
                "components": {
                    "supervisor": supervisor_time,
                    "product_search": search_time,
                    "order_agent": order_time,
                    "response_compiler": compiler_time
                },
                "products_found": len(result.get("products", [])),
                "cache_info": execution.get("reasoning_steps", []),
                "success": result.get("success", False)
            }
            
    except Exception as e:
        return {
            "query": query,
            "type": query_info["type"],
            "error": str(e),
            "total_latency": (time.time() - start_time) * 1000
        }

async def run_tests():
    """Run all tests and display results"""
    print("=" * 80)
    print("🔍 DETAILED PERFORMANCE ANALYSIS WITH ALPHA VALUES")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)
    
    async with aiohttp.ClientSession() as session:
        # Warm up
        print("\n🔥 Warming up service...")
        await test_query(session, {"query": "test", "type": "warmup", "expected_alpha": 0})
        
        print("\n📊 QUERY ANALYSIS:")
        print("-" * 80)
        
        results = []
        for query_info in TEST_QUERIES:
            result = await test_query(session, query_info)
            results.append(result)
            
            print(f"\n📝 Query: '{result['query']}' ({result['type']})")
            print(f"   Intent: {result.get('intent', 'unknown')}")
            print(f"   Alpha: Expected {result.get('expected_alpha', 'N/A')} → Actual {result.get('actual_alpha', 'N/A')}")
            
            if 'error' not in result:
                print(f"   Total latency: {result['total_latency']:.0f}ms")
                print(f"   Server time: {result['server_time']:.0f}ms")
                print(f"   Network overhead: {result['network_overhead']:.0f}ms")
                
                print("\n   Component breakdown:")
                components = result['components']
                for comp, time_ms in components.items():
                    if time_ms > 0:
                        pct = (time_ms / result['server_time'] * 100) if result['server_time'] > 0 else 0
                        print(f"     - {comp}: {time_ms:.0f}ms ({pct:.0f}%)")
                
                if result.get('cache_info'):
                    print(f"   Cache: {result['cache_info'][0]}")
                
                # Performance verdict
                if result['total_latency'] < 300:
                    print("   ✅ PASS: Under 300ms target")
                elif result['total_latency'] < 500:
                    print("   ⚠️  WARNING: 300-500ms")
                else:
                    print("   ❌ FAIL: Over 500ms")
            else:
                print(f"   ❌ ERROR: {result['error']}")
        
        # Summary by query type
        print("\n" + "=" * 80)
        print("📈 SUMMARY BY QUERY TYPE:")
        print("-" * 80)
        
        query_types = {}
        for result in results:
            if 'error' not in result:
                qtype = result['type']
                if qtype not in query_types:
                    query_types[qtype] = []
                query_types[qtype].append(result)
        
        for qtype, type_results in query_types.items():
            avg_latency = sum(r['total_latency'] for r in type_results) / len(type_results)
            avg_alpha = sum(r.get('actual_alpha', 0) for r in type_results) / len(type_results)
            
            print(f"\n{qtype}:")
            print(f"  Average latency: {avg_latency:.0f}ms")
            print(f"  Average alpha: {avg_alpha:.2f}")
            print(f"  Queries: {len(type_results)}")
        
        # Component performance
        print("\n" + "=" * 80)
        print("🔧 COMPONENT PERFORMANCE:")
        print("-" * 80)
        
        all_components = {}
        for result in results:
            if 'error' not in result and 'components' in result:
                for comp, time_ms in result['components'].items():
                    if comp not in all_components:
                        all_components[comp] = []
                    if time_ms > 0:
                        all_components[comp].append(time_ms)
        
        for comp, times in all_components.items():
            if times:
                avg_time = sum(times) / len(times)
                print(f"\n{comp}:")
                print(f"  Average: {avg_time:.0f}ms")
                print(f"  Min: {min(times):.0f}ms")
                print(f"  Max: {max(times):.0f}ms")
                print(f"  Calls: {len(times)}")

if __name__ == "__main__":
    asyncio.run(run_tests())
