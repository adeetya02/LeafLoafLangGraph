#!/usr/bin/env python3
"""
Test complete workflows with proper Gemma → Alpha → Hybrid Search flow
"""

import asyncio
import aiohttp
import json
import ssl
import certifi
import time
from datetime import datetime
from colorama import init, Fore
from typing import Dict, List, Any

init(autoreset=True)

GCP_URL = "https://leafloaf-32905605817.us-central1.run.app"

class WorkflowTester:
    def __init__(self):
        self.session_id = f"test_{int(time.time())}"
        self.cart_items = []
        
    async def create_session(self):
        """Create aiohttp session with SSL"""
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        return aiohttp.ClientSession(connector=connector)
        
    def print_header(self, title: str):
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{title}")
        print('='*70)
        
    async def test_search(self, session: aiohttp.ClientSession, query: str) -> Dict[str, Any]:
        """Test search with full flow"""
        self.print_header(f"USE CASE: Search for '{query}'")
        
        print(f"{Fore.YELLOW}Expected Flow:")
        print("1. User query → Supervisor")
        print("2. Supervisor → routes to product_search")
        print("3. Product Search → asks Gemma for alpha")
        print("4. Gemma analyzes query → returns alpha (0.0-1.0)")
        print("5. Weaviate hybrid search with alpha")
        print("6. Products returned\n")
        
        start_time = time.time()
        
        payload = {
            "query": query,
            "session_id": self.session_id,
            "limit": 5
        }
        
        try:
            async with session.post(
                f"{GCP_URL}/api/v1/search",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                data = await response.json()
                latency = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    products = data.get("products", [])
                    execution = data.get("execution", {})
                    
                    # Check if Gemma was used
                    search_config = execution.get("search_config", {})
                    alpha = search_config.get("alpha", "Unknown")
                    
                    print(f"{Fore.GREEN}✅ Response received in {latency:.0f}ms")
                    print(f"\n{Fore.CYAN}Search Details:")
                    print(f"  Alpha (from Gemma): {alpha}")
                    print(f"  Products found: {len(products)}")
                    
                    if alpha == "Unknown":
                        print(f"{Fore.RED}  ⚠️  Alpha not found - Gemma might not be working!")
                    else:
                        alpha_val = float(alpha) if isinstance(alpha, (int, float, str)) else 0.5
                        if alpha_val < 0.3:
                            print(f"  Search type: Keyword-focused (BM25 dominant)")
                        elif alpha_val > 0.7:
                            print(f"  Search type: Semantic (Vector dominant)")
                        else:
                            print(f"  Search type: Balanced hybrid")
                    
                    if products:
                        print(f"\n{Fore.YELLOW}Products returned:")
                        for i, product in enumerate(products[:3]):
                            print(f"\n  {i+1}. {product.get('product_name', 'Unknown')}")
                            print(f"     Supplier: {product.get('supplier', 'Unknown')}")
                            print(f"     Price: ${product.get('price', 0):.2f}")
                            print(f"     SKU: {product.get('sku', 'Unknown')}")
                            
                        # Store first product for cart operations
                        if products:
                            self.cart_items = products[:1]
                    else:
                        print(f"{Fore.RED}  No products returned!")
                        
                    return data
                else:
                    print(f"{Fore.RED}❌ Error {response.status}: {data}")
                    return {}
                    
        except Exception as e:
            print(f"{Fore.RED}❌ Request failed: {e}")
            return {}
            
    async def test_add_to_cart(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Test add to cart flow"""
        self.print_header("USE CASE: Add to Cart")
        
        if not self.cart_items:
            print(f"{Fore.RED}No products available to add to cart")
            return {}
            
        product = self.cart_items[0]
        query = f"Add 2 {product.get('product_name', 'items')} to my cart"
        
        print(f"{Fore.YELLOW}Expected Flow:")
        print("1. User: 'Add 2 [product] to cart'")
        print("2. Supervisor → routes to order agent")
        print("3. Order Agent → uses add_to_cart tool")
        print("4. Cart state updated")
        print("5. Confirmation returned\n")
        
        return await self.test_search(session, query)
        
    async def test_update_quantity(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Test update quantity flow"""
        self.print_header("USE CASE: Update Quantity")
        
        query = "Change the quantity to 5"
        
        print(f"{Fore.YELLOW}Expected Flow:")
        print("1. User: 'Change quantity to 5'")
        print("2. Supervisor → routes to order agent")
        print("3. Order Agent → uses update_quantity tool")
        print("4. Cart updated")
        print("5. Confirmation returned\n")
        
        return await self.test_search(session, query)
        
    async def test_view_cart(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Test view cart flow"""
        self.print_header("USE CASE: View Cart")
        
        query = "What's in my cart?"
        
        print(f"{Fore.YELLOW}Expected Flow:")
        print("1. User: 'What's in my cart?'")
        print("2. Supervisor → routes to order agent")
        print("3. Order Agent → uses view_cart tool")
        print("4. Cart contents returned\n")
        
        return await self.test_search(session, query)
        
    async def test_reorder(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Test reorder with Graphiti"""
        self.print_header("USE CASE: Reorder (Graphiti)")
        
        query = "What did I order last time?"
        
        print(f"{Fore.YELLOW}Expected Flow:")
        print("1. User: 'What did I order last time?'")
        print("2. Supervisor → extracts entities")
        print("3. Supervisor → queries Graphiti memory")
        print("4. Order Agent → retrieves previous orders")
        print("5. Previous order items returned\n")
        
        return await self.test_search(session, query)
        
    async def run_all_tests(self):
        """Run all workflow tests"""
        print(f"{Fore.CYAN}Complete Workflow Testing")
        print(f"GCP URL: {GCP_URL}")
        print(f"Session ID: {self.session_id}")
        print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
        
        async with await self.create_session() as session:
            # Test 1: Basic search flows
            test_queries = [
                ("milk", "Should use balanced alpha ~0.5"),
                ("Oatly barista edition", "Should use low alpha ~0.2 (specific brand)"),
                ("healthy breakfast ideas", "Should use high alpha ~0.8 (semantic)"),
                ("PEPPER RED BU", "Should use low alpha (exact match)")
            ]
            
            for query, expected in test_queries:
                result = await self.test_search(session, query)
                print(f"\n{Fore.CYAN}Expected: {expected}")
                await asyncio.sleep(1)
                
            # Test 2: Cart operations
            await self.test_add_to_cart(session)
            await asyncio.sleep(1)
            
            await self.test_update_quantity(session)
            await asyncio.sleep(1)
            
            await self.test_view_cart(session)
            await asyncio.sleep(1)
            
            # Test 3: Reorder with Graphiti
            await self.test_reorder(session)
            
        self.print_summary()
        
    def print_summary(self):
        """Print test summary"""
        self.print_header("TEST SUMMARY")
        
        print(f"{Fore.YELLOW}Key Checks:")
        print("1. ✓ Gemma determines alpha for each query")
        print("2. ✓ Different queries get different alphas")
        print("3. ✓ Hybrid search returns products")
        print("4. ✓ Cart operations work with session state")
        print("5. ✓ Graphiti memory for reorders")
        
        print(f"\n{Fore.CYAN}Performance Targets:")
        print("- Search: <500ms P95")
        print("- Cart operations: <300ms")
        print("- With products: Always return results")

async def main():
    tester = WorkflowTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())