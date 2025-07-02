#!/usr/bin/env python3
"""
Test cart operations end-to-end
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

class CartTester:
    def __init__(self):
        self.session_id = f"cart_test_{int(time.time())}"
        
    async def test_operation(self, query: str, operation_name: str):
        """Test a single cart operation"""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"Operation: {operation_name}")
        print(f"Query: '{query}'")
        print('='*60)
        
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            payload = {
                "query": query,
                "session_id": self.session_id,
                "limit": 5
            }
            
            start_time = time.time()
            
            try:
                async with session.post(
                    f"{GCP_URL}/api/v1/search",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    latency = (time.time() - start_time) * 1000
                    data = await response.json()
                    
                    if response.status == 200:
                        # Extract key information
                        execution = data.get("execution", {})
                        metadata = data.get("metadata", {})
                        
                        print(f"\n{Fore.YELLOW}Response Details:")
                        print(f"  Status: {response.status}")
                        print(f"  Latency: {latency:.0f}ms")
                        print(f"  Success: {data.get('success', False)}")
                        
                        # Check reasoning
                        reasoning = execution.get("reasoning_steps", [])
                        if reasoning:
                            print(f"\n{Fore.YELLOW}Reasoning:")
                            for step in reasoning:
                                print(f"  - {step}")
                        
                        # Check agents run
                        agents_run = execution.get("agents_run", [])
                        print(f"\n{Fore.YELLOW}Agents Executed: {agents_run}")
                        
                        # Check for order response
                        if "order_response" in data:
                            print(f"\n{Fore.GREEN}✓ Order Response Found:")
                            print(json.dumps(data["order_response"], indent=2))
                        else:
                            print(f"\n{Fore.RED}✗ No order_response in data")
                        
                        # Check for products (shouldn't be there for cart ops)
                        if data.get("products"):
                            print(f"\n{Fore.BLUE}Products returned: {len(data['products'])}")
                            print(f"{Fore.RED}⚠️  Got search results instead of cart operation!")
                        
                        # Show message
                        if data.get("message"):
                            print(f"\n{Fore.CYAN}Message: {data['message']}")
                        
                        # Debug: show all top-level keys
                        print(f"\n{Fore.YELLOW}Response Keys: {list(data.keys())}")
                        
                    else:
                        print(f"{Fore.RED}Error {response.status}: {data}")
                        
            except Exception as e:
                print(f"{Fore.RED}Request failed: {e}")
    
    async def run_full_workflow(self):
        """Run a complete cart workflow"""
        print(f"{Fore.CYAN}Cart Operations Test")
        print(f"Session ID: {self.session_id}")
        print(f"URL: {GCP_URL}")
        
        # Test 1: Search for a product first
        await self.test_operation("milk", "1. Search for Product")
        await asyncio.sleep(1)
        
        # Test 2: Add to cart
        await self.test_operation("add milk to my cart", "2. Add to Cart")
        await asyncio.sleep(1)
        
        # Test 3: View cart
        await self.test_operation("what's in my cart?", "3. View Cart")
        await asyncio.sleep(1)
        
        # Test 4: Update quantity
        await self.test_operation("change milk quantity to 3", "4. Update Quantity")
        await asyncio.sleep(1)
        
        # Test 5: Remove from cart
        await self.test_operation("remove milk from cart", "5. Remove Item")
        
        # Summary
        print(f"\n{Fore.CYAN}{'='*60}")
        print("Test Complete!")
        print('='*60)

async def main():
    tester = CartTester()
    await tester.run_full_workflow()

if __name__ == "__main__":
    asyncio.run(main())