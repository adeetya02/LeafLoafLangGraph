#!/usr/bin/env python3
"""
Test cart operations with proper session handling
"""

import asyncio
import httpx
import uuid
import json

async def test_cart_with_session():
    """Test cart operations in a single session"""
    
    print("="*80)
    print("CART OPERATIONS WITH SESSION TEST")
    print("="*80)
    
    base_url = "http://localhost:8080"
    session_id = str(uuid.uuid4())
    user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    
    print(f"\nSession ID: {session_id}")
    print(f"User ID: {user_id}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Search for spinach
        print("\n1. Searching for spinach...")
        search_resp = await client.post(
            f"{base_url}/api/v1/search",
            json={
                "query": "I need spinach",
                "session_id": session_id,
                "user_id": user_id
            }
        )
        search_data = search_resp.json()
        
        print(f"   ✓ Found {len(search_data.get('products', []))} products")
        print(f"   ✓ Intent: {search_data.get('conversation', {}).get('intent', 'unknown')}")
        print(f"   ✓ Response time: {search_data.get('execution', {}).get('total_time_ms', 0):.0f}ms")
        
        if search_data.get('products'):
            print("\n   Top 3 products:")
            for i, p in enumerate(search_data['products'][:3]):
                print(f"   {i+1}. {p['product_name']} (SKU: {p.get('sku', 'N/A')}) - ${p['price']:.2f}")
        
        # Step 2: Add first item to cart
        print("\n2. Adding first spinach to cart...")
        cart_resp = await client.post(
            f"{base_url}/api/v1/search",
            json={
                "query": "add the first spinach to my cart",
                "session_id": session_id,
                "user_id": user_id
            }
        )
        cart_data = cart_resp.json()
        
        print(f"   ✓ Success: {cart_data.get('success')}")
        print(f"   ✓ Intent: {cart_data.get('conversation', {}).get('intent', 'unknown')}")
        print(f"   ✓ Message: {cart_data.get('message')}")
        print(f"   ✓ Response time: {cart_data.get('execution', {}).get('total_time_ms', 0):.0f}ms")
        
        # Check if order data is in response
        if 'order' in cart_data:
            order = cart_data['order']
            print(f"\n   Cart contents:")
            if order.get('items'):
                for item in order['items']:
                    print(f"   - {item.get('name', 'Unknown')} x{item.get('quantity', 1)} - ${item.get('price', 0):.2f}")
                total = sum(item.get('price', 0) * item.get('quantity', 1) for item in order['items'])
                print(f"   Total: ${total:.2f}")
            else:
                print("   - Empty")
        
        # Step 3: Check cart
        print("\n3. Checking cart contents...")
        check_resp = await client.post(
            f"{base_url}/api/v1/search",
            json={
                "query": "what's in my cart?",
                "session_id": session_id,
                "user_id": user_id
            }
        )
        check_data = check_resp.json()
        
        print(f"   ✓ Intent: {check_data.get('conversation', {}).get('intent', 'unknown')}")
        print(f"   ✓ Message: {check_data.get('message')}")
        
        # Step 4: Add more items
        print("\n4. Adding more items...")
        more_resp = await client.post(
            f"{base_url}/api/v1/search",
            json={
                "query": "add 2 more spinach",
                "session_id": session_id,
                "user_id": user_id
            }
        )
        more_data = more_resp.json()
        
        print(f"   ✓ Intent: {more_data.get('conversation', {}).get('intent', 'unknown')}")
        print(f"   ✓ Message: {more_data.get('message')}")
        
        # Print reasoning steps
        print("\n5. Reasoning steps from last operation:")
        reasoning = more_data.get('execution', {}).get('reasoning_steps', [])
        for step in reasoning[:5]:  # First 5 steps
            print(f"   - {step}")
        
        print("\n✅ Test complete!")

if __name__ == "__main__":
    asyncio.run(test_cart_with_session())