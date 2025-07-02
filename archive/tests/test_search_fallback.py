#!/usr/bin/env python3
import asyncio
from src.tools.search_tools import product_search_tool

async def test_search():
    """Test that BM25 fallback works when vectorization fails"""
    print("Testing search tool with fallback...")
    
    # Test search that should trigger BM25 fallback
    result = await product_search_tool.run(
        query="spinach",
        limit=10,
        alpha=0.5
    )
    
    print(f"\nSearch succeeded: {result['success']}")
    print(f"Products found: {result['count']}")
    print(f"Search config: {result.get('search_config', {})}")
    
    if result['success'] and result['count'] > 0:
        print("\nFirst 3 products:")
        for i, product in enumerate(result['products'][:3]):
            print(f"{i+1}. {product.get('name')} - ${product.get('price')}")
            print(f"   {product.get('description', 'No description')}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    asyncio.run(test_search())