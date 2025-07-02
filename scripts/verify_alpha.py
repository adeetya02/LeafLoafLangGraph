#!/usr/bin/env python3
"""
Simple verification that alpha is working correctly
"""

import asyncio
import aiohttp
import json
import ssl
import certifi

GCP_URL = "https://leafloaf-32905605817.us-central1.run.app"

async def check_alpha(query: str):
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        payload = {"query": query, "limit": 2}
        
        async with session.post(
            f"{GCP_URL}/api/v1/search",
            json=payload,
            headers={"Content-Type": "application/json"}
        ) as response:
            data = await response.json()
            
            # Look for alpha in all possible places
            places_to_check = [
                ("metadata.search_config.alpha", data.get("metadata", {}).get("search_config", {}).get("alpha")),
                ("execution.reasoning_steps", data.get("execution", {}).get("reasoning_steps", [])),
                ("metadata.alpha", data.get("metadata", {}).get("alpha")),
            ]
            
            print(f"\nQuery: '{query}'")
            print(f"Products found: {len(data.get('products', []))}")
            
            for location, value in places_to_check:
                if value:
                    print(f"✓ Alpha found in {location}: {value}")
            
            # Show first product if any
            products = data.get("products", [])
            if products:
                print(f"First product: {products[0].get('product_name')}")

async def main():
    queries = ["milk", "Oatly barista edition", "healthy breakfast ideas"]
    
    print("Alpha Value Verification Test")
    print(f"Testing {GCP_URL}")
    
    for query in queries:
        await check_alpha(query)
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main())