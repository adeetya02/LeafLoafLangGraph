#!/usr/bin/env python3
"""
Focused test on cart operation latency
"""
import requests
import time
import statistics

BASE_URL = "https://leafloaf-32905605817.us-central1.run.app"

def test_cart_operations():
    """Test cart operations specifically"""
    print("=" * 80)
    print("🛒 CART OPERATIONS LATENCY TEST (Min Instances = 1)")
    print("=" * 80)
    
    session_id = f"cart-latency-{int(time.time())}"
    
    # Cart operation queries
    cart_queries = [
        "add that to my cart",
        "throw in 2 of those",
        "what's in my basket?",
        "yes please",
        "actually make it 3",
        "show my cart",
        "add some milk",
        "checkout"
    ]
    
    # Warm up with health checks
    print("\nWarming up...")
    for _ in range(3):
        requests.get(f"{BASE_URL}/health")
    
    print("\n📊 Testing cart operations:")
    print("-" * 80)
    
    latencies = []
    
    for query in cart_queries:
        # Test 3 times for consistency
        query_latencies = []
        
        for i in range(3):
            start = time.time()
            response = requests.post(
                f"{BASE_URL}/api/v1/search",
                json={"query": query, "session_id": session_id}
            )
            latency = (time.time() - start) * 1000
            query_latencies.append(latency)
            
            if i == 0 and response.status_code == 200:
                data = response.json()
                intent = data.get("conversation", {}).get("intent", "unknown")
                server_time = data.get("execution", {}).get("total_time_ms", 0)
                gemma_time = data.get("execution", {}).get("agent_timings", {}).get("supervisor", 0)
        
        avg_latency = statistics.mean(query_latencies)
        latencies.extend(query_latencies)
        
        print(f"\n'{query}'")
        print(f"  Intent: {intent}")
        print(f"  Latencies: {[f'{l:.0f}ms' for l in query_latencies]}")
        print(f"  Average: {avg_latency:.0f}ms")
        print(f"  Server time: {server_time:.0f}ms")
        print(f"  Gemma time: {gemma_time:.0f}ms")
        
        if avg_latency < 300:
            print(f"  ✅ PASS: Under 300ms!")
        elif avg_latency < 350:
            print(f"  ⚠️  OK: Under 350ms")
        else:
            print(f"  ❌ FAIL: Over 350ms")
    
    # Summary
    print("\n" + "=" * 80)
    print("📈 SUMMARY")
    print("=" * 80)
    
    if latencies:
        print(f"Overall average: {statistics.mean(latencies):.0f}ms")
        print(f"Best: {min(latencies):.0f}ms")
        print(f"Worst: {max(latencies):.0f}ms")
        print(f"P50: {statistics.median(latencies):.0f}ms")
        
        under_300 = sum(1 for l in latencies if l < 300)
        under_350 = sum(1 for l in latencies if l < 350)
        
        print(f"\nSuccess rate:")
        print(f"  Under 300ms: {under_300}/{len(latencies)} ({under_300/len(latencies)*100:.0f}%)")
        print(f"  Under 350ms: {under_350}/{len(latencies)} ({under_350/len(latencies)*100:.0f}%)")
    
    print("\n🔍 Analysis:")
    print("Min instances=1 should eliminate cold starts")
    print("Cart operations don't need Weaviate search")
    print("Should see consistent ~250-300ms latency")

if __name__ == "__main__":
    test_cart_operations()