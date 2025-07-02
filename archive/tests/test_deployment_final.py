#!/usr/bin/env python3
"""Test the deployed system for SKUs, prices, and performance"""

import asyncio
import httpx
import time
import json

async def test_deployed_system():
    base_url = 'https://leafloaf-32905605817.us-central1.run.app'
    
    # Test 1: Search for spinach - verify SKUs and prices
    print('=== Test 1: Spinach Search (SKU verification) ===')
    start = time.time()
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f'{base_url}/api/v1/search',
            json={'query': 'spinach'}
        )
    elapsed = (time.time() - start) * 1000
    
    if response.status_code == 200:
        data = response.json()
        print(f'✓ Search completed in {elapsed:.0f}ms')
        print(f'✓ Found {len(data.get("products", []))} products')
        
        # Check if SKUs are included
        has_sku = False
        for i, product in enumerate(data.get('products', [])[:5]):
            sku = product.get('sku', '')
            name = product.get('product_name', '')
            price = product.get('price', 0)
            product_id = product.get('product_id', '')
            
            print(f'\n{i+1}. {name}')
            if sku:
                print(f'   SKU: {sku}')
                has_sku = True
            else:
                print(f'   ID: {product_id}')
            print(f'   Price: ${price:.2f}')
        
        if not has_sku:
            print('\n⚠️  WARNING: SKUs not included in response!')
            print('   The response_compiler needs to be updated')
    else:
        print(f'✗ Error: {response.status_code}')
        print(response.text)
    
    # Test 2: Generic search with alpha=0.5
    print('\n\n=== Test 2: Breakfast Ideas (alpha=0.5 test) ===')
    start = time.time()
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f'{base_url}/api/v1/search',
            json={'query': 'breakfast ideas'}
        )
    elapsed = (time.time() - start) * 1000
    
    if response.status_code == 200:
        data = response.json()
        print(f'✓ Search completed in {elapsed:.0f}ms')
        print(f'✓ Found {len(data.get("products", []))} products')
        
        # Show execution time breakdown
        exec_data = data.get('execution', {})
        print(f'✓ Total execution: {exec_data.get("total_time_ms", 0):.0f}ms')
        
        # Show categories found
        categories = set()
        for product in data.get('products', []):
            cat = product.get('category', '')
            if cat:
                categories.add(cat)
        if categories:
            print(f'✓ Categories: {sorted(categories)[:5]}...')
    else:
        print(f'✗ Error: {response.status_code}')
    
    # Test 3: Performance test
    print('\n\n=== Test 3: Performance Test (5 queries) ===')
    queries = ['tomatoes', 'organic apples', 'spinach', 'berries', 'fresh herbs']
    times = []
    
    for query in queries:
        start = time.time()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f'{base_url}/api/v1/search',
                json={'query': query}
            )
        elapsed = (time.time() - start) * 1000
        times.append(elapsed)
        
        if response.status_code == 200:
            data = response.json()
            products = len(data.get('products', []))
            exec_time = data.get('execution', {}).get('total_time_ms', 0)
            print(f'✓ {query}: {elapsed:.0f}ms total, {exec_time:.0f}ms execution ({products} products)')
        else:
            print(f'✗ {query}: Failed')
    
    avg_time = sum(times) / len(times)
    print(f'\n📊 Average response time: {avg_time:.0f}ms')
    if avg_time < 300:
        print('✅ MEETING <300ms REQUIREMENT!')
    else:
        print('⚠️  Not meeting <300ms requirement yet')

if __name__ == "__main__":
    asyncio.run(test_deployed_system())