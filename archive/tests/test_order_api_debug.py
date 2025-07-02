#!/usr/bin/env python3
"""
Debug exactly why order data isn't showing in API response
"""

import asyncio
import httpx
import json
import uuid

async def test_order_api_debug():
    """Test order operations with detailed debugging"""
    
    print("="*80)
    print("ORDER API DEBUG TEST")
    print("="*80)
    
    base_url = "http://localhost:8080"
    session_id = str(uuid.uuid4())
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. First search for products
        print("\n1. SEARCH FOR PRODUCTS")
        search_resp = await client.post(
            f"{base_url}/api/v1/search",
            json={
                "query": "spinach",
                "session_id": session_id
            }
        )
        
        search_data = search_resp.json()
        print(f"Found {len(search_data.get('products', []))} products")
        if search_data.get('products'):
            print(f"First product: {search_data['products'][0]['product_name']} (SKU: {search_data['products'][0]['sku']})")
        
        # 2. Add to cart - direct and simple
        print("\n2. ADD TO CART - SIMPLE")
        add_resp = await client.post(
            f"{base_url}/api/v1/search",
            json={
                "query": "add spinach",
                "session_id": session_id
            }
        )
        
        add_data = add_resp.json()
        print(f"\nResponse keys: {list(add_data.keys())}")
        print(f"Order field exists: {'order' in add_data}")
        print(f"Order value: {add_data.get('order')}")
        print(f"Message: {add_data.get('message')}")
        print(f"Success: {add_data.get('success')}")
        
        # Print conversation data
        print(f"\nConversation data:")
        conv = add_data.get('conversation', {})
        print(f"  Intent: {conv.get('intent')}")
        print(f"  Confidence: {conv.get('confidence')}")
        
        # 3. Try with more explicit language
        print("\n3. ADD TO CART - EXPLICIT")
        add2_resp = await client.post(
            f"{base_url}/api/v1/search",
            json={
                "query": "add the spinach to my cart",
                "session_id": session_id
            }
        )
        
        add2_data = add2_resp.json()
        print(f"\nOrder field exists: {'order' in add2_data}")
        print(f"Order value: {add2_data.get('order')}")
        
        # 4. Check the execution data
        print("\n4. EXECUTION DETAILS")
        exec_data = add2_data.get('execution', {})
        print(f"Agents run: {exec_data.get('agents_run', [])}")
        print(f"Agent timings: {exec_data.get('agent_timings', {})}")
        
        # Print reasoning steps
        print("\nReasoning steps:")
        for step in exec_data.get('reasoning_steps', []):
            print(f"  - {step}")

if __name__ == "__main__":
    asyncio.run(test_order_api_debug())