#!/usr/bin/env python3
"""
Direct Weaviate test to check data availability
"""

import os
import sys
import weaviate
from weaviate.auth import AuthApiKey
from colorama import init, Fore

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import settings

init(autoreset=True)

def test_weaviate():
    print(f"{Fore.CYAN}Testing Weaviate Connection...")
    
    # Get credentials from settings
    weaviate_url = settings.weaviate_url
    weaviate_key = settings.weaviate_api_key
    
    if not weaviate_url or not weaviate_key:
        print(f"{Fore.RED}Missing WEAVIATE_URL or WEAVIATE_API_KEY in settings")
        return
        
    print(f"URL: {weaviate_url}")
    print(f"Key: {'*' * 10}...")
    
    try:
        # Remove https:// prefix for connect_to_weaviate_cloud
        cluster_url = weaviate_url.replace("https://", "").replace("http://", "")
        
        # Connect to Weaviate
        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=cluster_url,
            auth_credentials=AuthApiKey(weaviate_key)
        )
        
        print(f"{Fore.GREEN}✅ Connected to Weaviate")
        
        # Check if ready
        is_ready = client.is_ready()
        print(f"{'✅' if is_ready else '❌'} Weaviate Ready: {is_ready}")
        
        # List collections (v4 API)
        collections = client.collections.list_all()
        print(f"\n{Fore.YELLOW}Collections in schema:")
        for collection_name in collections:
            print(f"- {collection_name}")
            
        # Check Product class
        product_collection = client.collections.get("Product")
        
        # Get collection config to see properties
        config = product_collection.config.get()
        print(f"\n{Fore.YELLOW}Product properties:")
        for prop in config.properties:
            print(f"- {prop.name} ({prop.data_type})")
        
        # Count products
        agg_result = product_collection.aggregate.over_all(
            total_count=True
        )
        
        count = agg_result.total_count if agg_result else 0
        print(f"\n{Fore.CYAN}Product Count: {count}")
        
        if count == 0:
            print(f"{Fore.RED}❌ No products in database!")
            print("\nChecking if there's a data loading issue...")
            
            # Try to get any object
            try:
                result = product_collection.query.fetch_objects(limit=1)
                if result and result.objects:
                    print(f"Actually found {len(result.objects)} products")
                else:
                    print("Confirmed: No products in collection")
            except Exception as e:
                print(f"Error fetching: {e}")
        else:
            print(f"{Fore.GREEN}✅ Products available")
            
            # Get sample products - use actual properties
            print(f"\n{Fore.YELLOW}Sample products:")
            result = product_collection.query.fetch_objects(
                limit=5
            )
            
            if result and result.objects:
                for obj in result.objects:
                    props = obj.properties
                    # Print all available properties
                    print(f"- Product: {props}")
                    
            # Test BM25 search directly
            print(f"\n{Fore.YELLOW}Testing BM25 search for 'milk':")
            search_result = product_collection.query.bm25(
                query="milk",
                limit=5
            )
            
            if search_result and search_result.objects:
                print(f"Found {len(search_result.objects)} results:")
                for obj in search_result.objects:
                    props = obj.properties
                    print(f"- {props}")
            else:
                print("No search results")
                
                # Test different BM25 queries
                print(f"\n{Fore.YELLOW}Testing various BM25 queries:")
                
                test_queries = ["milk", "pepper", "Laxmi", "organic", "BALDOR"]
                for test_query in test_queries:
                    print(f"\n  Testing '{test_query}':")
                    bm25_result = product_collection.query.bm25(
                        query=test_query,
                        limit=3
                    )
                
                    if bm25_result and bm25_result.objects:
                        print(f"    Found {len(bm25_result.objects)} results")
                        for obj in bm25_result.objects[:2]:
                            print(f"    - {obj.properties.get('name', 'Unknown')}")
                    else:
                        print(f"    No results")
                    
        client.close()
        
    except Exception as e:
        print(f"{Fore.RED}Error: {e}")
        print(f"Error type: {type(e).__name__}")

if __name__ == "__main__":
    test_weaviate()