#!/usr/bin/env python3
"""
Test with the original API key that was working
"""

import weaviate
from weaviate.auth import AuthApiKey

print("=" * 80)
print("🔍 TESTING WITH ORIGINAL CREDENTIALS")
print("=" * 80)

# Original credentials that worked before
WEAVIATE_URL = "7cijosfpsryfteazzawhjw.c0.us-east1.gcp.weaviate.cloud"
WEAVIATE_KEY = "U2U2UFoveExPaG9mVExaaV92ZDVkUUUxSUkzZVVkRElHSTFyNUpzMnppNEJ1NmtEZm82eEtSQVg4eDZ3PV92MjAw"

print(f"\n📡 Connecting to: {WEAVIATE_URL}")

try:
    # Connect
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=WEAVIATE_URL,
        auth_credentials=AuthApiKey(WEAVIATE_KEY)
    )
    
    print("✅ Connected successfully!")
    
    # Get Product collection
    collection = client.collections.get("Product")
    
    # Get count
    agg_result = collection.aggregate.over_all(total_count=True)
    count = agg_result.total_count if agg_result else 0
    
    print(f"\n📦 Product collection:")
    print(f"   - Objects: {count}")
    
    # Check vectorizer
    config = collection.config.get()
    print(f"   - Vectorizer: {config.vectorizer if config.vectorizer else 'None (BM25 only)'}")
    
    # Test BM25 search
    print("\n🔍 Testing BM25 search...")
    result = collection.query.bm25(
        query="organic",
        limit=5
    )
    
    print(f"   Found {len(result.objects)} results:")
    for i, obj in enumerate(result.objects):
        product = obj.properties
        print(f"   {i+1}. {product.get('name', 'Unknown')} - ${product.get('retailPrice', 0):.2f}")
    
    client.close()
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)