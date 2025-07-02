#!/usr/bin/env python3
"""
Test Weaviate connection with credentials from settings
"""

import weaviate
from weaviate.auth import AuthApiKey
from src.config.settings import settings

print("=" * 80)
print("🔍 TESTING WEAVIATE CONNECTION")
print("=" * 80)

print(f"\n📡 Connecting to: {settings.weaviate_url}")
print(f"   API Key: {settings.weaviate_api_key[:20]}...")

try:
    # Remove https:// prefix for connect_to_weaviate_cloud
    cluster_url = settings.weaviate_url.replace("https://", "").replace("http://", "")
    
    # Connect
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=cluster_url,
        auth_credentials=AuthApiKey(settings.weaviate_api_key)
    )
    
    print("\n✅ Connected successfully!")
    
    # Check collections
    print("\n📦 Collections in cluster:")
    collections = client.collections.list_all()
    
    for collection_name in collections:
        print(f"\n   Collection: {collection_name}")
        try:
            collection = client.collections.get(collection_name)
            config = collection.config.get()
            
            # Get count using aggregate
            agg_result = collection.aggregate.over_all(total_count=True)
            count = agg_result.total_count if agg_result else 0
            
            print(f"   - Objects: {count}")
            print(f"   - Vectorizer: {config.vectorizer if config.vectorizer else 'None (BM25 only)'}")
            
            # Test BM25 search
            print("\n   Testing BM25 search...")
            result = collection.query.bm25(
                query="organic",
                limit=3
            )
            print(f"   ✅ BM25 works! Found {len(result.objects)} results")
            
            # Show first result
            if result.objects:
                first = result.objects[0].properties
                print(f"   Example: {first.get('name', 'No name')} - ${first.get('retailPrice', 0):.2f}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    client.close()
    
except Exception as e:
    print(f"\n❌ Connection error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)