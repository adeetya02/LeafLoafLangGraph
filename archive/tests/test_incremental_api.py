#!/usr/bin/env python3
"""
Incremental API testing - verify response at each stage
"""

import asyncio
import httpx
import json
import uuid

async def test_incremental_api():
    """Test API incrementally with detailed response checking"""
    
    print("="*80)
    print("INCREMENTAL API TESTING")
    print("="*80)
    
    base_url = "http://localhost:8080"
    session_id = str(uuid.uuid4())
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # STAGE 1: Test Search
        print("\n1. SEARCH OPERATION")
        print("-"*40)
        
        search_resp = await client.post(
            f"{base_url}/api/v1/search",
            json={
                "query": "I need spinach",
                "session_id": session_id
            }
        )
        
        print(f"Status: {search_resp.status_code}")
        search_data = search_resp.json()
        
        print("\nResponse structure:")
        for key in search_data.keys():
            value = search_data[key]
            if isinstance(value, list):
                print(f"  {key}: list with {len(value)} items")
            elif isinstance(value, dict):
                print(f"  {key}: dict with keys {list(value.keys())}")
            else:
                print(f"  {key}: {type(value).__name__} = {value}")
        
        print(f"\nProducts found: {len(search_data.get('products', []))}")
        if search_data.get('products'):
            first_product = search_data['products'][0]
            print(f"First product:")
            print(f"  Name: {first_product.get('product_name')}")
            print(f"  SKU: {first_product.get('sku')}")
            print(f"  Price: ${first_product.get('price', 0):.2f}")
        
        print(f"\nConversation:")
        print(f"  Intent: {search_data.get('conversation', {}).get('intent')}")
        print(f"  Confidence: {search_data.get('conversation', {}).get('confidence')}")
        
        # STAGE 2: Test Add to Cart
        print("\n\n2. ADD TO CART OPERATION")
        print("-"*40)
        
        add_resp = await client.post(
            f"{base_url}/api/v1/search",
            json={
                "query": "add the first spinach to my cart",
                "session_id": session_id
            }
        )
        
        print(f"Status: {add_resp.status_code}")
        add_data = add_resp.json()
        
        print("\nResponse structure:")
        for key in add_data.keys():
            value = add_data[key]
            if isinstance(value, list):
                print(f"  {key}: list with {len(value)} items")
            elif isinstance(value, dict):
                print(f"  {key}: dict with keys {list(value.keys())}")
            elif value is None:
                print(f"  {key}: None")
            else:
                print(f"  {key}: {type(value).__name__} = {value}")
        
        print(f"\nOrder data:")
        order = add_data.get('order')
        if order:
            print(f"  Order keys: {list(order.keys())}")
            items = order.get('items', [])
            print(f"  Items in cart: {len(items)}")
            for item in items:
                print(f"    - {item.get('name')} x{item.get('quantity')} @ ${item.get('price', 0):.2f}")
        else:
            print(f"  Order is: {order}")
        
        print(f"\nMessage: {add_data.get('message')}")
        print(f"Success: {add_data.get('success')}")
        
        # STAGE 3: Check Cart Status
        print("\n\n3. CHECK CART STATUS")
        print("-"*40)
        
        check_resp = await client.post(
            f"{base_url}/api/v1/search",
            json={
                "query": "what's in my cart?",
                "session_id": session_id
            }
        )
        
        check_data = check_resp.json()
        print(f"Status: {check_resp.status_code}")
        print(f"Message: {check_data.get('message')}")
        print(f"Order in response: {'order' in check_data}")
        
        # STAGE 4: Add More Items
        print("\n\n4. ADD MORE ITEMS (QUANTITY)")
        print("-"*40)
        
        more_resp = await client.post(
            f"{base_url}/api/v1/search",
            json={
                "query": "add 3 more spinach",
                "session_id": session_id
            }
        )
        
        more_data = more_resp.json()
        print(f"Status: {more_resp.status_code}")
        print(f"Message: {more_data.get('message')}")
        
        # STAGE 5: Remove Item
        print("\n\n5. REMOVE ITEM")
        print("-"*40)
        
        remove_resp = await client.post(
            f"{base_url}/api/v1/search",
            json={
                "query": "remove spinach from cart",
                "session_id": session_id
            }
        )
        
        remove_data = remove_resp.json()
        print(f"Status: {remove_resp.status_code}")
        print(f"Message: {remove_data.get('message')}")
        
        # Debug: Print full response for one operation
        print("\n\n6. DEBUG: Full response for add operation")
        print("-"*40)
        print(json.dumps(add_data, indent=2))

if __name__ == "__main__":
    asyncio.run(test_incremental_api())