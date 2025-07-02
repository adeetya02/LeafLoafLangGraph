#!/usr/bin/env python3
"""Test Weaviate connection and status"""

import weaviate
from weaviate.connect import ConnectionParams
from weaviate.auth import AuthApiKey
import os

# Get Weaviate credentials directly from .env.yaml
WEAVIATE_URL = "https://leafloaf-7xk8zor5.weaviate.network"
WEAVIATE_API_KEY = "dqgYpdMBw06CL7XMSuHaxDNiW2kBoCrYtRDR"

print(f"Testing Weaviate at: {WEAVIATE_URL}")

try:
    # Create v4 client
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=WEAVIATE_URL.replace("https://", ""),
        auth_credentials=AuthApiKey(WEAVIATE_API_KEY)
    )
    
    # Test connection
    print("\n1. Testing connection...")
    if client.is_ready():
        print("✅ Weaviate is ready!")
    else:
        print("❌ Weaviate is not ready")
    
    # Get schema
    print("\n2. Checking schema...")
    schema = client.schema.get()
    if schema.get('classes'):
        print(f"✅ Found {len(schema['classes'])} classes:")
        for cls in schema['classes']:
            print(f"   - {cls['class']}")
    else:
        print("❌ No classes found in schema")
    
    # Count products
    print("\n3. Counting products...")
    try:
        result = client.query.aggregate("Product").with_meta_count().do()
        if result and 'data' in result:
            count = result['data']['Aggregate']['Product'][0]['meta']['count']
            print(f"✅ Found {count} products in database")
        else:
            print("❌ Could not count products")
    except Exception as e:
        print(f"❌ Error counting products: {e}")
    
    # Test search
    print("\n4. Testing search...")
    try:
        result = client.query.get("Product", ["name", "description"]).with_limit(5).do()
        if result and 'data' in result and result['data']['Get']['Product']:
            print(f"✅ Sample products:")
            for p in result['data']['Get']['Product'][:3]:
                print(f"   - {p.get('name', 'Unknown')}")
        else:
            print("❌ No products found in search")
    except Exception as e:
        print(f"❌ Error searching: {e}")
    
except Exception as e:
    print(f"\n❌ Failed to connect to Weaviate: {e}")
    print("\nPossible issues:")
    print("- Weaviate instance might be paused or deleted")
    print("- API key might be invalid")
    print("- Network connectivity issues")
    print("- Credits might be exhausted")