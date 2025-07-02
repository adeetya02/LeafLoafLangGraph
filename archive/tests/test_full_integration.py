#!/usr/bin/env python3
"""
Full integration test: Search → Add to Cart → Update → Delete → Confirm Order
Tests the complete user journey with session memory
"""

import asyncio
import httpx
import json
import uuid
from typing import Dict, List, Any

class IntegrationTester:
    def __init__(self):
        self.base_url = 'https://leafloaf-32905605817.us-central1.run.app'
        self.session_id = str(uuid.uuid4())
        self.cart_items = []
    
    async def search_products(self, query: str) -> Dict:
        """Search for products"""
        print(f"\n🔍 Searching for: '{query}'")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f'{self.base_url}/api/v1/search',
                json={
                    'query': query,
                    'session_id': self.session_id
                }
            )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {len(data.get('products', []))} products")
            
            # Display first 3 products
            for i, product in enumerate(data.get('products', [])[:3], 1):
                print(f"   {i}. {product.get('product_name')} - ${product.get('price', 0):.2f} (SKU: {product.get('sku')})")
            
            return data
        else:
            print(f"❌ Search failed: {response.status_code}")
            return {}
    
    async def add_to_cart(self, product_name: str, quantity: int = 1) -> Dict:
        """Add item to cart"""
        print(f"\n🛒 Adding to cart: {product_name} (qty: {quantity})")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f'{self.base_url}/api/v1/search',
                json={
                    'query': f"add {quantity} {product_name} to my cart",
                    'session_id': self.session_id
                }
            )
        
        if response.status_code == 200:
            print(f"✅ Added to cart")
            return response.json()
        else:
            print(f"❌ Failed to add to cart: {response.status_code}")
            return {}
    
    async def update_quantity(self, product_name: str, new_quantity: int) -> Dict:
        """Update item quantity in cart"""
        print(f"\n📝 Updating quantity: {product_name} to {new_quantity}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f'{self.base_url}/api/v1/search',
                json={
                    'query': f"update {product_name} quantity to {new_quantity}",
                    'session_id': self.session_id
                }
            )
        
        if response.status_code == 200:
            print(f"✅ Updated quantity")
            return response.json()
        else:
            print(f"❌ Failed to update: {response.status_code}")
            return {}
    
    async def remove_from_cart(self, product_name: str) -> Dict:
        """Remove item from cart"""
        print(f"\n🗑️  Removing from cart: {product_name}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f'{self.base_url}/api/v1/search',
                json={
                    'query': f"remove {product_name} from my cart",
                    'session_id': self.session_id
                }
            )
        
        if response.status_code == 200:
            print(f"✅ Removed from cart")
            return response.json()
        else:
            print(f"❌ Failed to remove: {response.status_code}")
            return {}
    
    async def view_cart(self) -> Dict:
        """View current cart"""
        print(f"\n📋 Viewing cart")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f'{self.base_url}/api/v1/search',
                json={
                    'query': "show my cart",
                    'session_id': self.session_id
                }
            )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Cart contents:")
            # Parse cart from message or response
            return data
        else:
            print(f"❌ Failed to view cart: {response.status_code}")
            return {}
    
    async def confirm_order(self) -> Dict:
        """Confirm the order"""
        print(f"\n✅ Confirming order")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f'{self.base_url}/api/v1/search',
                json={
                    'query': "confirm my order",
                    'session_id': self.session_id
                }
            )
        
        if response.status_code == 200:
            print(f"✅ Order confirmed!")
            return response.json()
        else:
            print(f"❌ Failed to confirm order: {response.status_code}")
            return {}
    
    async def run_scenario(self, scenario_name: str, steps: List[Dict]):
        """Run a complete scenario"""
        print(f"\n{'='*80}")
        print(f"SCENARIO: {scenario_name}")
        print(f"Session ID: {self.session_id}")
        print(f"{'='*80}")
        
        for step in steps:
            action = step['action']
            
            if action == 'search':
                await self.search_products(step['query'])
            elif action == 'add':
                await self.add_to_cart(step['product'], step.get('quantity', 1))
            elif action == 'update':
                await self.update_quantity(step['product'], step['quantity'])
            elif action == 'remove':
                await self.remove_from_cart(step['product'])
            elif action == 'view':
                await self.view_cart()
            elif action == 'confirm':
                await self.confirm_order()
            
            # Small delay between actions
            await asyncio.sleep(0.5)

async def main():
    """Run multiple integration test scenarios"""
    
    # Scenario 1: Basic grocery shopping
    print("\n" + "="*80)
    print("FULL INTEGRATION TESTS - COMPLETE USER JOURNEY")
    print("="*80)
    
    tester1 = IntegrationTester()
    await tester1.run_scenario(
        "Basic Grocery Shopping",
        [
            {'action': 'search', 'query': 'organic spinach'},
            {'action': 'add', 'product': 'spinach', 'quantity': 2},
            {'action': 'search', 'query': 'fresh tomatoes'},
            {'action': 'add', 'product': 'tomatoes', 'quantity': 3},
            {'action': 'search', 'query': 'whole milk'},
            {'action': 'add', 'product': 'milk', 'quantity': 1},
            {'action': 'view'},
            {'action': 'update', 'product': 'spinach', 'quantity': 3},
            {'action': 'remove', 'product': 'milk'},
            {'action': 'view'},
            {'action': 'confirm'}
        ]
    )
    
    # Scenario 2: SKU-based ordering
    print("\n" + "="*100)
    tester2 = IntegrationTester()
    await tester2.run_scenario(
        "SKU-Based Ordering",
        [
            {'action': 'search', 'query': 'SP6BW1'},  # Specific SKU
            {'action': 'add', 'product': 'SP6BW1', 'quantity': 1},
            {'action': 'search', 'query': 'SALADSF04'},  # Another SKU
            {'action': 'add', 'product': 'SALADSF04', 'quantity': 2},
            {'action': 'view'},
            {'action': 'confirm'}
        ]
    )
    
    # Scenario 3: Dietary preferences
    print("\n" + "="*100)
    tester3 = IntegrationTester()
    await tester3.run_scenario(
        "Dietary Preferences Shopping",
        [
            {'action': 'search', 'query': 'gluten free pasta'},
            {'action': 'add', 'product': 'pasta', 'quantity': 2},
            {'action': 'search', 'query': 'dairy free cheese'},
            {'action': 'add', 'product': 'cheese', 'quantity': 1},
            {'action': 'search', 'query': 'organic vegetables'},
            {'action': 'add', 'product': 'vegetables', 'quantity': 5},
            {'action': 'update', 'product': 'pasta', 'quantity': 3},
            {'action': 'view'},
            {'action': 'confirm'}
        ]
    )
    
    # Scenario 4: Contextual memory test
    print("\n" + "="*100)
    tester4 = IntegrationTester()
    await tester4.run_scenario(
        "Contextual Memory Test",
        [
            {'action': 'search', 'query': 'apples'},
            {'action': 'add', 'product': 'apples', 'quantity': 6},
            {'action': 'search', 'query': 'add more apples'},  # Test context
            {'action': 'search', 'query': 'berries for smoothie'},
            {'action': 'add', 'product': 'berries', 'quantity': 2},
            {'action': 'search', 'query': 'double the berries'},  # Test context
            {'action': 'view'},
            {'action': 'remove', 'product': 'apples'},
            {'action': 'confirm'}
        ]
    )

if __name__ == "__main__":
    asyncio.run(main())