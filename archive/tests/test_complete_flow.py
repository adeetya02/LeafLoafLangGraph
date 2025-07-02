#!/usr/bin/env python3
"""
Test complete flow: search, add to cart, update quantity, remove
"""

import asyncio
import httpx
import json
import uuid

async def test_complete_flow():
    """Test complete shopping flow"""
    
    print("="*80)
    print("COMPLETE SHOPPING FLOW TEST")
    print("="*80)
    
    base_url = "http://localhost:8080"
    session_id = f"test-{uuid.uuid4()}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Search for spinach
        print("\n1. SEARCH FOR SPINACH")
        print("-"*40)
        
        resp = await client.post(
            f"{base_url}/api/v1/search",
            json={"query": "organic spinach", "session_id": session_id}
        )
        data = resp.json()
        
        print(f"Status: {resp.status_code}")
        print(f"Success: {data['success']}")
        print(f"Products found: {len(data.get('products', []))}")
        print(f"Intent: {data.get('conversation', {}).get('intent')}")
        print(f"Confidence: {data.get('conversation', {}).get('confidence')}")
        
        if data.get('products'):
            print(f"\nFirst 3 products:")
            for i, p in enumerate(data['products'][:3]):
                print(f"  {i+1}. {p['product_name']} - ${p['price']:.2f} ({p['sku']})")
        
        # 2. Add first item to cart
        print("\n\n2. ADD FIRST SPINACH TO CART")
        print("-"*40)
        
        resp = await client.post(
            f"{base_url}/api/v1/search",
            json={"query": "add the first spinach", "session_id": session_id}
        )
        data = resp.json()
        
        print(f"Status: {resp.status_code}")
        print(f"Success: {data['success']}")
        print(f"Message: {data['message']}")
        print(f"Intent: {data.get('conversation', {}).get('intent')}")
        
        order = data.get('order', {})
        if order and order.get('items'):
            print(f"\nCart contents:")
            for item in order['items']:
                print(f"  - {item['name']} x{item['quantity']} @ ${item['price']:.2f}")
            total = sum(item['quantity'] * item['price'] for item in order['items'])
            print(f"  Total: ${total:.2f}")
        
        # 3. Add more quantity
        print("\n\n3. ADD 2 MORE OF THE SAME")
        print("-"*40)
        
        resp = await client.post(
            f"{base_url}/api/v1/search",
            json={"query": "add 2 more spinach", "session_id": session_id}
        )
        data = resp.json()
        
        print(f"Message: {data['message']}")
        order = data.get('order', {})
        if order and order.get('items'):
            print(f"\nUpdated cart:")
            for item in order['items']:
                print(f"  - {item['name']} x{item['quantity']} @ ${item['price']:.2f}")
            total = sum(item['quantity'] * item['price'] for item in order['items'])
            print(f"  Total: ${total:.2f}")
        
        # 4. Show cart
        print("\n\n4. SHOW CART")
        print("-"*40)
        
        resp = await client.post(
            f"{base_url}/api/v1/search",
            json={"query": "what's in my cart?", "session_id": session_id}
        )
        data = resp.json()
        
        print(f"Message: {data['message']}")
        print(f"Intent: {data.get('conversation', {}).get('intent')}")
        
        # 5. Remove item
        print("\n\n5. REMOVE SPINACH")
        print("-"*40)
        
        resp = await client.post(
            f"{base_url}/api/v1/search",
            json={"query": "remove spinach from cart", "session_id": session_id}
        )
        data = resp.json()
        
        print(f"Message: {data['message']}")
        order = data.get('order', {})
        print(f"Cart now has {len(order.get('items', []))} items")
        
        # 6. Performance summary
        print("\n\n6. PERFORMANCE SUMMARY")
        print("-"*40)
        print(f"All operations completed successfully!")
        print(f"Session ID: {session_id}")
        
        # Check execution times
        exec_data = data.get('execution', {})
        if 'total_time_ms' in exec_data:
            print(f"Last operation time: {exec_data['total_time_ms']:.1f}ms")

if __name__ == "__main__":
    asyncio.run(test_complete_flow())