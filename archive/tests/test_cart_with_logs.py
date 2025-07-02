#!/usr/bin/env python3
"""
Test cart operations with detailed logging
"""

import asyncio
import logging
import structlog
from src.core.graph import search_graph
from src.models.state import SearchState
import uuid

# Enable detailed logging
logging.basicConfig(level=logging.INFO)
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

async def test_contextual_cart():
    """Test contextual cart operations with the graph"""
    
    print("="*80)
    print("CONTEXTUAL CART TEST WITH LOGS")
    print("="*80)
    
    session_id = str(uuid.uuid4())
    
    # Step 1: Search for products
    print(f"\n1. Searching for spinach (session: {session_id[:8]}...)")
    search_state = SearchState(
        query="I need spinach",
        session_id=session_id,
        messages=[],
        reasoning=[],
        completed_tool_calls=[],
        agent_status={},
        agent_timings={},
        search_params={},  # Required by supervisor
        should_search=False,
        routing_decision=None
    )
    
    search_result = await search_graph.ainvoke(search_state)
    final_response = search_result.get("final_response", {})
    
    print(f"   Found {len(final_response.get('products', []))} products")
    print(f"   Success: {final_response.get('success')}")
    
    # Step 2: Add to cart
    print("\n2. Adding to cart...")
    cart_state = SearchState(
        query="add the first spinach to my cart",
        session_id=session_id,
        messages=[],
        reasoning=[],
        completed_tool_calls=[],
        agent_status={},
        agent_timings={},
        search_params={},  # Required by supervisor
        should_search=False,
        routing_decision=None
    )
    
    cart_result = await search_graph.ainvoke(cart_state)
    cart_response = cart_result.get("final_response", {})
    
    print(f"   Success: {cart_response.get('success')}")
    print(f"   Message: {cart_response.get('message')}")
    if 'order' in cart_response:
        print(f"   Order items: {len(cart_response['order'].get('items', []))}")
    
    # Print reasoning steps
    print("\n3. Reasoning steps from cart operation:")
    for step in cart_result.get("reasoning", []):
        print(f"   - {step}")

if __name__ == "__main__":
    asyncio.run(test_contextual_cart())