#!/usr/bin/env python3
"""
Simple test to verify memory sharing between agents
"""

import asyncio
import uuid
from src.memory.memory_manager import memory_manager
from src.agents.product_search import ProductSearchReactAgent
from src.agents.order_agent import OrderReactAgent
from src.models.state import SearchState

async def test_memory_sharing():
    """Test that agents share the same memory instance"""
    
    print("="*80)
    print("MEMORY SHARING TEST")
    print("="*80)
    
    # Initialize agents
    search_agent = ProductSearchReactAgent()
    order_agent = OrderReactAgent()
    
    # Check they have the same memory instance
    print(f"\n1. Memory instance check:")
    print(f"   Search agent memory ID: {id(search_agent.session_memory)}")
    print(f"   Order agent memory ID: {id(order_agent.session_memory)}")
    print(f"   Same instance: {search_agent.session_memory is order_agent.session_memory}")
    
    # Test storing and retrieving
    session_id = str(uuid.uuid4())
    
    # Store some test products via search agent
    test_products = [
        {"sku": "TEST1", "name": "Test Product 1", "price": 10.00},
        {"sku": "TEST2", "name": "Test Product 2", "price": 20.00}
    ]
    
    print(f"\n2. Storing products via search agent:")
    await search_agent.session_memory.add_search_results(session_id, "test query", test_products)
    print(f"   Stored {len(test_products)} products")
    
    # Retrieve via order agent
    print(f"\n3. Retrieving via order agent:")
    retrieved = await order_agent.session_memory.get_recent_search_results(session_id)
    print(f"   Retrieved {len(retrieved)} products")
    print(f"   Same products: {retrieved == test_products}")
    
    # Test with actual state execution
    print(f"\n4. Testing with actual state execution:")
    
    # Create search state
    search_state = SearchState(
        query="test products",
        session_id=session_id,
        messages=[],
        routing_decision="product_search",
        search_results=[],
        reasoning=[],
        completed_tool_calls=[]
    )
    
    # Manually add products to simulate search
    search_state["search_results"] = test_products
    await search_agent.session_memory.add_search_results(session_id, "test products", test_products)
    
    # Create order state
    order_state = SearchState(
        query="add the first one",
        session_id=session_id,
        messages=[],
        routing_decision="order_agent",
        search_results=[],  # Empty - should pull from memory
        reasoning=[],
        completed_tool_calls=[]
    )
    
    # Check if order agent can access the products
    stored_products = await order_agent.session_memory.get_recent_search_results(session_id)
    print(f"   Order agent found {len(stored_products)} products in memory")
    
    print("\n✅ Memory sharing test complete!")

if __name__ == "__main__":
    asyncio.run(test_memory_sharing())