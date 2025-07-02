#!/usr/bin/env python3
"""
Test the optimized supervisor performance
"""
import time
import asyncio
from src.agents.supervisor_optimized import OptimizedSupervisorAgent
from src.models.state import SearchState

def create_test_state(query: str, session_id: str = None) -> SearchState:
    """Create a test state"""
    return {
        "messages": [{"role": "human", "content": query}],
        "query": query,
        "session_id": session_id,
        "search_params": {},
        "reasoning": [],
        "agent_timings": {},
        "routing_decision": None,
        "should_search": False,
        "intent": None,
        "confidence": 0.0,
        "enhanced_query": None
    }

async def test_supervisor_performance():
    """Test optimized supervisor performance"""
    print("=" * 80)
    print("🚀 TESTING OPTIMIZED SUPERVISOR PERFORMANCE")
    print("=" * 80)
    
    supervisor = OptimizedSupervisorAgent()
    
    # Test queries
    test_queries = [
        # Cache hits (should be <20ms)
        ("add to cart", "Cache hit - cart operation"),
        ("oatly", "Cache hit - brand search"),
        ("breakfast ideas", "Cache hit - exploratory"),
        
        # Partial cache (should be <30ms)
        ("add 2 to cart", "Partial cache - cart"),
        ("oatly barista milk", "Partial cache - brand"),
        
        # Pattern match (should be <50ms)
        ("I need some milk", "Pattern - product search"),
        ("show me organic options", "Pattern - exploratory"),
        
        # Needs Gemma (should be <200ms)
        ("colorful bell peppers 3 pack", "Gemma - specific"),
        ("what's the cheapest spinach", "Gemma - price query"),
    ]
    
    print("\n📊 Testing various query types:")
    print("-" * 80)
    
    total_latencies = []
    
    for query, description in test_queries:
        # Test 3 times
        latencies = []
        
        for i in range(3):
            state = create_test_state(query, f"test-session-{i}")
            
            start = time.time()
            result_state = await supervisor._run(state)
            latency = (time.time() - start) * 1000
            latencies.append(latency)
            
            if i == 0:  # Print details for first run
                intent = result_state.get("intent", "unknown")
                alpha = result_state["search_params"].get("alpha", 0)
                routing = result_state.get("routing_decision", "unknown")
                
                print(f"\n'{query}' ({description})")
                print(f"  Intent: {intent} | Alpha: {alpha} | Route: {routing}")
                print(f"  Latencies: {[f'{l:.0f}ms' for l in latencies]}")
        
        avg_latency = sum(latencies) / len(latencies)
        total_latencies.extend(latencies)
        
        if avg_latency < 50:
            print(f"  ✅ FAST: Average {avg_latency:.0f}ms")
        elif avg_latency < 150:
            print(f"  ⚠️  OK: Average {avg_latency:.0f}ms")
        else:
            print(f"  ❌ SLOW: Average {avg_latency:.0f}ms")
    
    # Summary
    print("\n" + "=" * 80)
    print("📈 SUMMARY")
    print("=" * 80)
    
    if total_latencies:
        avg = sum(total_latencies) / len(total_latencies)
        print(f"Overall average: {avg:.0f}ms")
        print(f"Best: {min(total_latencies):.0f}ms")
        print(f"Worst: {max(total_latencies):.0f}ms")
        
        under_50 = sum(1 for l in total_latencies if l < 50)
        under_100 = sum(1 for l in total_latencies if l < 100)
        under_150 = sum(1 for l in total_latencies if l < 150)
        
        print(f"\nSuccess rates:")
        print(f"  Under 50ms: {under_50}/{len(total_latencies)} ({under_50/len(total_latencies)*100:.0f}%)")
        print(f"  Under 100ms: {under_100}/{len(total_latencies)} ({under_100/len(total_latencies)*100:.0f}%)")
        print(f"  Under 150ms: {under_150}/{len(total_latencies)} ({under_150/len(total_latencies)*100:.0f}%)")
    
    print("\n💡 Optimizations:")
    print("1. Exact cache matches: ~5-10ms")
    print("2. Partial cache matches: ~10-20ms")
    print("3. Pattern matching: ~20-50ms")
    print("4. Gemma with 150ms timeout: ~150-200ms")
    print("\n🎯 This should reduce total latency by 150-200ms!")

if __name__ == "__main__":
    asyncio.run(test_supervisor_performance())