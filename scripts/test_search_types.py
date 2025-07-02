#!/usr/bin/env python3
"""
Test different search types to see if hybrid/vector search is working
"""

import os
import sys
import weaviate
from weaviate.auth import AuthApiKey
from colorama import init, Fore

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config.settings import settings

init(autoreset=True)

def test_search_types():
    print(f"{Fore.CYAN}Testing Weaviate Search Types")
    print(f"weaviate_bm25_only: {settings.weaviate_bm25_only}")
    
    # Connect to Weaviate
    cluster_url = settings.weaviate_url.replace("https://", "").replace("http://", "")
    
    # Add HuggingFace key
    headers = {}
    if settings.huggingface_api_key:
        headers["X-HuggingFace-Api-Key"] = settings.huggingface_api_key
        print(f"HuggingFace key: {'*' * 10}...")
    
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=cluster_url,
        auth_credentials=AuthApiKey(settings.weaviate_api_key),
        headers=headers
    )
    
    print(f"✅ Connected to Weaviate")
    
    collection = client.collections.get("Product")
    
    # Test 1: BM25 (should always work)
    print(f"\n{Fore.YELLOW}Test 1: BM25 Search")
    try:
        result = collection.query.bm25(
            query="milk",
            limit=2
        )
        print(f"✅ BM25 works - found {len(result.objects)} products")
    except Exception as e:
        print(f"❌ BM25 failed: {e}")
    
    # Test 2: Hybrid Search
    print(f"\n{Fore.YELLOW}Test 2: Hybrid Search (alpha=0.5)")
    try:
        result = collection.query.hybrid(
            query="milk",
            alpha=0.5,
            limit=2
        )
        print(f"✅ Hybrid search works - found {len(result.objects)} products")
    except Exception as e:
        print(f"❌ Hybrid search failed: {e}")
        print(f"   Error type: {type(e).__name__}")
    
    # Test 3: Pure Vector Search
    print(f"\n{Fore.YELLOW}Test 3: Pure Vector Search")
    try:
        result = collection.query.near_text(
            query="healthy breakfast",
            limit=2
        )
        print(f"✅ Vector search works - found {len(result.objects)} products")
    except Exception as e:
        print(f"❌ Vector search failed: {e}")
        print(f"   Error type: {type(e).__name__}")
    
    # Test 4: Check actual alpha routing
    print(f"\n{Fore.YELLOW}Test 4: Alpha Routing Simulation")
    test_cases = [
        ("milk", 0.5, "hybrid"),
        ("Oatly barista", 0.1, "bm25"),
        ("healthy ideas", 0.8, "vector")
    ]
    
    for query, alpha, expected_type in test_cases:
        print(f"\nQuery: '{query}', Alpha: {alpha}")
        print(f"Expected: {expected_type} search")
        
        try:
            if alpha < 0.3 or settings.weaviate_bm25_only:
                print("  → Using BM25")
                result = collection.query.bm25(query=query, limit=2)
            elif alpha > 0.7:
                print("  → Using Vector")
                result = collection.query.near_text(query=query, limit=2)
            else:
                print("  → Using Hybrid")
                result = collection.query.hybrid(query=query, alpha=alpha, limit=2)
                
            print(f"  ✅ Found {len(result.objects)} products")
            
        except Exception as e:
            print(f"  ❌ Failed: {str(e)[:100]}...")
    
    client.close()
    print(f"\n{Fore.GREEN}Test complete!")

if __name__ == "__main__":
    test_search_types()