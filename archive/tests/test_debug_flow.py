#!/usr/bin/env python3
"""
Debug the complete flow to understand where the API response breaks
"""

import asyncio
from src.core.graph import search_graph
from src.models.state import SearchState
from src.memory.memory_manager import memory_manager
import uuid
import json

async def test_debug_flow():
    """Test with detailed debugging at each stage"""
    
    print("="*80)
    print("DEBUGGING COMPLETE FLOW")
    print("="*80)
    
    session_id = str(uuid.uuid4())
    print(f"\nSession ID: {session_id}")
    
    # STEP 1: Search directly with graph
    print("\n1. SEARCH WITH GRAPH:")
    search_state = {
        'query': 'spinach',
        'session_id': session_id,
        'messages': [],
        'reasoning': [],
        'completed_tool_calls': [],
        'agent_status': {},
        'agent_timings': {},
        'search_params': {},
        'should_search': False,
        'routing_decision': None,
        'intent': None,
        'confidence': 0.0
    }
    
    result1 = await search_graph.ainvoke(search_state)
    
    print(f"   Final response keys: {list(result1.get('final_response', {}).keys())}")
    print(f"   Products in state: {len(result1.get('search_results', []))}")
    print(f"   Products in final_response: {len(result1.get('final_response', {}).get('products', []))}")
    
    # Check memory
    print("\n2. CHECK SESSION MEMORY:")
    stored = await memory_manager.session_memory.get_recent_search_results(session_id)
    print(f"   Products in memory: {len(stored)}")
    if stored:
        print(f"   First product in memory: {stored[0].get('name')} (SKU: {stored[0].get('sku')})")
    
    # STEP 2: Add to cart with graph
    print("\n3. ADD TO CART WITH GRAPH:")
    cart_state = {
        'query': 'add the first spinach to my cart',
        'session_id': session_id,
        'messages': [],
        'reasoning': [],
        'completed_tool_calls': [],
        'agent_status': {},
        'agent_timings': {},
        'search_params': {},
        'should_search': False,
        'routing_decision': None,
        'intent': None,
        'confidence': 0.0,
        'search_results': []  # Empty to test memory retrieval
    }
    
    result2 = await search_graph.ainvoke(cart_state)
    
    print(f"   Routing decision: {result2.get('routing_decision')}")
    print(f"   Final response keys: {list(result2.get('final_response', {}).keys())}")
    
    final_resp = result2.get('final_response', {})
    print(f"   Success: {final_resp.get('success')}")
    print(f"   Message: {final_resp.get('message')}")
    print(f"   Has order: {'order' in final_resp}")
    
    if 'order' in final_resp:
        order = final_resp['order']
        print(f"   Order items: {len(order.get('items', []))}")
        for item in order.get('items', []):
            print(f"     - {item['name']} x{item['quantity']} @ ${item['price']:.2f}")
    
    # Check agent status
    print("\n4. AGENT EXECUTION:")
    for agent, status in result2.get('agent_status', {}).items():
        print(f"   {agent}: {status}")
    
    # Check tool calls
    print("\n5. TOOL CALLS:")
    for tool_call in result2.get('completed_tool_calls', []):
        print(f"   Tool: {tool_call.get('name')}")
        print(f"   Success: {tool_call.get('result', {}).get('success')}")
        if tool_call.get('name') == 'add_to_cart':
            args = tool_call.get('args', {})
            print(f"   Search results in args: {len(args.get('search_results', []))}")
    
    # STEP 3: Test API endpoint
    print("\n6. TEST VIA API:")
    import httpx
    
    async with httpx.AsyncClient() as client:
        # Search first
        search_api = await client.post(
            "http://localhost:8080/api/v1/search",
            json={"query": "spinach", "session_id": "api-test-1"}
        )
        print(f"   Search status: {search_api.status_code}")
        
        # Then add to cart
        cart_api = await client.post(
            "http://localhost:8080/api/v1/search",
            json={"query": "add spinach to cart", "session_id": "api-test-1"}
        )
        cart_data = cart_api.json()
        
        print(f"   Cart status: {cart_api.status_code}")
        print(f"   Order in API response: {cart_data.get('order')}")
        print(f"   Conversation in API response: {cart_data.get('conversation')}")
    
    print("\n✅ Debug complete!")

if __name__ == "__main__":
    asyncio.run(test_debug_flow())