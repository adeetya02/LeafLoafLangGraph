#!/usr/bin/env python3
"""
Test alpha-driven search with current Weaviate configuration
"""

from src.integrations.weaviate_client_simple import get_simple_client
import time

print("=" * 80)
print("🧪 TESTING ALPHA-DRIVEN SEARCH")
print("=" * 80)

# Get the simple client
client = get_simple_client()

# Test queries with different alpha values
test_cases = [
    # (query, alpha, description)
    ("BALDOR PE64A", 0.2, "Exact SKU search - keyword focused"),
    ("organic tomatoes", 0.5, "Balanced search - category/attribute"),
    ("healthy dinner vegetables", 0.8, "Semantic search - conceptual"),
    ("red peppers", 0.0, "Pure keyword search"),
    ("fresh produce", 0.7, "Semantic-leaning search"),
]

print("\n📊 Running search tests...")
print("-" * 80)

for query, alpha, description in test_cases:
    print(f"\n🔍 Test: {description}")
    print(f"   Query: '{query}'")
    print(f"   Alpha: {alpha}")
    
    # Execute search
    start = time.time()
    result = client.search(query=query, alpha=alpha, limit=5)
    elapsed = (time.time() - start) * 1000
    
    print(f"   Time: {elapsed:.0f}ms")
    
    if result.get("error"):
        print(f"   ❌ Error: {result['error']}")
    else:
        products = result.get("products", [])
        print(f"   Found: {len(products)} products")
        
        # Show top 3 results
        for i, product in enumerate(products[:3]):
            name = product.get("product_name", "Unknown")
            price = product.get("price", 0)
            supplier = product.get("supplier", "Unknown")
            print(f"   {i+1}. {name} - ${price:.2f} ({supplier})")

print("\n" + "=" * 80)
print("🏁 Test complete!")
print("\n📝 Notes:")
print("- Currently using BM25-only search (no vectorizer configured)")
print("- Alpha parameter is recorded but not affecting results")
print("- To enable hybrid search, configure a vectorizer using:")
print("  - setup_gemini_vectorizer.py (Google AI)")
print("  - setup_cohere_vectorizer.py (Cohere)")
print("  - setup_openai_vectorizer.py (OpenAI)")
print("=" * 80)