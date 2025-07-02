#!/usr/bin/env python3
"""
Test routing for different query types
"""

import asyncio
import aiohttp
import json
import ssl
import certifi
from colorama import init, Fore

init(autoreset=True)

GCP_URL = "https://leafloaf-32905605817.us-central1.run.app"

async def test_routing(query: str, expected_route: str):
    """Test where a query gets routed"""
    
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        payload = {"query": query, "limit": 2}
        
        try:
            async with session.post(
                f"{GCP_URL}/api/v1/search",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                data = await response.json()
                
                # Check execution details
                execution = data.get("execution", {})
                reasoning = execution.get("reasoning_steps", [])
                agents_run = execution.get("agents_run", [])
                
                # Look for routing info
                routing_info = None
                for step in reasoning:
                    if "Intent:" in step:
                        routing_info = step
                        break
                
                # Check if order agent was used
                used_order_agent = "order_agent" in agents_run
                
                print(f"\n{Fore.CYAN}Query: '{query}'")
                print(f"{Fore.YELLOW}Expected: Route to {expected_route}")
                print(f"Reasoning: {routing_info}")
                print(f"Agents run: {agents_run}")
                
                # Check the response type
                if data.get("order_response"):
                    print(f"{Fore.GREEN}✓ Got order response")
                elif data.get("products"):
                    print(f"{Fore.BLUE}Got search results ({len(data['products'])} products)")
                else:
                    print(f"{Fore.RED}No products or order response")
                
                # Verify routing
                if expected_route == "order_agent" and used_order_agent:
                    print(f"{Fore.GREEN}✅ Correctly routed to order agent")
                elif expected_route == "product_search" and not used_order_agent:
                    print(f"{Fore.GREEN}✅ Correctly routed to product search")
                else:
                    print(f"{Fore.RED}❌ Routing mismatch!")
                    
        except Exception as e:
            print(f"{Fore.RED}Error: {e}")

async def main():
    print(f"{Fore.CYAN}Testing Query Routing")
    print(f"URL: {GCP_URL}")
    
    test_cases = [
        # Search queries (should go to product_search)
        ("milk", "product_search"),
        ("show me organic bananas", "product_search"),
        ("I need bread", "product_search"),
        
        # Cart operations (should go to order_agent)
        ("add milk to my cart", "order_agent"),
        ("put 2 bananas in my basket", "order_agent"),
        ("I'll take 3 of those", "order_agent"),
        ("add the first one to cart", "order_agent"),
        
        # Other order operations
        ("what's in my cart?", "order_agent"),
        ("remove milk from cart", "order_agent"),
        ("change quantity to 5", "order_agent"),
    ]
    
    for query, expected in test_cases:
        await test_routing(query, expected)
        print("-" * 60)
        await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(main())