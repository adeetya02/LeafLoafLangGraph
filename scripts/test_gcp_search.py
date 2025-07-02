#!/usr/bin/env python3
"""
Test GCP deployed search to verify BM25 is working
"""

import asyncio
import aiohttp
import json
import ssl
import certifi
from colorama import init, Fore

init(autoreset=True)

GCP_URL = "https://leafloaf-32905605817.us-central1.run.app"

async def test_search(query: str):
    """Test a search query against GCP"""
    print(f"\n{Fore.CYAN}Testing: '{query}'")
    
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        payload = {
            "query": query,
            "limit": 5
        }
        
        try:
            async with session.post(
                f"{GCP_URL}/api/v1/search",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                data = await response.json()
                
                if response.status == 200:
                    products = data.get("products", [])
                    print(f"{Fore.GREEN}✅ Found {len(products)} products")
                    
                    for product in products[:3]:  # Show first 3
                        print(f"\n{Fore.YELLOW}Product:")
                        print(f"  Name: {product.get('product_name', 'Unknown')}")
                        print(f"  Supplier: {product.get('supplier', 'Unknown')}")
                        print(f"  Price: ${product.get('price', 0):.2f}")
                        print(f"  Pack: {product.get('retail_pack_size', 'Unknown')}")
                        
                    # Check search config
                    exec_info = data.get("execution", {})
                    print(f"\n{Fore.CYAN}Search Config:")
                    print(f"  Alpha: {exec_info.get('search_config', {}).get('alpha', 'Unknown')}")
                    print(f"  Total Time: {exec_info.get('total_time_ms', 0):.0f}ms")
                    
                else:
                    print(f"{Fore.RED}❌ Error {response.status}: {data}")
                    
        except Exception as e:
            print(f"{Fore.RED}❌ Request failed: {e}")

async def main():
    print(f"{Fore.CYAN}Testing GCP Search API")
    print(f"URL: {GCP_URL}")
    print(f"\n{Fore.YELLOW}Note: Using BM25 only (keyword search)")
    
    # Test various queries
    queries = [
        "milk",
        "organic milk",
        "Oatly",
        "bananas",
        "pasta sauce",
        "PEPPER RED",  # Exact match from our data
        "Laxmi"  # Brand name
    ]
    
    for query in queries:
        await test_search(query)
        await asyncio.sleep(0.5)  # Be nice to the API

if __name__ == "__main__":
    asyncio.run(main())