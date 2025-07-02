#!/usr/bin/env python3
"""
Test to see actual order data in responses
"""

import asyncio
import aiohttp
import json
import ssl
import certifi
from colorama import init, Fore

init(autoreset=True)

GCP_URL = "https://leafloaf-32905605817.us-central1.run.app"

async def test_order_data():
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    
    session_id = "test_order_data"
    
    async with aiohttp.ClientSession(connector=connector) as session:
        # Step 1: Add something to cart
        print(f"{Fore.CYAN}Step 1: Adding milk to cart...")
        payload = {
            "query": "add 2 milk to my cart",
            "session_id": session_id
        }
        
        async with session.post(
            f"{GCP_URL}/api/v1/search",
            json=payload,
            headers={"Content-Type": "application/json"}
        ) as response:
            data = await response.json()
            
            print(f"\n{Fore.YELLOW}Add to cart response:")
            print(f"Success: {data.get('success')}")
            print(f"Message: {data.get('message')}")
            
            # Check order data
            order_data = data.get('order')
            if order_data:
                print(f"\n{Fore.GREEN}Order data found:")
                print(json.dumps(order_data, indent=2))
            else:
                print(f"\n{Fore.RED}Order data is: {order_data}")
        
        # Step 2: View cart
        print(f"\n{Fore.CYAN}Step 2: Viewing cart...")
        payload = {
            "query": "show me my cart",
            "session_id": session_id
        }
        
        async with session.post(
            f"{GCP_URL}/api/v1/search",
            json=payload,
            headers={"Content-Type": "application/json"}
        ) as response:
            data = await response.json()
            
            print(f"\n{Fore.YELLOW}View cart response:")
            print(f"Success: {data.get('success')}")
            print(f"Message: {data.get('message')}")
            
            # Check order data
            order_data = data.get('order')
            if order_data:
                print(f"\n{Fore.GREEN}Order data found:")
                print(json.dumps(order_data, indent=2))
            else:
                print(f"\n{Fore.RED}Order data is: {order_data}")
                
            # Check if cart contents are in message
            if "cart" in data.get('message', '').lower():
                print(f"\n{Fore.BLUE}Cart info in message: {data.get('message')}")

if __name__ == "__main__":
    asyncio.run(test_order_data())