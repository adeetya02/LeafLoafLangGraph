#!/usr/bin/env python3
"""
Test session memory implementation
Verify that search results are stored and accessible for contextual cart operations
"""

import asyncio
from src.memory.session_memory import SessionMemory
import uuid

async def test_session_memory():
    """Test session memory functionality"""
    
    print("="*80)
    print("TESTING SESSION MEMORY")
    print("="*80)
    
    # Initialize memory
    memory = SessionMemory()
    session_id = str(uuid.uuid4())
    
    # Test 1: Store and retrieve conversation
    print("\n1. Testing conversation history:")
    await memory.add_to_conversation(session_id, "human", "I need spinach")
    await memory.add_to_conversation(session_id, "assistant", "Found 5 spinach products")
    
    history = await memory.get_conversation_history(session_id)
    print(f"   Stored {len(history)} messages")
    for msg in history:
        print(f"   - {msg['role']}: {msg['content']}")
    
    # Test 2: Store and retrieve search results
    print("\n2. Testing search results storage:")
    test_products = [
        {"sku": "SP6BW1", "name": "Spinach Baby", "price": 20.62},
        {"sku": "SP93", "name": "Spinach Triple Washed", "price": 26.56}
    ]
    
    await memory.add_search_results(session_id, "spinach", test_products)
    
    retrieved = await memory.get_recent_search_results(session_id)
    print(f"   Stored {len(retrieved)} products")
    for product in retrieved[:2]:
        print(f"   - {product['name']} (SKU: {product['sku']}) - ${product['price']}")
    
    # Test 3: User context
    print("\n3. Testing user context:")
    context = await memory.get_user_context(session_id)
    print(f"   Context keys: {list(context.keys())}")
    print(f"   Has conversation: {'conversation' in context}")
    print(f"   Has recent searches: {'recent_searches' in context}")
    
    # Test 4: Order management
    print("\n4. Testing order management:")
    await memory.update_order(session_id, {"SP6BW1": {"quantity": 2, "product": test_products[0]}})
    
    order = await memory.get_current_order(session_id)
    print(f"   Order has {len(order)} items")
    for sku, details in order.items():
        print(f"   - {sku}: {details['quantity']} x {details['product']['name']}")
    
    # Test 5: Preferences
    print("\n5. Testing preferences:")
    await memory.add_preference(session_id, "organic")
    await memory.add_preference(session_id, "gluten-free")
    
    prefs = await memory.get_preferences(session_id)
    print(f"   Stored preferences: {prefs}")
    
    print("\n✅ Session memory tests complete!")

if __name__ == "__main__":
    asyncio.run(test_session_memory())