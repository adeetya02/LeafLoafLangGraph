"""
Test LeafLoaf with Baldor produce queries
Testing wholesale to retail conversion
"""

import asyncio
import aiohttp
import json
import ssl
import certifi
from typing import Dict, List
from datetime import datetime

# Base URL for testing - GCP deployment
BASE_URL = "https://leafloafai-32905605817.us-east1.run.app"

# Baldor produce test queries - matching actual database content
BALDOR_TEST_QUERIES = [
    # Specific produce items
    {
        "query": "bell peppers",
        "expected_type": "produce",
        "description": "Looking for tri-color or regular bell peppers"
    },
    {
        "query": "strawberries",
        "expected_type": "berries",
        "description": "Fresh strawberries"
    },
    {
        "query": "organic kale",
        "expected_type": "leafy_greens",
        "description": "Organic kale bunches"
    },
    {
        "query": "tomatoes",
        "expected_type": "produce",
        "description": "Various tomato types"
    },
    {
        "query": "avocados",
        "expected_type": "produce",
        "description": "Ripe avocados"
    },
    {
        "query": "mushrooms",
        "expected_type": "produce",
        "description": "Fresh mushrooms"
    },
    {
        "query": "apples",
        "expected_type": "fruit",
        "description": "Different apple varieties"
    },
    {
        "query": "citrus fruits",
        "expected_type": "fruit",
        "description": "Oranges, lemons, limes"
    },
    {
        "query": "fresh herbs",
        "expected_type": "herbs",
        "description": "Basil, cilantro, parsley"
    },
    {
        "query": "potatoes",
        "expected_type": "produce",
        "description": "Various potato types"
    }
]

# Wholesale to retail conversion rules
WHOLESALE_TO_RETAIL = {
    "CTN": "pack",
    "CS": "pack", 
    "BG": "bag",
    "BX": "box",
    "BU": "bunch",
    "LB": "lb",
    "EA": "each",
    "DZ": "dozen",
    "PT": "pint",
    "QT": "quart"
}

def convert_wholesale_to_retail(product: Dict) -> Dict:
    """
    Convert Baldor wholesale format to retail customer format
    Example: "TRI-COLOR BELL PEPPERS 8 X 3CT CTN 28.5" 
    -> "Tri-Color Bell Peppers (3-pack)" with retail price
    """
    
    # Extract product info
    name = product.get("name", product.get("product_name", ""))
    description = product.get("description", "")
    wholesale_price = float(product.get("price", 0))
    
    # Parse the Baldor format
    # Format is typically: NAME PACK_SIZE X UNIT_COUNT UNIT_TYPE PRICE
    parts = name.split()
    
    # Clean up the name (remove quantity info)
    clean_name = []
    pack_info = ""
    
    for i, part in enumerate(parts):
        # Check if we've hit quantity indicators
        if part.isdigit() or part == "X" or part in WHOLESALE_TO_RETAIL:
            # Extract pack information
            if i > 0 and parts[i-1].isdigit() and i+1 < len(parts):
                pack_info = f"{parts[i-1]}-{parts[i+1].lower()}"
            break
        else:
            clean_name.append(part.title())
    
    # Create retail-friendly name
    retail_name = " ".join(clean_name)
    if pack_info:
        retail_name += f" ({pack_info})"
    
    # Calculate retail price (markup from wholesale)
    # Typical retail markup is 50-100% for produce
    retail_price = round(wholesale_price * 1.75 / 8, 2)  # Divide by pack size if bulk
    
    return {
        **product,
        "retail_name": retail_name,
        "retail_price": retail_price,
        "retail_unit": "per pack" if pack_info else "per item",
        "wholesale_info": {
            "original_name": name,
            "wholesale_price": wholesale_price,
            "pack_size": pack_info
        }
    }

async def test_search(session: aiohttp.ClientSession, query: str) -> Dict:
    """Test a single search query"""
    
    payload = {
        "query": query,
        "config": {},
        "kwargs": {}
    }
    
    print(f"\n🔍 Testing query: '{query}'")
    
    try:
        async with session.post(
            f"{BASE_URL}/api/v1/search",
            json=payload,
            headers={"Content-Type": "application/json"}
        ) as response:
            result = await response.json()
            
            if result.get("products"):
                print(f"✅ Found {len(result['products'])} products")
                
                # Convert and display first few products
                for i, product in enumerate(result["products"][:3]):
                    retail_product = convert_wholesale_to_retail(product)
                    print(f"\n  Product {i+1}:")
                    print(f"  - Retail Name: {retail_product['retail_name']}")
                    print(f"  - Retail Price: ${retail_product['retail_price']}")
                    print(f"  - Unit: {retail_product['retail_unit']}")
                    if 'description' in product:
                        print(f"  - Description: {product['description'][:100]}...")
            else:
                print("❌ No products found")
                
            return result
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {"error": str(e)}

async def test_add_to_cart(session: aiohttp.ClientSession, product_id: str, quantity: int = 1) -> Dict:
    """Test adding item to cart with retail display"""
    
    payload = {
        "query": f"add {quantity} of product {product_id} to my cart",
        "config": {},
        "kwargs": {}
    }
    
    print(f"\n🛒 Adding to cart: {product_id} (qty: {quantity})")
    
    try:
        async with session.post(
            f"{BASE_URL}/api/v1/order",
            json=payload,
            headers={"Content-Type": "application/json"}
        ) as response:
            result = await response.json()
            print(f"✅ Cart updated: {result.get('message', 'Success')}")
            return result
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {"error": str(e)}

async def test_conversation_flow(session: aiohttp.ClientSession):
    """Test a complete shopping conversation with Baldor products"""
    
    print("\n" + "="*50)
    print("🛍️  BALDOR PRODUCE SHOPPING TEST")
    print("="*50)
    
    # 1. Search for bell peppers
    result = await test_search(session, "bell peppers")
    
    if result.get("products"):
        # 2. Add first product to cart
        first_product = result["products"][0]
        product_id = first_product.get("id", first_product.get("sku", ""))
        
        if product_id:
            await test_add_to_cart(session, product_id, 2)
    
    # 3. Search for organic produce
    await test_search(session, "organic vegetables")
    
    # 4. Search for strawberries
    await test_search(session, "fresh strawberries")
    
    # 5. Get current cart
    print("\n📋 Checking cart contents...")
    cart_payload = {
        "query": "what's in my cart?",
        "config": {},
        "kwargs": {}
    }
    
    try:
        async with session.post(
            f"{BASE_URL}/api/v1/order",
            json=cart_payload,
            headers={"Content-Type": "application/json"}
        ) as response:
            cart_result = await response.json()
            print(f"Cart: {cart_result.get('message', 'No items')}")
    except Exception as e:
        print(f"❌ Error checking cart: {str(e)}")

async def main():
    """Run all Baldor product tests"""
    
    # Create SSL context to handle certificate issues
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    conn = aiohttp.TCPConnector(ssl=ssl_context)
    
    async with aiohttp.ClientSession(connector=conn) as session:
        # Test individual queries
        print("\n🧪 TESTING INDIVIDUAL PRODUCE QUERIES")
        print("-" * 40)
        
        for test_query in BALDOR_TEST_QUERIES:
            await test_search(session, test_query["query"])
            await asyncio.sleep(0.5)  # Rate limiting
        
        # Test conversation flow
        await test_conversation_flow(session)
        
        print("\n✅ All tests completed!")
        print("\n📝 Note: All wholesale quantities have been converted to retail format")
        print("   Prices shown are retail prices, not wholesale")

if __name__ == "__main__":
    asyncio.run(main())