import weaviate
from weaviate.auth import AuthApiKey
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env
env_path = Path(__file__).parent.parent / '.env'
print(f"📁 Loading .env from: {env_path}")
print(f"📁 File exists: {env_path.exists()}")

# Force reload
load_dotenv(env_path, override=True)

def test_auth_methods():
    """Test different HuggingFace authentication methods"""
    url = os.getenv("WEAVIATE_URL")
    api_key = os.getenv("WEAVIATE_API_KEY")
    hf_key = os.getenv("HUGGINGFACE_API_KEY")
    
    print("\n🔍 Environment Variables Check:")
    print(f"WEAVIATE_URL: {'✅ Found' if url else '❌ Missing'}")
    print(f"WEAVIATE_API_KEY: {'✅ Found' if api_key else '❌ Missing'}")
    print(f"HUGGINGFACE_API_KEY: {'✅ Found' if hf_key else '❌ Missing'}")
    
    if hf_key:
        print(f"\n🔑 HF Key details:")
        print(f"  - Starts with: {hf_key[:10]}...")
        print(f"  - Length: {len(hf_key)}")
    else:
        print("\n❌ HUGGINGFACE_API_KEY is None or empty!")
        print("\n📝 Check your .env file has:")
        print("HUGGINGFACE_API_KEY=hf_xxxxxxxxxxxx")
        print("(No quotes, no spaces)")
        
        # Try reading .env directly
        print(f"\n📄 Reading .env file directly:")
        try:
            with open(env_path, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if 'HUGGINGFACE' in line:
                        print(f"Found line: {line.strip()[:30]}...")
        except Exception as e:
            print(f"Error reading .env: {e}")
        
        return
    
    # Only continue if we have the key
    print("\n🧪 Testing authentication...")
    
    try:
        # Simple test with the key we have
        headers = {"X-HuggingFace-Api-Key": hf_key}
        print(f"Headers being sent: {headers}")
        
        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=url,
            auth_credentials=AuthApiKey(api_key),
            headers=headers
        )
        
        collection = client.collections.get("Product")
        results = collection.query.hybrid(
            query="tomato",
            alpha=0.5,
            limit=1
        )
        
        print(f"✅ SUCCESS! Found {len(results.objects)} results")
        client.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_auth_methods()