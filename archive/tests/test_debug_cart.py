#!/usr/bin/env python3
"""
Debug cart operations by testing the tool directly
"""

import asyncio
from src.tools.order_tools import add_to_cart
from src.memory.memory_manager import memory_manager

async def test_cart_tool_directly():
    """Test the add_to_cart tool directly"""
    
    print("="*80)
    print("TESTING CART TOOL DIRECTLY")
    print("="*80)
    
    # Sample products (like what search would return)
    test_products = [
        {
            "sku": "SP6BW1",
            "name": "Spinach Baby 2X2 Lb B&W",
            "price": 20.62,
            "unit": "Case",
            "size": "2X2 Lb",
            "brand": "Baldor",
            "category": "Vegetables",
            "description": "Fresh baby spinach"
        },
        {
            "sku": "SP93",
            "name": "Spinach Triple Washed",
            "price": 26.56,
            "unit": "Case",
            "size": "4X2.5 Lb",
            "brand": "Baldor",
            "category": "Vegetables",
            "description": "Premium triple washed spinach"
        }
    ]
    
    # Test 1: Direct tool call
    print("\n1. Testing direct add_to_cart call:")
    result = await add_to_cart(
        query="add the first spinach to my cart",
        search_results=test_products,
        current_order={"items": []}
    )
    
    print(f"   Success: {result['success']}")
    print(f"   Message: {result.get('message', 'N/A')}")
    if result['success'] and result.get('order', {}).get('items'):
        print(f"   Items in cart: {len(result['order']['items'])}")
        for item in result['order']['items']:
            print(f"   - {item['name']} x{item['quantity']}")
    
    # Test 2: Store in session and retrieve
    print("\n2. Testing session storage:")
    session_id = "test-session-123"
    
    # Store search results
    await memory_manager.session_memory.add_search_results(session_id, "spinach", test_products)
    
    # Retrieve
    retrieved = await memory_manager.session_memory.get_recent_search_results(session_id)
    print(f"   Stored products: {len(test_products)}")
    print(f"   Retrieved products: {len(retrieved)}")
    print(f"   Match: {retrieved == test_products}")
    
    # Test 3: Test with empty search results
    print("\n3. Testing with empty search results:")
    empty_result = await add_to_cart(
        query="add spinach",
        search_results=[],
        current_order={"items": []}
    )
    print(f"   Success: {empty_result['success']}")
    print(f"   Error: {empty_result.get('error', 'N/A')}")
    
    # Test 4: Test quantity parsing
    print("\n4. Testing quantity parsing:")
    qty_result = await add_to_cart(
        query="add 3 bags of spinach",
        search_results=test_products,
        current_order={"items": []}
    )
    if qty_result['success'] and qty_result.get('order', {}).get('items'):
        item = qty_result['order']['items'][0]
        print(f"   Added: {item['name']} x{item['quantity']}")

if __name__ == "__main__":
    asyncio.run(test_cart_tool_directly())