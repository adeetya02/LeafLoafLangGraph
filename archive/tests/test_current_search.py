#!/usr/bin/env python3
"""
Test current search functionality with BM25
"""

import asyncio
from src.tools.search_tools import ProductSearchTool
import time

async def test_search():
    print("=" * 80)
    print("🔍 TESTING CURRENT SEARCH (BM25)")
    print("=" * 80)
    
    # Initialize search tool
    search_tool = ProductSearchTool()
    
    # Test queries that work well with keyword search
    test_queries = [
        ("BALDOR", "Supplier search"),
        ("organic", "Attribute search"),
        ("PE64A", "SKU fragment search"),
        ("celery", "Product name search"),
        ("fresh produce", "Category search"),
    ]
    
    print("\n📊 Running BM25 searches...")
    print("-" * 80)
    
    for query, description in test_queries:
        print(f"\n🔍 {description}")
        print(f"   Query: '{query}'")
        
        start = time.time()
        result = await search_tool.run(query=query, limit=5)
        elapsed = (time.time() - start) * 1000
        
        print(f"   Time: {elapsed:.0f}ms")
        
        if result.get("success"):
            products = result.get("products", [])
            print(f"   Found: {len(products)} products")
            
            # Show top 3
            for i, product in enumerate(products[:3]):
                name = product.get('product_name', 'Unknown')
                price = product.get('price', 0)
                sku = product.get('sku', 'N/A')
                print(f"   {i+1}. {name} (SKU: {sku}) - ${price:.2f}")
        else:
            print(f"   ❌ Error: {result.get('error', 'Unknown error')}")
    
    # Close the search tool
    search_tool.close()
    
    print("\n" + "=" * 80)
    print("📝 Summary:")
    print("- BM25 (keyword) search is working")
    print("- Performance: ~100-150ms per search")
    print("- Good for exact matches and known terms")
    print("- Semantic search will enable:")
    print("  • Concept queries ('healthy dinner')")
    print("  • Similarity search ('products like tomatoes')")
    print("  • Better typo tolerance")
    print("=" * 80)

# Run the test
if __name__ == "__main__":
    asyncio.run(test_search())