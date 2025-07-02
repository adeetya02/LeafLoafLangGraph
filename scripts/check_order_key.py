#!/usr/bin/env python3
"""
Check the 'order' key in response
"""

import asyncio
import aiohttp
import json
import ssl
import certifi
from colorama import init, Fore

init(autoreset=True)

GCP_URL = "https://leafloaf-32905605817.us-central1.run.app"

async def check_order_response():
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        payload = {
            "query": "add 2 bananas to my cart",
            "session_id": "test_order_key"
        }
        
        async with session.post(
            f"{GCP_URL}/api/v1/search",
            json=payload,
            headers={"Content-Type": "application/json"}
        ) as response:
            data = await response.json()
            
            print(f"{Fore.CYAN}Query: 'add 2 bananas to my cart'")
            print(f"\n{Fore.YELLOW}Looking for order data...")
            
            # Check the 'order' key
            if "order" in data:
                print(f"\n{Fore.GREEN}✓ Found 'order' key!")
                print(f"{Fore.CYAN}Order data:")
                print(json.dumps(data["order"], indent=2))
            else:
                print(f"{Fore.RED}✗ No 'order' key found")
            
            # Check order_response
            if "order_response" in data:
                print(f"\n{Fore.GREEN}✓ Found 'order_response' key!")
                print(json.dumps(data["order_response"], indent=2))
            
            # Check conversation
            if "conversation" in data:
                print(f"\n{Fore.YELLOW}Conversation:")
                print(json.dumps(data["conversation"], indent=2))
            
            # Show all keys
            print(f"\n{Fore.YELLOW}All response keys: {list(data.keys())}")

if __name__ == "__main__":
    asyncio.run(check_order_response())