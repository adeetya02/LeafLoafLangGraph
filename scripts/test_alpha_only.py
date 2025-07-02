#!/usr/bin/env python3
"""
Simple test to check just the alpha calculation
"""

import asyncio
import aiohttp
import json
import ssl
import certifi
from colorama import init, Fore

init(autoreset=True)

GCP_URL = "https://leafloaf-32905605817.us-central1.run.app"

async def test_alpha(query: str):
    """Test alpha calculation for a query"""
    
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        payload = {
            "query": query,
            "limit": 1  # Just need to check alpha
        }
        
        try:
            async with session.post(
                f"{GCP_URL}/api/v1/search",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                data = await response.json()
                
                if response.status == 200:
                    # Check execution
                    execution = data.get("execution", {})
                    reasoning = execution.get("reasoning_steps", [])
                    
                    # Extract alpha from reasoning
                    alpha_info = None
                    for step in reasoning:
                        if "Alpha:" in step:
                            alpha_info = step
                            break
                    
                    # Check metadata
                    metadata = data.get("metadata", {})
                    search_config = metadata.get("search_config", {})
                    
                    print(f"\n{Fore.CYAN}Query: '{query}'")
                    print(f"{Fore.YELLOW}Reasoning: {alpha_info}")
                    print(f"{Fore.GREEN}Search Config Alpha: {search_config.get('alpha', 'NOT FOUND')}")
                    
                    # Show if it's using the right search type
                    alpha_val = search_config.get('alpha')
                    if alpha_val is not None:
                        alpha_float = float(alpha_val)
                        if alpha_float < 0.3:
                            print(f"  → Should use BM25 search")
                        elif alpha_float > 0.7:
                            print(f"  → Should use Vector search")  
                        else:
                            print(f"  → Should use Hybrid search")
                    
                    return alpha_val
                    
        except Exception as e:
            print(f"{Fore.RED}Error: {e}")
            return None

async def main():
    print(f"{Fore.CYAN}Testing Alpha Calculation")
    print(f"URL: {GCP_URL}")
    
    queries = [
        "milk",                    # Generic - expect ~0.5
        "Oatly barista edition",   # Specific - expect ~0.1-0.2
        "healthy breakfast",       # Conceptual - expect ~0.8
        "PEPPER RED BU 1-1/9",    # Exact match - expect ~0.1
    ]
    
    for query in queries:
        alpha = await test_alpha(query)
        print(f"{Fore.CYAN}{'='*50}")

if __name__ == "__main__":
    asyncio.run(main())