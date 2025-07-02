#\!/usr/bin/env python3
"""
Test Weaviate v4 connectivity
"""
import weaviate
from weaviate.auth import AuthApiKey
import time
import os

# Hardcode the credentials from .env.yaml
WEAVIATE_URL = "https://7cijosfpsryfteazzawhjw.c0.us-east1.gcp.weaviate.cloud"
WEAVIATE_API_KEY = "QWhiUlhJcFptTGEvV1ZNRF8wZ1QxWGZmblVnakFTclN4RitPc3JEMzZWTFdBNW9BaVJkMktJcFN5TjhRPV92MjAw"

print("=" * 80)
print("🔍 WEAVIATE V4 CONNECTIVITY TEST")
print("=" * 80)
print(f"URL: {WEAVIATE_URL}")
print(f"API Key: {WEAVIATE_API_KEY[:20]}...")

# Test 1: Connect with v4 API
print("\n1️⃣ Testing v4 connection...")
start = time.time()
try:
    # Use v4 connection method
    client = weaviate.connect_to_wcs(
        cluster_url=WEAVIATE_URL,
        auth_credentials=AuthApiKey(WEAVIATE_API_KEY),
        headers={
            "X-Weaviate-Api-Key": WEAVIATE_API_KEY
        }
    )
    
    print(f"✅ Connected successfully in {(time.time() - start)*1000:.0f}ms")
    
    # Test 2: Check if ready
    print("\n2️⃣ Testing readiness...")
    start = time.time()
    try:
        is_ready = client.is_ready()
        print(f"✅ Ready check: {is_ready} ({(time.time() - start)*1000:.0f}ms)")
    except Exception as e:
        print(f"❌ Ready check failed: {e}")
    
    # Test 3: Get collections
    print("\n3️⃣ Getting collections...")
    start = time.time()
    try:
        collections = client.collections.list_all()
        print(f"✅ Collections retrieved in {(time.time() - start)*1000:.0f}ms")
        for collection in collections:
            print(f"   - {collection}")
    except Exception as e:
        print(f"❌ Collections failed: {e}")
    
    # Test 4: Search products
    print("\n4️⃣ Testing product search...")
    start = time.time()
    try:
        products = client.collections.get("Product")
        
        # Simple query
        result = products.query.fetch_objects(limit=5)
        
        elapsed = (time.time() - start) * 1000
        print(f"✅ Search completed in {elapsed:.0f}ms")
        print(f"   Found {len(result.objects)} products")
        
        for obj in result.objects[:3]:
            props = obj.properties
            print(f"   - {props.get('name', 'N/A')} ({props.get('brand', 'N/A')})")
            
    except Exception as e:
        print(f"❌ Search failed: {e}")
    
    # Test 5: Hybrid search
    print("\n5️⃣ Testing hybrid search...")
    start = time.time()
    try:
        products = client.collections.get("Product")
        
        # Hybrid search
        result = products.query.hybrid(
            query="oatly",
            alpha=0.5,
            limit=5
        )
        
        elapsed = (time.time() - start) * 1000
        print(f"✅ Hybrid search completed in {elapsed:.0f}ms")
        print(f"   Found {len(result.objects)} products")
        
        for obj in result.objects[:3]:
            props = obj.properties
            print(f"   - {props.get('name', 'N/A')} ({props.get('brand', 'N/A')})")
            
    except Exception as e:
        print(f"❌ Hybrid search failed: {e}")
    
    # Close connection
    client.close()
    
except Exception as e:
    print(f"❌ Connection failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("✅ Test complete")
