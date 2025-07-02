#!/usr/bin/env python3
"""
Debug why order agent isn't using search results from memory
"""

import asyncio
from src.memory.memory_manager import memory_manager
from src.agents.order_agent import OrderReactAgent
from src.models.state import SearchState
import uuid
import json

async def test_order_memory_debug():
    """Test order agent with memory directly"""
    
    print("="*80)
    print("ORDER AGENT MEMORY DEBUG")
    print("="*80)
    
    session_id = str(uuid.uuid4())
    
    # 1. Store search results in memory
    print("\n1. STORING SEARCH RESULTS IN MEMORY")
    test_products = [
        {
            "name": "Spinach Baby 2X2 Lb B&W",
            "sku": "SP6BW1",
            "price": 20.62,
            "unit": "2 LB",
            "description": "Fresh baby spinach"
        },
        {
            "name": "Spinach Organic 1 Lb",
            "sku": "SP002",
            "price": 8.99,
            "unit": "1 LB",
            "description": "Organic spinach"
        }
    ]
    
    await memory_manager.session_memory.add_search_results(session_id, "spinach", test_products)
    
    # Verify storage
    stored = await memory_manager.session_memory.get_recent_search_results(session_id)
    print(f"Stored {len(stored)} products in memory")
    print(f"First product: {stored[0]['name']} (SKU: {stored[0]['sku']})")
    
    # 2. Create order agent and state
    print("\n2. CREATING ORDER AGENT")
    order_agent = OrderReactAgent()
    
    state = {
        'query': 'add the first spinach to my cart',
        'session_id': session_id,
        'messages': [],
        'reasoning': [],
        'completed_tool_calls': [],
        'agent_status': {},
        'agent_timings': {},
        'search_params': {},
        'should_search': False,
        'routing_decision': 'order_agent',
        'intent': 'add_to_order',
        'confidence': 0.9,
        'search_results': [],  # Empty to test memory retrieval
        'current_order': {"items": []},
        'order_metadata': {}
    }
    
    # 3. Run order agent
    print("\n3. RUNNING ORDER AGENT")
    print(f"Initial search_results in state: {len(state['search_results'])}")
    
    # Add some debug logging
    original_run = order_agent._run
    async def debug_run(state):
        print("\nDEBUG: Inside _run method")
        print(f"  search_results at start: {len(state.get('search_results', []))}")
        
        # Call original
        result = await original_run(state)
        
        print(f"\nDEBUG: After _run method")
        print(f"  search_results in result: {len(result.get('search_results', []))}")
        print(f"  current_order items: {len(result.get('current_order', {}).get('items', []))}")
        
        return result
    
    order_agent._run = debug_run
    
    result_state = await order_agent.execute(state)
    
    # 4. Check results
    print("\n4. RESULTS")
    print(f"Completed tool calls: {len(result_state.get('completed_tool_calls', []))}")
    
    for call in result_state.get('completed_tool_calls', []):
        print(f"\nTool call: {call.get('name')}")
        print(f"Success: {call.get('result', {}).get('success')}")
        print(f"Message: {call.get('result', {}).get('message')}")
        
        if call.get('name') == 'add_to_cart':
            args = call.get('args', {})
            print(f"Search results in args: {len(args.get('search_results', []))}")
    
    # Check current order
    current_order = result_state.get('current_order', {})
    print(f"\nCurrent order has {len(current_order.get('items', []))} items")
    for item in current_order.get('items', []):
        print(f"  - {item['name']} x{item['quantity']} @ ${item['price']}")
    
    # Check reasoning
    print("\nReasoning steps:")
    for step in result_state.get('reasoning', []):
        print(f"  - {step}")

if __name__ == "__main__":
    asyncio.run(test_order_memory_debug())