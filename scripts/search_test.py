import weaviate
from weaviate.auth import AuthApiKey
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from the project root
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

def test_search():
    """Test different search methods on Weaviate"""
    url = os.getenv("WEAVIATE_URL")
    api_key = os.getenv("WEAVIATE_API_KEY")
    
    print(f"📁 Loading .env from: {env_path}")
    print(f"🔗 Weaviate URL: {url}")
    print(f"🔑 API Key: {'*' * 10 if api_key else 'NOT FOUND'}\n")
    
    if not url or not api_key:
        print("❌ Missing WEAVIATE_URL or WEAVIATE_API_KEY in .env file")
        return
    
    # Use the new method name
    hf_api_key = os.getenv("HUGGINGFACE_API_KEY")

    # Set up additional headers
    additional_headers = {
    "X-HuggingFace-Api-Key": hf_api_key
    } if hf_api_key else {}

    # Use the new method name with headers
    client = weaviate.connect_to_weaviate_cloud(
    cluster_url=url,
    auth_credentials=AuthApiKey(api_key),
    headers=additional_headers
)
    
    try:
        collection = client.collections.get("Product")
        
        print("🔍 Testing Weaviate Search\n")
        
        # 1. First, let's see if potatoes exist at all
        print("1. Checking all products for 'potato':")
        all_products = collection.query.fetch_objects(limit=1000)
        potato_products = []
        
        for obj in all_products.objects:
            name = str(obj.properties.get('name', '')).lower()
            # Handle searchTerms as a list
            search_terms = obj.properties.get('searchTerms', [])
            if isinstance(search_terms, list):
                search_terms_str = ' '.join(search_terms).lower()
            else:
                search_terms_str = str(search_terms).lower()
                
            if 'potato' in name or 'potato' in search_terms_str:
                potato_products.append(obj.properties)
                print(f"   Found: {obj.properties.get('name')} - SKU: {obj.properties.get('sku')}")
        
        print(f"\n   Total potato products: {len(potato_products)}")
        
        # 2. Test hybrid search
        print("\n2. Testing hybrid search for 'potatoes':")
        hybrid_results = collection.query.hybrid(
            query="potatoes",
            alpha=0.7,
            limit=10
        )
        print(f"   Found {len(hybrid_results.objects)} results")
        for obj in hybrid_results.objects:
            print(f"   - {obj.properties.get('name')}")
        
        # 3. Test keyword search
        print("\n3. Testing keyword (BM25) search for 'potatoes':")
        keyword_results = collection.query.bm25(
            query="potatoes",
            limit=10
        )
        print(f"   Found {len(keyword_results.objects)} results")
        for obj in keyword_results.objects:
            print(f"   - {obj.properties.get('name')}")
        
        # 4. Show a sample product to see structure
        print("\n4. Sample product structure:")
        if all_products.objects:
            sample = all_products.objects[0].properties
            for key, value in sample.items():
                if isinstance(value, list):
                    print(f"   {key}: {value[:3]}...")  # Show first 3 items if list
                else:
                    print(f"   {key}: {value}")
                    
    finally:
        client.close()

if __name__ == "__main__":
    test_search()