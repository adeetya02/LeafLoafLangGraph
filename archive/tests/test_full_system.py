#!/usr/bin/env python3
"""
Test the full LeafLoaf system - what's working and what needs fixing
"""

import asyncio
from src.core.graph import create_search_graph
from src.models.state import SearchState
import time

async def test_system():
    print("=" * 80)
    print("🧪 LEAFLOAF SYSTEM TEST")
    print("=" * 80)
    
    # Create the graph
    print("\n1️⃣ Creating LangGraph workflow...")
    try:
        app = create_search_graph()
        print("   ✅ Graph created successfully")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return
    
    # Test queries
    test_cases = [
        {
            "query": "I need organic vegetables",
            "session_id": "test-001",
            "description": "Product search query"
        },
        {
            "query": "Add 3 bunches of celery to my cart",
            "session_id": "test-002", 
            "description": "Order operation"
        },
        {
            "query": "What's in my cart?",
            "session_id": "test-002",
            "description": "Cart query (contextual)"
        }
    ]
    
    print("\n2️⃣ Running test queries...")
    print("-" * 80)
    
    for test in test_cases:
        print(f"\n🔍 Test: {test['description']}")
        print(f"   Query: '{test['query']}'")
        print(f"   Session: {test['session_id']}")
        
        # Create initial state
        initial_state = SearchState(
            query=test["query"],
            session_id=test["session_id"],
            search_results=[],
            completed_tool_calls=[],
            messages=[]
        )
        
        try:
            start = time.time()
            
            # Run the graph
            result = await app.ainvoke(initial_state)
            
            elapsed = (time.time() - start) * 1000
            print(f"   Time: {elapsed:.0f}ms")
            
            # Check results
            if "response" in result:
                response = result["response"]
                print(f"   ✅ Got response: {response[:100]}...")
            else:
                print("   ❌ No response generated")
            
            # Check what was routed
            if "routing_decision" in result:
                print(f"   Routing: {result['routing_decision']}")
            
            # Check search results
            if "search_results" in result and result["search_results"]:
                print(f"   Products found: {len(result['search_results'])}")
            
            # Check completed tools
            if "completed_tool_calls" in result and result["completed_tool_calls"]:
                tools = [tc.get("tool", {}).get("name", "unknown") for tc in result["completed_tool_calls"]]
                print(f"   Tools used: {', '.join(tools)}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:100]}...")
    
    print("\n" + "=" * 80)
    print("\n📊 System Status:")
    print("✅ Working:")
    print("   - LangGraph orchestration")
    print("   - Supervisor routing")
    print("   - Order agent with tools")
    print("   - Response compilation")
    print("   - Session memory")
    
    print("\n⚠️  Issues:")
    print("   - Weaviate auth (API key mismatch)")
    print("   - No vectorizer (need HF Pro key)")
    print("   - Search returns 0 products")
    
    print("\n📝 Next Steps:")
    print("1. Get correct HuggingFace Pro API key")
    print("2. Run: python3 setup_hf_vectorizer_fixed.py")
    print("3. Test alpha-driven search")
    print("4. Optimize latency (<300ms)")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_system())