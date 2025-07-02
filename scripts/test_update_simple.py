#!/usr/bin/env python3
"""
Simple test for update order functionality
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

async def test_update():
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    
    session_id = f"update_test_{int(time.time())}"
    
    async with aiohttp.ClientSession(connector=connector) as session:
        # First add something to cart with a simple pattern
        print(f"{Fore.CYAN}Step 1: Add milk to cart")
        payload = {
            "query": "add milk to cart",
            "session_id": session_id
        }
        
        async with session.post(
            f"{GCP_URL}/api/v1/search",
            json=payload,
            headers={"Content-Type": "application/json"}
        ) as response:
            data = await response.json()
            print(f"Response: {data.get('message')}")
            if data.get('order'):
                print(f"Cart: {json.dumps(data['order'], indent=2)}")
        
        await asyncio.sleep(1)
        
        # Now try to update with different phrasings
        update_queries = [
            "change milk quantity to 3",
            "update milk to 5 units",
            "I want to change the milk quantity to 3",
            "modify the milk amount to 3 please",
            "can you update milk quantity to 3"
        ]
        
        for query in update_queries:
            print(f"\n{Fore.CYAN}Testing: '{query}'")
            payload = {
                "query": query,
                "session_id": session_id
            }
            
            async with session.post(
                f"{GCP_URL}/api/v1/search",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                data = await response.json()
                
                # Check intent from conversation
                intent = data.get('conversation', {}).get('intent', 'unknown')
                confidence = data.get('conversation', {}).get('confidence', 0)
                agents = data.get('execution', {}).get('agents_run', [])
                
                if 'order_agent' in agents or intent == 'update_order':
                    print(f"{Fore.GREEN}✓ Correctly identified as update_order")
                else:
                    print(f"{Fore.RED}✗ Identified as: {intent} (confidence: {confidence})")
                    print(f"   Agents run: {agents}")

if __name__ == "__main__":
    asyncio.run(test_update())