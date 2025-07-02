#!/usr/bin/env python3
"""
Test Gemma health on deployed instance
"""

import asyncio
import aiohttp
import json
import ssl
import certifi
from colorama import init, Fore

init(autoreset=True)

GCP_URL = "https://leafloaf-32905605817.us-central1.run.app"

async def test_health():
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        # Test a simple query and look at the metadata
        print(f"{Fore.CYAN}Testing Gemma integration...")
        
        payload = {
            "query": "update milk quantity to 3",
            "session_id": "test_health"
        }
        
        async with session.post(
            f"{GCP_URL}/api/v1/search",
            json=payload,
            headers={"Content-Type": "application/json"}
        ) as response:
            data = await response.json()
            
            # Check execution details
            execution = data.get('execution', {})
            reasoning = execution.get('reasoning_steps', [])
            
            print(f"\n{Fore.YELLOW}Reasoning steps:")
            for step in reasoning:
                print(f"  - {step}")
            
            # Check conversation metadata
            conversation = data.get('conversation', {})
            print(f"\n{Fore.YELLOW}Conversation data:")
            print(f"  Intent: {conversation.get('intent')}")
            print(f"  Confidence: {conversation.get('confidence')}")
            
            # Check if there's any Gemma metadata
            metadata = data.get('metadata', {})
            if 'search_config' in metadata:
                print(f"\n{Fore.YELLOW}Search config:")
                print(f"  {json.dumps(metadata['search_config'], indent=4)}")

if __name__ == "__main__":
    asyncio.run(test_health())