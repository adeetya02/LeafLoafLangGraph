#!/usr/bin/env python3
"""
Test the complete order flow to debug where products are lost
"""

import asyncio
from src.core.graph import search_graph
from src.models.state import SearchState
import uuid
import json

async def test_order_flow():
    """Test search -> cart flow with detailed logging"""
    
    print("="*80)
    print("TESTING COMPLETE ORDER FLOW")
    print("="*80)
    
    session_id = str(uuid.uuid4())
    print(f"\nSession ID: {session_id}")
    
    # Step 1: Search for products
    print("\n1. SEARCH PHASE:")
    search_state = {
        'query': 'I need spinach',
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
    
    search_result = await search_graph.ainvoke(search_state)
    
    print(f"   Routing decision: {search_result.get('routing_decision')}")
    print(f"   Products found: {len(search_result.get('search_results', []))}")
    print(f"   Final response products: {len(search_result.get('final_response', {}).get('products', []))}")
    
    if search_result.get('search_results'):
        print("\n   Search results in state:")
        for i, p in enumerate(search_result['search_results'][:3]):
            print(f"   {i+1}. {p.get('name', 'Unknown')} (SKU: {p.get('sku', 'N/A')})")
    
    # Step 2: Add to cart
    print("\n2. CART PHASE:")
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
        'search_results': []  # Start empty to test session retrieval
    }
    
    cart_result = await search_graph.ainvoke(cart_state)
    
    print(f"   Routing decision: {cart_result.get('routing_decision')}")
    print(f"   Intent: {cart_result.get('intent')}")
    
    # Check what the order agent saw
    for msg in cart_result.get('messages', []):
        if msg.get('role') == 'assistant' and 'Using' in msg.get('content', ''):
            print(f"   Order agent: {msg['content']}")
    
    # Check tool calls
    for tool_call in cart_result.get('completed_tool_calls', []):
        if tool_call.get('name') == 'add_to_cart':
            args = tool_call.get('args', {})
            print(f"\n   add_to_cart was called with:")
            print(f"   - query: {args.get('query')}")
            print(f"   - search_results: {len(args.get('search_results', []))} products")
            print(f"   - current_order: {args.get('current_order', {})}")
    
    # Check final response
    final = cart_result.get('final_response', {})
    print(f"\n   Final response:")
    print(f"   - Success: {final.get('success')}")
    print(f"   - Message: {final.get('message')}")
    print(f"   - Order: {final.get('order', {})}")
    
    # Step 3: Check session memory directly
    print("\n3. CHECKING SESSION MEMORY:")
    from src.memory.memory_manager import memory_manager
    
    stored = await memory_manager.session_memory.get_recent_search_results(session_id)
    print(f"   Products in memory: {len(stored)}")
    
    session_data = await memory_manager.session_memory.get_session(session_id)
    print(f"   Session keys: {list(session_data.keys())}")
    
    print("\n✅ Test complete!")

if __name__ == "__main__":
    asyncio.run(test_order_flow())