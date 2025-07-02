#\!/usr/bin/env python3
"""
Simple Weaviate v4 test without GRPC
"""
import weaviate
from weaviate.auth import AuthApiKey
import time
from src.config.settings import settings

print("=" * 80)
print("🔍 SIMPLE WEAVIATE V4 TEST")
print("=" * 80)

# Test with v4 API
start = time.time()
try:
    # Use HTTP protocol instead of GRPC
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=settings.weaviate_url,
        auth_credentials=AuthApiKey(settings.weaviate_api_key),
        headers={
            "X-Weaviate-Api-Key": settings.weaviate_api_key,
        },
        additional_config=weaviate.config.AdditionalConfig(
            timeout=(5, 15),  # 5s connect, 15s read
        )
    )
    
    print(f"✅ Connected in {(time.time() - start)*1000:.0f}ms")
    
    # Test readiness
    start = time.time()
    is_ready = client.is_ready()
    print(f"✅ Ready: {is_ready} ({(time.time() - start)*1000:.0f}ms)")
    
    # Get collection
    start = time.time()
    collection = client.collections.get("Product")
    print(f"✅ Got collection in {(time.time() - start)*1000:.0f}ms")
    
    # Simple fetch without vector search (avoids GRPC)
    print("\n📦 Testing simple fetch...")
    start = time.time()
    result = collection.query.fetch_objects(limit=5)
    elapsed = (time.time() - start) * 1000
    print(f"✅ Fetch completed in {elapsed:.0f}ms")
    print(f"   Found {len(result.objects)} products")
    
    for obj in result.objects[:3]:
        props = obj.properties
        print(f"   - {props.get('product_name', 'N/A')} (${props.get('price', 0):.2f})")
    
    # Test BM25 search (keyword only, no vectors)
    print("\n🔍 Testing BM25 search...")
    start = time.time()
    result = collection.query.bm25(
        query="oatly",
        limit=5
    )
    elapsed = (time.time() - start) * 1000
    print(f"✅ BM25 search completed in {elapsed:.0f}ms")
    print(f"   Found {len(result.objects)} products")
    
    for obj in result.objects[:3]:
        props = obj.properties
        print(f"   - {props.get('product_name', 'N/A')} ({props.get('brand', 'N/A')})")
    
    # Close properly
    client.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("✅ Test complete")