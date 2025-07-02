#!/usr/bin/env python3
"""
Test if Gemma is calculating alpha values for search queries
"""

import asyncio
import aiohttp
import json
import ssl
import certifi
from colorama import init, Fore

init(autoreset=True)

GCP_URL = "https://leafloaf-32905605817.us-central1.run.app"

async def test_single_search(query: str):
    """Test a single search and trace alpha calculation"""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"Testing: '{query}'")
    print('='*60)
    
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        payload = {
            "query": query,
            "limit": 3
        }
        
        try:
            async with session.post(
                f"{GCP_URL}/api/v1/search",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                data = await response.json()
                
                if response.status == 200:
                    # Extract all the info we can about alpha
                    execution = data.get("execution", {})
                    metadata = data.get("metadata", {})
                    
                    print(f"\n{Fore.YELLOW}Execution Details:")
                    print(f"  Total time: {execution.get('total_time_ms', 'Unknown')}ms")
                    
                    # Check search config
                    search_config = execution.get("search_config", {})
                    if search_config:
                        print(f"\n{Fore.YELLOW}Search Config:")
                        print(f"  Alpha: {search_config.get('alpha', 'NOT SET')}")
                        print(f"  Full config: {json.dumps(search_config, indent=4)}")
                    else:
                        print(f"\n{Fore.RED}No search_config found in execution")
                    
                    # Check if there's alpha in metadata
                    if "alpha" in metadata:
                        print(f"\n{Fore.YELLOW}Metadata Alpha: {metadata['alpha']}")
                    
                    # Check agents used
                    agents_used = execution.get("agents_used", [])
                    print(f"\n{Fore.YELLOW}Agents Used: {agents_used}")
                    
                    # Check search params
                    if "search_params" in execution:
                        print(f"\n{Fore.YELLOW}Search Params:")
                        print(json.dumps(execution["search_params"], indent=4))
                    
                    # Products found
                    products = data.get("products", [])
                    print(f"\n{Fore.GREEN}Products found: {len(products)}")
                    
                    # Check the raw execution data
                    print(f"\n{Fore.CYAN}Full Execution Data:")
                    print(json.dumps(execution, indent=2))
                    
                else:
                    print(f"{Fore.RED}Error {response.status}: {data}")
                    
        except Exception as e:
            print(f"{Fore.RED}Request failed: {e}")

async def main():
    print(f"{Fore.CYAN}Alpha Calculation Test")
    print(f"Testing if Gemma is setting alpha values")
    print(f"GCP URL: {GCP_URL}")
    
    # Test different query types that should get different alphas
    test_queries = [
        ("milk", "Generic term - should get balanced alpha ~0.5"),
        ("Oatly barista edition", "Specific product - should get low alpha ~0.2"),
        ("healthy breakfast ideas", "Conceptual query - should get high alpha ~0.8"),
    ]
    
    for query, expected in test_queries:
        print(f"\n{Fore.CYAN}Expected: {expected}")
        await test_single_search(query)
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())