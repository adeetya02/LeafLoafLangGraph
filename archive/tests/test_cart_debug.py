#!/usr/bin/env python3
"""
Debug contextual cart operations
"""

import asyncio
import httpx
import uuid

async def test_cart_operation():
    """Test a single cart operation flow with debug output"""
    
    print("="*80)
    print("CART OPERATION DEBUG TEST")
    print("="*80)
    
    base_url = "http://localhost:8080"
    session_id = str(uuid.uuid4())
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Step 1: Search for spinach
        print("\n1. Searching for spinach...")
        search_response = await client.post(
            f"{base_url}/api/v1/search",
            json={
                "query": "I need spinach",
                "session_id": session_id
            }
        )
        
        search_data = search_response.json()
        print(f"   Status: {search_response.status_code}")
        print(f"   Products found: {len(search_data.get('products', []))}")
        print(f"   Success: {search_data.get('success')}")
        
        # Step 2: Add to cart
        print("\n2. Adding to cart...")
        cart_response = await client.post(
            f"{base_url}/api/v1/search",
            json={
                "query": "add the first one to my cart",
                "session_id": session_id
            }
        )
        
        cart_data = cart_response.json()
        print(f"   Status: {cart_response.status_code}")
        print(f"   Response keys: {list(cart_data.keys())}")
        print(f"   Success: {cart_data.get('success')}")
        print(f"   Message: {cart_data.get('message')}")
        
        # Print order details if present
        if 'order' in cart_data:
            print(f"   Order: {cart_data['order']}")
        
        # Print full response for debugging
        print("\n3. Full cart response:")
        import json
        print(json.dumps(cart_data, indent=2))
        
        # Check what's in messages
        if 'execution' in cart_data and 'reasoning_steps' in cart_data['execution']:
            print("\n4. Reasoning steps:")
            for step in cart_data['execution']['reasoning_steps']:
                print(f"   - {step}")

if __name__ == "__main__":
    asyncio.run(test_cart_operation())