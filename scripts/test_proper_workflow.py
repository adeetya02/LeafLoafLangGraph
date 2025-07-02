#!/usr/bin/env python3
"""
Test the proper workflow: search first, then add to cart
"""

import asyncio
import aiohttp
import json
import ssl
import certifi
import time
from colorama import init, Fore

init(autoreset=True)

GCP_URL = "https://leafloaf-32905605817.us-central1.run.app"

async def run_workflow():
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    
    session_id = f"proper_workflow_{int(time.time())}"
    
    async with aiohttp.ClientSession(connector=connector) as session:
        # Step 1: Search for milk
        print(f"{Fore.CYAN}Step 1: Search for milk")
        print("Query: 'I need milk'")
        
        payload = {
            "query": "I need milk",
            "session_id": session_id,
            "limit": 3
        }
        
        async with session.post(
            f"{GCP_URL}/api/v1/search",
            json=payload,
            headers={"Content-Type": "application/json"}
        ) as response:
            data = await response.json()
            
            print(f"\n{Fore.YELLOW}Search Results:")
            products = data.get('products', [])
            print(f"Found {len(products)} products")
            
            for i, product in enumerate(products[:3]):
                print(f"\n{i+1}. {product.get('product_name')}")
                print(f"   SKU: {product.get('sku')}")
                print(f"   Price: ${product.get('price', 0):.2f}")
                print(f"   Supplier: {product.get('supplier')}")
        
        await asyncio.sleep(1)
        
        # Step 2: Add first milk to cart
        print(f"\n{Fore.CYAN}Step 2: Add first milk to cart")
        print("Query: 'add the first one to my cart'")
        
        payload = {
            "query": "add the first one to my cart",
            "session_id": session_id
        }
        
        async with session.post(
            f"{GCP_URL}/api/v1/search",
            json=payload,
            headers={"Content-Type": "application/json"}
        ) as response:
            data = await response.json()
            
            print(f"\n{Fore.YELLOW}Add to Cart Response:")
            print(f"Success: {data.get('success')}")
            print(f"Message: {data.get('message')}")
            
            order_data = data.get('order')
            if order_data and order_data.get('items'):
                print(f"\n{Fore.GREEN}Cart Contents:")
                for item in order_data['items']:
                    print(f"- {item.get('name')} x{item.get('quantity')} @ ${item.get('price', 0):.2f}")
        
        await asyncio.sleep(1)
        
        # Step 3: Add more quantity
        print(f"\n{Fore.CYAN}Step 3: Add more of the same")
        print("Query: 'add 2 more milk'")
        
        payload = {
            "query": "add 2 more milk",
            "session_id": session_id
        }
        
        async with session.post(
            f"{GCP_URL}/api/v1/search",
            json=payload,
            headers={"Content-Type": "application/json"}
        ) as response:
            data = await response.json()
            
            print(f"\n{Fore.YELLOW}Update Response:")
            print(f"Success: {data.get('success')}")
            print(f"Message: {data.get('message')}")
            
            order_data = data.get('order')
            if order_data and order_data.get('items'):
                print(f"\n{Fore.GREEN}Updated Cart:")
                for item in order_data['items']:
                    print(f"- {item.get('name')} x{item.get('quantity')} @ ${item.get('price', 0):.2f} = ${item.get('subtotal', 0):.2f}")
                print(f"\nTotal: ${order_data.get('total', 0):.2f}")
        
        await asyncio.sleep(1)
        
        # Step 4: View cart
        print(f"\n{Fore.CYAN}Step 4: View cart")
        print("Query: 'what's in my cart?'")
        
        payload = {
            "query": "what's in my cart?",
            "session_id": session_id
        }
        
        async with session.post(
            f"{GCP_URL}/api/v1/search",
            json=payload,
            headers={"Content-Type": "application/json"}
        ) as response:
            data = await response.json()
            
            print(f"\n{Fore.YELLOW}Cart View Response:")
            print(f"Message: {data.get('message')}")
            
            order_data = data.get('order')
            if order_data and order_data.get('items'):
                print(f"\n{Fore.GREEN}Current Cart:")
                for item in order_data['items']:
                    print(f"- {item.get('name')} x{item.get('quantity')} @ ${item.get('price', 0):.2f} = ${item.get('subtotal', 0):.2f}")
                print(f"\nTotal: ${order_data.get('total', 0):.2f}")
        
        # Summary
        print(f"\n{Fore.CYAN}{'='*60}")
        print("Workflow Test Complete!")
        print('='*60)

if __name__ == "__main__":
    asyncio.run(run_workflow())