#!/usr/bin/env python3
import weaviate
from weaviate.auth import AuthApiKey

# New credentials
WEAVIATE_URL = "7cijosfpsryfteazzawhjw.c0.us-east1.gcp.weaviate.cloud"
WEAVIATE_KEY = "RDNqMFd0N3YyaHNpL3JheF9NYU1NKzJqRjYvVzR1VUxWSUZPdDZiL2JFbkdOTzY5MEhGOVdTMTZWaW5FPV92MjAw"

print("Testing new Weaviate key...")

try:
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=WEAVIATE_URL,
        auth_credentials=AuthApiKey(WEAVIATE_KEY)
    )
    
    print("✅ Connected!")
    
    # Get collection info
    collection = client.collections.get("Product")
    count = collection.aggregate.over_all(total_count=True).total_count
    print(f"Products: {count}")
    
    # Check vectorizer
    config = collection.config.get()
    print(f"Vectorizer: {config.vectorizer}")
    
    client.close()
    
except Exception as e:
    print(f"❌ Error: {e}")

print("Done")