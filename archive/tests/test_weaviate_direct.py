#\!/usr/bin/env python3
"""
Direct Weaviate connectivity test
"""
import weaviate
from weaviate.auth import AuthApiKey
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env.yaml")

# Get Weaviate credentials
WEAVIATE_URL = os.getenv("WEAVIATE_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")

print("=" * 80)
print("🔍 WEAVIATE DIRECT CONNECTIVITY TEST")
print("=" * 80)
print(f"URL: {WEAVIATE_URL}")
print(f"API Key: {WEAVIATE_API_KEY[:10]}..." if WEAVIATE_API_KEY else "No API key found")

# Test 1: Basic connection
print("\n1️⃣ Testing basic connection...")
start = time.time()
try:
    client = weaviate.Client(
        url=WEAVIATE_URL,
        auth_client_secret=AuthApiKey(api_key=WEAVIATE_API_KEY),
        timeout_config=(5, 15)  # 5s connect, 15s read
    )
    
    # Test if client is ready
    if client.is_ready():
        print(f"✅ Connected successfully in {(time.time() - start)*1000:.0f}ms")
    else:
        print("❌ Client not ready")
        
except Exception as e:
    print(f"❌ Connection failed: {e}")

# Test 2: Get schema
print("\n2️⃣ Testing schema access...")
start = time.time()
try:
    schema = client.schema.get()
    print(f"✅ Schema retrieved in {(time.time() - start)*1000:.0f}ms")
    print(f"   Classes: {[c['class'] for c in schema.get('classes', [])]}")
except Exception as e:
    print(f"❌ Schema access failed: {e}")

# Test 3: Simple search
print("\n3️⃣ Testing search functionality...")
start = time.time()
try:
    result = client.query.get(
        "Product", 
        ["name", "brand", "category"]
    ).with_limit(1).do()
    
    elapsed = (time.time() - start) * 1000
    print(f"✅ Search completed in {elapsed:.0f}ms")
    
    if result.get('data', {}).get('Get', {}).get('Product'):
        product = result['data']['Get']['Product'][0]
        print(f"   Sample product: {product.get('name', 'N/A')}")
    else:
        print("   No products found")
        
except Exception as e:
    print(f"❌ Search failed: {e}")

# Test 4: Hybrid search
print("\n4️⃣ Testing hybrid search...")
start = time.time()
try:
    result = client.query.get(
        "Product",
        ["name", "brand", "category", "description"]
    ).with_hybrid(
        query="oatly",
        alpha=0.5
    ).with_limit(5).do()
    
    elapsed = (time.time() - start) * 1000
    print(f"✅ Hybrid search completed in {elapsed:.0f}ms")
    
    products = result.get('data', {}).get('Get', {}).get('Product', [])
    print(f"   Found {len(products)} products")
    for p in products[:3]:
        print(f"   - {p.get('name', 'N/A')} ({p.get('brand', 'N/A')})")
        
except Exception as e:
    print(f"❌ Hybrid search failed: {e}")

# Test 5: Check timeout settings
print("\n5️⃣ Testing with different timeout settings...")
for connect_timeout, read_timeout in [(1, 1), (2, 2), (5, 5), (10, 10)]:
    start = time.time()
    try:
        test_client = weaviate.Client(
            url=WEAVIATE_URL,
            auth_client_secret=AuthApiKey(api_key=WEAVIATE_API_KEY),
            timeout_config=(connect_timeout, read_timeout)
        )
        
        # Quick search
        result = test_client.query.get(
            "Product", ["name"]
        ).with_limit(1).do()
        
        elapsed = (time.time() - start) * 1000
        print(f"   Timeout ({connect_timeout}s, {read_timeout}s): {elapsed:.0f}ms ✅")
        
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        print(f"   Timeout ({connect_timeout}s, {read_timeout}s): {elapsed:.0f}ms ❌ - {str(e)[:50]}...")

print("\n" + "=" * 80)
print("✅ Test complete")
