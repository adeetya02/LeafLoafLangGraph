import weaviate
from weaviate.auth import AuthApiKey
import os
from dotenv import load_dotenv
from pathlib import Path
import json

# Load .env from the project root
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

def check_config():
    """Check Weaviate configuration and schema"""
    url = os.getenv("WEAVIATE_URL")
    api_key = os.getenv("WEAVIATE_API_KEY")
    
    # Connect without HF key first
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=url,
        auth_credentials=AuthApiKey(api_key)
    )
    
    try:
        print("🔍 Checking Weaviate Configuration\n")
        
        # Get all collections
        collections = client.collections.list_all()
        print(f"📦 Found {len(collections)} collections:\n")
        
        for idx, collection_name in enumerate(collections):
            print(f"\n{idx+1}. Collection: '{collection_name}'")
            
            collection = client.collections.get(collection_name)
            
            # Get sample data
            sample = collection.query.fetch_objects(limit=2)
            
            if sample.objects:
                print(f"   Objects count: {len(sample.objects)}")
                print(f"   Properties: {list(sample.objects[0].properties.keys())}")
                
                # Check for products
                first_item = sample.objects[0].properties
                if 'name' in first_item:
                    print(f"   Sample: {first_item.get('name', 'N/A')}")
                    
            # Get config
            try:
                config = collection.config.get()
                print(f"   Vectorizer: {config.vectorizer}")
            except:
                print(f"   Vectorizer: Unable to retrieve")
        
        print(f"\n💡 Current .env setting: WEAVIATE_CLASS_NAME={os.getenv('WEAVIATE_CLASS_NAME', 'Not Set')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
    finally:
        client.close()

if __name__ == "__main__":
    check_config()