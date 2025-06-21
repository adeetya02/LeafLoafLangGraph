import weaviate
from weaviate.auth import AuthApiKey
import os
from dotenv import load_dotenv

load_dotenv()

def discover_weaviate():
    """Discover Weaviate schema without knowing class name"""
    url = os.getenv("WEAVIATE_URL")
    api_key = os.getenv("WEAVIATE_API_KEY")
    
    if not url or not api_key:
        print("❌ Missing WEAVIATE_URL or WEAVIATE_API_KEY in .env")
        return
    
    print(f"🔍 Connecting to: {url}\n")
    
    try:
        client = weaviate.connect_to_wcs(
            cluster_url=url,
            auth_credentials=AuthApiKey(api_key)
        )
        
        # Get schema
        schema = client.collections.list_all()
        print(f"📦 Found {len(schema)} collections:\n")
        
        for collection_name in schema:
            print(f"Collection: '{collection_name}'")
            
        # If we found collections, check the first one
        if schema:
            first_collection = list(schema)[0]
            print(f"\n🔍 Checking collection '{first_collection}'...")
            
            collection = client.collections.get(first_collection)
            sample = collection.query.fetch_objects(limit=2)
            
            if sample.objects:
                print(f"\n📋 Properties in '{first_collection}':")
                for key in sample.objects[0].properties.keys():
                    print(f"   - {key}")
                    
                print(f"\n📦 Sample product:")
                print(sample.objects[0].properties)
                
                print(f"\n✅ Add this to your .env file:")
                print(f"WEAVIATE_CLASS_NAME={first_collection}")
                
        client.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    discover_weaviate()