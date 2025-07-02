#!/usr/bin/env python3
"""
Test the complete update workflow on GCP
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

async def test_update_workflow():
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    
    session_id = f"test_update_{int(time.time())}"
    
    async with aiohttp.ClientSession(connector=connector) as session:
        # Step 1: Add milk to cart
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
            print(f"{Fore.YELLOW}Response: {data.get('message')}")
            
            if data.get('order'):
                order = data['order']
                print(f"{Fore.GREEN}Cart contents:")
                for item in order.get('items', []):
                    print(f"  - {item.get('name')} x{item.get('quantity')}")
        
        await asyncio.sleep(1)
        
        # Step 2: Update quantity using the problematic pattern
        print(f"\n{Fore.CYAN}Step 2: Testing 'change milk quantity to 3'...")
        payload = {
            "query": "change milk quantity to 3",
            "session_id": session_id
        }
        
        async with session.post(
            f"{GCP_URL}/api/v1/search",
            json=payload,
            headers={"Content-Type": "application/json"}
        ) as response:
            data = await response.json()
            print(f"{Fore.YELLOW}Response: {data.get('message')}")
            
            # Check if it went to order agent
            execution = data.get('execution', {})
            agents_run = execution.get('agents_run', [])
            print(f"Agents run: {agents_run}")
            
            if 'order_agent' in agents_run:
                print(f"{Fore.GREEN}✓ Correctly routed to order agent!")
                
                if data.get('order'):
                    order = data['order']
                    print(f"{Fore.GREEN}Updated cart:")
                    for item in order.get('items', []):
                        print(f"  - {item.get('name')} x{item.get('quantity')}")
                else:
                    print(f"{Fore.RED}No order data in response")
            else:
                print(f"{Fore.RED}✗ Incorrectly routed to: {agents_run}")
                if data.get('products'):
                    print(f"{Fore.RED}Got search results instead!")
        
        await asyncio.sleep(1)
        
        # Step 3: Try other update patterns
        test_patterns = [
            "update banana quantity to 5",
            "make it 10",
            "double the milk quantity"
        ]
        
        for pattern in test_patterns:
            print(f"\n{Fore.CYAN}Testing: '{pattern}'...")
            payload = {
                "query": pattern,
                "session_id": session_id
            }
            
            async with session.post(
                f"{GCP_URL}/api/v1/search",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                data = await response.json()
                agents_run = data.get('execution', {}).get('agents_run', [])
                
                if 'order_agent' in agents_run:
                    print(f"{Fore.GREEN}✓ Routed to order agent")
                else:
                    print(f"{Fore.RED}✗ Routed to: {agents_run}")

if __name__ == "__main__":
    asyncio.run(test_update_workflow())