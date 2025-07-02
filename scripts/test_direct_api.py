import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.tools.search_tools import product_search_tool
from src.config.settings import settings

async def test_direct():
    """Test the search tool directly"""
    print("🔍 Testing search tool directly...\n")
    
    # Test queries
    queries = ["potato", "tomato", "peppers"]
    
    for query in queries:
        print(f"\n📦 Searching for: {query}")
        result = await product_search_tool.run(query=query, limit=5)
        
        print(f"Success: {result['success']}")
        print(f"Count: {result['count']}")
        
        if result['success'] and result['count'] > 0:
            print("Products found:")
            for i, product in enumerate(result['products'][:3]):
                print(f"  {i+1}. {product.get('name')} - {product.get('sku')}")
        else:
            print(f"Error: {result.get('error', 'No products found')}")

if __name__ == "__main__":
    asyncio.run(test_direct()) 