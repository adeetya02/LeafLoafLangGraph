#!/usr/bin/env python3
"""
Test pack conversion in actual search
"""

import asyncio
from src.tools.search_tools import SearchTools

async def test_pack_search():
    """Test that pack conversion works in search results"""
    
    print("="*80)
    print("🔍 TESTING PACK CONVERSION IN SEARCH")
    print("="*80)
    
    search_tools = SearchTools()
    
    # Test queries that should show packs
    test_queries = [
        "bell peppers",
        "strawberries", 
        "spinach"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Searching for: {query}")
        print("-" * 60)
        
        result = await search_tools.search_products(query, limit=3)
        
        if result["success"] and result["products"]:
            for product in result["products"]:
                print(f"\n📦 {product.get('name', 'Unknown')}")
                print(f"   Price: {product.get('price_display', 'N/A')}")
                print(f"   Unit: {product.get('unit', 'N/A')}")
                if product.get('pack_size'):
                    print(f"   Pack Size: {product['pack_size']}")
                print(f"   SKU: {product.get('sku', 'N/A')}")
        else:
            print(f"   No results or error: {result.get('error', 'Unknown')}")

if __name__ == "__main__":
    asyncio.run(test_pack_search())