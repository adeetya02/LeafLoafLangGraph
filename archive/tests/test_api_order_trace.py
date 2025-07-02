#!/usr/bin/env python3
"""
Trace the complete API flow for order operations
"""

import asyncio
import httpx
import json
import uuid
from src.api.main import create_initial_state
from src.core.graph import search_graph

async def test_api_order_trace():
    """Trace order operation through the complete flow"""
    
    print("="*80)
    print("API ORDER TRACE TEST")
    print("="*80)
    
    session_id = str(uuid.uuid4())
    
    # 1. First do a search to populate session memory
    print("\n1. SEARCH TO POPULATE MEMORY")
    search_state = create_initial_state(
        type('Request', (), {
            'query': 'spinach',
            'session_id': session_id,
            'user_id': None,
            'limit': 10,
            'filters': None,
            'preferences': None
        })(),
        0.5
    )
    
    search_result = await search_graph.ainvoke(search_state)
    print(f"Search found {len(search_result.get('search_results', []))} products")
    
    # 2. Now do an add to cart operation
    print("\n2. ADD TO CART OPERATION")
    cart_state = create_initial_state(
        type('Request', (), {
            'query': 'add spinach to my cart',
            'session_id': session_id,
            'user_id': None,
            'limit': 10,
            'filters': None,
            'preferences': None
        })(),
        0.5
    )
    
    print("\nInitial state keys:", list(cart_state.keys()))
    print("Initial current_order:", cart_state.get('current_order'))
    
    cart_result = await search_graph.ainvoke(cart_state)
    
    print("\n3. FINAL STATE ANALYSIS")
    print("Final state keys:", list(cart_result.keys()))
    print("Routing decision:", cart_result.get('routing_decision'))
    print("Current order in state:", cart_result.get('current_order'))
    print("Order metadata:", cart_result.get('order_metadata'))
    
    # Check final response
    final_response = cart_result.get('final_response', {})
    print("\n4. FINAL RESPONSE ANALYSIS")
    print("Final response keys:", list(final_response.keys()))
    print("Has order in final_response:", 'order' in final_response)
    if 'order' in final_response:
        order = final_response['order']
        print(f"Order items: {len(order.get('items', []))}")
        for item in order.get('items', []):
            print(f"  - {item['name']} x{item['quantity']} @ ${item['price']}")
    
    print("Message:", final_response.get('message'))
    print("Success:", final_response.get('success'))
    
    # Test via API endpoint
    print("\n5. TEST VIA API ENDPOINT")
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Search first
        await client.post(
            "http://localhost:8080/api/v1/search",
            json={"query": "spinach", "session_id": "api-" + session_id}
        )
        
        # Then add to cart
        resp = await client.post(
            "http://localhost:8080/api/v1/search",
            json={"query": "add spinach to cart", "session_id": "api-" + session_id}
        )
        
        data = resp.json()
        print("API response has order field:", 'order' in data)
        print("API order value:", data.get('order'))

if __name__ == "__main__":
    asyncio.run(test_api_order_trace())