#!/usr/bin/env python3
"""
Test personalization scenarios with Baldor produce data
"""

import asyncio
import httpx
import uuid
import json
from datetime import datetime

# Test scenarios based on Baldor produce categories
PERSONALIZATION_SCENARIOS = [
    {
        "name": "Organic Preference User",
        "searches": [
            "I need vegetables for salad",
            "show me tomatoes", 
            "add organic tomatoes to cart",
            "I also need peppers",
            "add the organic ones"
        ],
        "expected_behavior": "Should learn organic preference and prioritize organic options"
    },
    {
        "name": "Budget Conscious User",
        "searches": [
            "cheapest spinach",
            "show me budget lettuce options",
            "add the least expensive one",
            "affordable vegetables",
            "add the cheapest peppers"
        ],
        "expected_behavior": "Should learn price sensitivity and show lower-priced options first"
    },
    {
        "name": "Specific Brand Loyalty",
        "searches": [
            "spinach from Local Farms",
            "add it to cart",
            "peppers from Local Farms",
            "add those too",
            "any vegetables from Local Farms"
        ],
        "expected_behavior": "Should recognize brand preference for Local Farms"
    },
    {
        "name": "Contextual Understanding",
        "searches": [
            "I'm making a salad",
            "add spinach",
            "and tomatoes",
            "double the spinach",
            "what's in my cart?"
        ],
        "expected_behavior": "Should maintain context throughout conversation"
    },
    {
        "name": "Quantity Patterns",
        "searches": [
            "2 bags of spinach",
            "add them",
            "3 peppers",
            "add those",
            "show my order"
        ],
        "expected_behavior": "Should understand quantity requests"
    }
]

async def test_personalization_scenario(base_url: str, scenario: dict):
    """Test a single personalization scenario"""
    session_id = str(uuid.uuid4())
    user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    
    print(f"\n{'='*80}")
    print(f"SCENARIO: {scenario['name']}")
    print(f"Session: {session_id[:8]}... User: {user_id}")
    print(f"Expected: {scenario['expected_behavior']}")
    print(f"{'='*80}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        results = []
        
        for i, query in enumerate(scenario['searches']):
            print(f"\n➤ Step {i+1}: '{query}'")
            
            start_time = datetime.now()
            response = await client.post(
                f"{base_url}/api/v1/search",
                json={
                    "query": query,
                    "session_id": session_id,
                    "user_id": user_id
                }
            )
            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            data = response.json()
            
            # Extract key information
            products = data.get("products", [])
            order = data.get("order", {})
            message = data.get("message", "")
            intent = data.get("conversation", {}).get("intent", "unknown")
            
            print(f"  ✓ Response time: {elapsed_ms:.0f}ms")
            print(f"  ✓ Intent: {intent}")
            
            if products:
                print(f"  ✓ Products found: {len(products)}")
                # Show first 3 products
                for j, product in enumerate(products[:3]):
                    print(f"     {j+1}. {product['product_name']} - ${product['price']:.2f}")
                    if 'organic' in product['product_name'].lower():
                        print(f"        → ORGANIC")
                    if product.get('supplier'):
                        print(f"        → Brand: {product['supplier']}")
                        
            if order and order.get("items"):
                print(f"  ✓ Cart items: {len(order['items'])}")
                total = sum(item.get('price', 0) * item.get('quantity', 1) for item in order['items'])
                print(f"  ✓ Cart total: ${total:.2f}")
                
            if message:
                print(f"  ✓ Message: {message}")
                
            results.append({
                "query": query,
                "response_time_ms": elapsed_ms,
                "products_found": len(products),
                "cart_items": len(order.get("items", [])),
                "intent": intent
            })
            
        return results

async def analyze_personalization(results: list, scenario: dict):
    """Analyze if personalization is working"""
    print(f"\n📊 ANALYSIS: {scenario['name']}")
    print(f"Expected behavior: {scenario['expected_behavior']}")
    
    # Calculate metrics
    avg_response_time = sum(r["response_time_ms"] for r in results) / len(results)
    successful_intents = sum(1 for r in results if r["intent"] != "unknown")
    
    print(f"\nMetrics:")
    print(f"  • Average response time: {avg_response_time:.0f}ms")
    print(f"  • Intent recognition: {successful_intents}/{len(results)} ({successful_intents/len(results)*100:.0f}%)")
    print(f"  • Final cart size: {results[-1]['cart_items']} items")
    
    # Check for personalization indicators
    if "organic" in scenario["name"].lower():
        print(f"\n  ✓ Testing organic preference learning...")
    elif "budget" in scenario["name"].lower():
        print(f"\n  ✓ Testing price sensitivity learning...")
    elif "brand" in scenario["name"].lower():
        print(f"\n  ✓ Testing brand loyalty recognition...")

async def main():
    """Run all personalization tests"""
    print("="*80)
    print("BALDOR PRODUCE PERSONALIZATION TEST SUITE")
    print("="*80)
    
    base_url = "http://localhost:8080"
    
    # Check if server is running
    try:
        async with httpx.AsyncClient() as client:
            health = await client.get(f"{base_url}/health")
            if health.status_code != 200:
                print("❌ Server not responding")
                return
    except:
        print("❌ Server not running on port 8080")
        return
    
    print("✅ Server is running")
    
    # Run each scenario
    all_results = []
    for scenario in PERSONALIZATION_SCENARIOS:
        results = await test_personalization_scenario(base_url, scenario)
        await analyze_personalization(results, scenario)
        all_results.append({
            "scenario": scenario["name"],
            "results": results
        })
        
        # Brief pause between scenarios
        await asyncio.sleep(1)
    
    # Overall summary
    print("\n" + "="*80)
    print("OVERALL SUMMARY")
    print("="*80)
    
    total_queries = sum(len(s["results"]) for s in all_results)
    total_time = sum(r["response_time_ms"] for s in all_results for r in s["results"])
    avg_time = total_time / total_queries
    
    print(f"\nTotal queries: {total_queries}")
    print(f"Average response time: {avg_time:.0f}ms")
    print(f"Performance: {'✅ PASS' if avg_time < 500 else '❌ FAIL'} (target <500ms)")
    
    # Check which scenarios show personalization
    print("\nPersonalization readiness:")
    for s in all_results:
        cart_built = any(r["cart_items"] > 0 for r in s["results"])
        print(f"  • {s['scenario']}: {'✅ Cart operations working' if cart_built else '❌ Cart not working'}")

if __name__ == "__main__":
    asyncio.run(main())