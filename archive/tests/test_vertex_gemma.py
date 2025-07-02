#!/usr/bin/env python3
"""
Test Vertex AI Gemma 2 9B integration
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.yaml')

# Set project ID and location
os.environ['GCP_PROJECT_ID'] = os.getenv('GCP_PROJECT_ID', 'leafloafai')
os.environ['GCP_LOCATION'] = os.getenv('GCP_LOCATION', 'us-central1')

async def test_vertex_gemma():
    """Test Gemma 2 9B on Vertex AI"""
    
    print("="*80)
    print("VERTEX AI GEMMA 2 9B TEST")
    print("="*80)
    
    print(f"\nProject ID: {os.getenv('GCP_PROJECT_ID')}")
    print(f"Location: {os.getenv('GCP_LOCATION')}")
    
    try:
        # Import after setting env vars
        from src.integrations.gemma_client_v2 import GemmaClientV2
        
        print("\n1. Initializing Gemma Client...")
        gemma = GemmaClientV2()
        
        # Test different queries
        test_queries = [
            ("I need some organic spinach", "Product search query"),
            ("throw that in my basket", "Conversational add to cart"),
            ("yeah grab me 3 of those", "Quantity with conversational language"),
            ("what's in my cart?", "Show cart query"),
            ("that's all, checkout please", "Confirm order")
        ]
        
        print("\n2. Testing Intent Recognition:")
        print("-"*60)
        
        for query, description in test_queries:
            print(f"\nTest: {description}")
            print(f"Query: \"{query}\"")
            
            try:
                # Test with context
                context = {
                    "recent_products": [
                        {"name": "Organic Spinach", "sku": "SP001", "price": 3.99},
                        {"name": "Baby Spinach", "sku": "SP002", "price": 4.99}
                    ]
                }
                
                # Analyze query
                result = await gemma.analyze_query(query, context)
                
                print(f"Intent: {result.intent}")
                print(f"Confidence: {result.confidence}")
                if result.metadata:
                    print(f"Entities: {result.metadata.get('entities', [])}")
                    print(f"Alpha: {result.metadata.get('search_alpha', 'N/A')}")
                
            except Exception as e:
                print(f"Error: {str(e)}")
        
        print("\n3. Testing Alpha Calculation:")
        print("-"*60)
        
        alpha_tests = [
            "oatly barista milk",  # Brand specific
            "organic vegetables",   # Category
            "breakfast ideas",      # Exploratory
            "spinach"              # Simple product
        ]
        
        for query in alpha_tests:
            try:
                alpha = await gemma.calculate_dynamic_alpha(query)
                print(f"Query: \"{query}\" → Alpha: {alpha}")
            except Exception as e:
                print(f"Query: \"{query}\" → Error: {str(e)}")
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Make sure you have authenticated with GCP:")
        print("   gcloud auth application-default login")
        print("2. Enable Vertex AI API:")
        print("   gcloud services enable aiplatform.googleapis.com")
        print("3. Check if Gemma 2 is available in your region:")
        print("   gcloud ai models list --region=us-central1 | grep gemma")

if __name__ == "__main__":
    asyncio.run(test_vertex_gemma())