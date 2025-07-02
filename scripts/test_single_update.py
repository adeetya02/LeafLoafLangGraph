#!/usr/bin/env python3
"""
Test a single update query with detailed output
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

async def test_single_update():
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    
    session_id = f"test_single_{int(time.time())}"
    
    async with aiohttp.ClientSession(connector=connector) as session:
        # Test the problematic query
        print(f"{Fore.CYAN}Testing: 'change milk quantity to 3'")
        print(f"Session ID: {session_id}")
        print("=" * 60)
        
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
            
            print(f"\n{Fore.YELLOW}Full Response:")
            print(json.dumps(data, indent=2))
            
            # Check routing
            execution = data.get('execution', {})
            agents_run = execution.get('agents_run', [])
            agent_timings = execution.get('agent_timings', {})
            reasoning = execution.get('reasoning_steps', [])
            
            print(f"\n{Fore.CYAN}Analysis:")
            print(f"Success: {data.get('success')}")
            print(f"Message: {data.get('message')}")
            print(f"Agents run: {agents_run}")
            print(f"Agent timings: {agent_timings}")
            print(f"\nReasoning steps:")
            for step in reasoning:
                print(f"  - {step}")
            
            # Check metadata
            metadata = data.get('metadata', {})
            search_config = metadata.get('search_config', {})
            print(f"\nSearch config: {search_config}")
            
            # Check if order data exists
            if 'order' in data:
                print(f"\n{Fore.GREEN}Order data found!")
                print(json.dumps(data['order'], indent=2))
            else:
                print(f"\n{Fore.RED}No order data in response")
            
            # Check products
            if data.get('products'):
                print(f"\n{Fore.YELLOW}Got {len(data['products'])} products instead of order operation")

if __name__ == "__main__":
    asyncio.run(test_single_update())