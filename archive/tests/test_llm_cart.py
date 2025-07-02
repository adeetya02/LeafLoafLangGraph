#!/usr/bin/env python3
"""
Test LLM-based cart intent recognition
"""

import asyncio
import httpx
import json

async def test_llm_cart():
    """Test cart operations with LLM"""
    
    print("="*80)
    print("LLM CART INTENT TEST")
    print("="*80)
    
    base_url = "http://localhost:8080"
    session_id = "llm-test-123"
    
    # Test sequence
    tests = [
        ("I need spinach", "Search for spinach"),
        ("throw that in my basket", "Add to cart - conversational"),
        ("actually grab me 3 of those", "Update quantity - conversational"),
        ("what's in my cart?", "Show cart - conversational"),
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for query, description in tests:
            print(f"\n{'-'*60}")
            print(f"Test: {description}")
            print(f"Query: \"{query}\"")
            
            resp = await client.post(
                f"{base_url}/api/v1/search",
                json={"query": query, "session_id": session_id}
            )
            
            data = resp.json()
            conv = data.get('conversation', {})
            
            print(f"\nResult:")
            print(f"  Intent: {conv.get('intent', 'unknown')}")
            print(f"  Confidence: {conv.get('confidence', 0.0)}")
            print(f"  Message: {data.get('message', '')[:80]}...")
            
            if 'order' in data and data['order'] and data['order'].get('items'):
                print(f"  Cart: {len(data['order']['items'])} items")
                for item in data['order']['items']:
                    print(f"    - {item['name']} x{item['quantity']}")

if __name__ == "__main__":
    asyncio.run(test_llm_cart())