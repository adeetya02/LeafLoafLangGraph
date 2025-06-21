import weaviate
from weaviate.auth import AuthApiKey
from dotenv import load_dotenv
from pathlib import Path
import os

# Load .env
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

def debug_search():
    """Debug why search isn't finding products"""
    
    # Get credentials
    url = os.getenv("WEAVIATE_URL")
    api_key = os.getenv("WEAVIATE_API_KEY")
    hf_key = os.getenv("HUGGINGFACE_API_KEY")
    
    print(f"🔑 Credentials loaded: Weaviate ✓, HF ✓" if hf_key else "Missing HF key")
    
    # Connect
    headers = {"X-HuggingFace-Api-Key": hf_key} if hf_key else {}
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=url,
        auth_credentials=AuthApiKey(api_key),
        headers=headers
    )
    
    try:
        collection = client.collections.get("Product")
        
        # 1. Check total count
        all_items = collection.query.fetch_objects(limit=5)
        print(f"\n📦 Total products accessible: {len(all_items.objects)}")
        
        # 2. Show sample products
        print("\n📋 Sample products:")
        for i, obj in enumerate(all_items.objects[:3]):
            print(f"\n{i+1}. Product:")
            print(f"   Name: {obj.properties.get('name')}")
            print(f"   SKU: {obj.properties.get('sku')}")
            print(f"   Category: {obj.properties.get('category')}")
            print(f"   Search Terms: {obj.properties.get('searchTerms')}")
        
        # 3. Try different search methods
        test_queries = ["potato", "tomato", "organic", "fresh"]
        
        for query in test_queries:
            print(f"\n🔍 Testing '{query}':")
            
            # BM25 (keyword)
            try:
                bm25_results = collection.query.bm25(query=query, limit=3)
                print(f"   BM25: {len(bm25_results.objects)} results")
            except Exception as e:
                print(f"   BM25: Failed - {str(e)[:50]}")
            
            # Hybrid
            try:
                hybrid_results = collection.query.hybrid(query=query, alpha=0.7, limit=3)
                print(f"   Hybrid: {len(hybrid_results.objects)} results")
            except Exception as e:
                print(f"   Hybrid: Failed - {str(e)[:50]}")
                
    finally:
        client.close()

if __name__ == "__main__":
    debug_search()