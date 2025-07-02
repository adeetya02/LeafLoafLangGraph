#!/usr/bin/env python3
"""
Test direct search without pooling
"""
import weaviate
from weaviate.auth import AuthApiKey
import weaviate.config
import time
from src.config.settings import settings

print("Testing direct Weaviate v4 search...")

# Create simple client
client = weaviate.connect_to_weaviate_cloud(
    cluster_url=settings.weaviate_url,
    auth_credentials=AuthApiKey(settings.weaviate_api_key),
    additional_config=weaviate.config.AdditionalConfig(
        timeout=(5, 15),
    )
)

try:
    collection = client.collections.get("Product")
    
    # Test BM25 search
    print("\n🔍 BM25 Search for 'beets':")
    start = time.time()
    result = collection.query.bm25(
        query="beets",
        limit=5,
        return_properties=["name", "category", "retailPrice", "sku"]
    )
    elapsed = (time.time() - start) * 1000
    
    print(f"✅ Search completed in {elapsed:.0f}ms")
    print(f"   Found {len(result.objects)} products:")
    for obj in result.objects:
        props = obj.properties
        print(f"   - {props.get('name', 'N/A')} (${props.get('retailPrice', 0):.2f})")

finally:
    client.close()

print("\n✅ Test complete")