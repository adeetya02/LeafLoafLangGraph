"""
Quick test to verify GCP deployment with Baldor data
"""

import requests
import json

# GCP deployment URL
BASE_URL = "https://leafloafai-32905605817.us-east1.run.app"

def test_search(query):
    """Test a search query"""
    payload = {
        "query": query,
        "config": {},
        "kwargs": {}
    }
    
    print(f"\n🔍 Testing: '{query}'")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/search",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        data = response.json()
        
        # Print full response for debugging
        print(f"   Response: {json.dumps(data, indent=2)[:500]}...")
        
        if data.get("success"):
            products = data.get("products", [])
            print(f"✅ Found {len(products)} products")
            
            # Show first product if any
            if products:
                first = products[0]
                print(f"   First product: {first.get('product_name', 'Unknown')}")
                print(f"   Price: ${first.get('price', 0)}")
                print(f"   Description: {first.get('product_description', 'N/A')[:100]}...")
        else:
            print(f"❌ Error: {data.get('error', 'Unknown error')}")
            
        # Show metadata
        metadata = data.get("metadata", {})
        if metadata:
            print(f"   Search config: {metadata.get('search_config', {})}")
            
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")

# Test various query formats
print("🧪 TESTING GCP DEPLOYMENT WITH BALDOR DATA")
print("=" * 50)

# Try different query patterns
test_queries = [
    # Generic produce terms
    "peppers",
    "pepper",
    "tri color",
    "tri-color",
    
    # Exact Baldor format
    "TRI-COLOR BELL PEPPERS",
    "BELL PEPPERS",
    
    # Partial matches
    "8 X 3CT",
    "CTN",
    
    # Other produce
    "strawberry",
    "STRAWBERRIES",
    "organic",
    "ORGANIC",
    
    # Very generic
    "vegetable",
    "produce",
    "fresh"
]

for query in test_queries:
    test_search(query)

# Check health endpoint
print("\n📊 System Health:")
health = requests.get(f"{BASE_URL}/health").json()
print(json.dumps(health, indent=2))