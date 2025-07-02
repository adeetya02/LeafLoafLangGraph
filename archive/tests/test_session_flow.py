#!/usr/bin/env python3
"""
Test complete session flow to debug contextual cart operations
"""

import asyncio
import uuid
import json
from src.memory.session_memory import SessionMemory
from src.agents.order_agent import OrderReactAgent
from src.models.state import SearchState

async def test_session_flow():
    """Test the complete flow from search to cart operations"""
    
    print("="*80)
    print("TESTING COMPLETE SESSION FLOW")
    print("="*80)
    
    # Initialize components
    memory = SessionMemory()
    order_agent = OrderReactAgent()
    # Use the same memory instance for order agent
    order_agent.session_memory = memory
    session_id = str(uuid.uuid4())
    
    # Test products (simulating what would come from search)
    test_products = [
        {
            "sku": "SP6BW1",
            "name": "Spinach Baby",
            "price": 20.62,
            "unit": "Case",
            "size": "4/3 LB",
            "brand": "Local Farms",
            "category": "Vegetables",
            "description": "Fresh baby spinach, triple washed"
        },
        {
            "sku": "SP93",
            "name": "Spinach Triple Washed",
            "price": 26.56,
            "unit": "Case", 
            "size": "12/10 OZ",
            "brand": "Green Valley",
            "category": "Vegetables",
            "description": "Premium triple washed spinach"
        }
    ]
    
    # Step 1: Store search results in session memory
    print("\n1. Storing search results in session memory:")
    print(f"   Session ID: {session_id}")
    await memory.add_search_results(session_id, "spinach", test_products)
    
    # Verify storage
    retrieved = await memory.get_recent_search_results(session_id)
    print(f"   Stored {len(retrieved)} products")
    for p in retrieved:
        print(f"   - {p['name']} (SKU: {p['sku']})")
    
    # Step 2: Check what session memory returns
    print("\n2. Checking full session data:")
    session_data = await memory.get_session(session_id)
    print(f"   Session keys: {list(session_data.keys())}")
    if "last_search_results" in session_data:
        print(f"   Last search has {len(session_data['last_search_results'])} products")
    if "recent_searches" in session_data:
        print(f"   Recent searches: {len(session_data['recent_searches'])}")
    
    # Step 3: Test order agent's intent analysis
    print("\n3. Testing order agent intent analysis:")
    query = "add the first spinach to my cart"
    current_order = {"items": []}
    
    intent = order_agent._analyze_order_intent(query.lower(), current_order, retrieved)
    print(f"   Query: '{query}'")
    print(f"   Intent: {intent}")
    
    # Step 4: Test order agent tool planning with search results
    print("\n4. Testing order agent tool planning:")
    state = SearchState(
        query=query,
        session_id=session_id,
        messages=[],
        routing_decision="order_agent",
        search_results=[],  # Empty in state
        reasoning=[],
        completed_tool_calls=[]
    )
    
    tool_plan = order_agent._plan_order_tools(state, query, current_order, retrieved, 1)
    print(f"   Reasoning: {tool_plan['reasoning']}")
    print(f"   Tool calls: {len(tool_plan['tool_calls'])}")
    if tool_plan['tool_calls']:
        for tc in tool_plan['tool_calls']:
            print(f"   - {tc['name']} with args keys: {list(tc['args'].keys())}")
            if 'search_results' in tc['args']:
                print(f"     Search results: {len(tc['args']['search_results'])} products")
    
    # Step 5: Test the full order agent execution
    print("\n5. Testing full order agent execution:")
    full_state = SearchState(
        query="add spinach to my cart",
        session_id=session_id,
        messages=[],
        routing_decision="order_agent",
        search_results=[],  # Empty - should pull from session
        reasoning=[],
        completed_tool_calls=[]
    )
    
    # Execute order agent
    result_state = await order_agent._run(full_state)
    
    print(f"   Messages added: {len(result_state['messages'])}")
    print(f"   Reasoning entries: {len(result_state['reasoning'])}")
    print(f"   Current order: {result_state.get('current_order', {})}")
    
    # Print detailed reasoning and messages
    print("\n   Detailed execution:")
    for i, reason in enumerate(result_state['reasoning']):
        print(f"   Reasoning {i+1}: {reason}")
    
    for i, msg in enumerate(result_state['messages']):
        if msg['role'] == 'assistant' and msg.get('tool_calls'):
            print(f"   Message {i+1}: Tool call - {msg['tool_calls'][0]['name'] if msg['tool_calls'] else 'none'}")
    
    # Check if products were retrieved from session
    for msg in result_state['messages']:
        if msg['content'] and 'recent search' in msg['content']:
            print(f"   ✓ Found message about using recent search")
    
    # Step 6: Test with search results in state (comparison)
    print("\n6. Testing with search results in state:")
    state_with_results = SearchState(
        query="add spinach to my cart",
        session_id=session_id,
        messages=[],
        routing_decision="order_agent",
        search_results=test_products,  # Products in state
        reasoning=[],
        completed_tool_calls=[]
    )
    
    result_with_products = await order_agent._run(state_with_results)
    print(f"   Current order items: {len(result_with_products.get('current_order', {}).get('items', []))}")
    
    print("\n✅ Session flow test complete!")

if __name__ == "__main__":
    asyncio.run(test_session_flow())