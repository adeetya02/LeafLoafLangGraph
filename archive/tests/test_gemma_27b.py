#!/usr/bin/env python3
"""
Test the deployed Gemma 2 27B model
"""

import asyncio
from google.cloud import aiplatform

PROJECT_ID = "leafloafai"
LOCATION = "us-central1"
GEMMA_27B_ENDPOINT_ID = "4519059860368654336"

async def test_gemma_27b():
    """Test the deployed Gemma 2 27B model"""
    
    print("="*80)
    print("🧪 TESTING GEMMA 2 27B DEPLOYMENT")
    print("="*80)
    
    # Initialize AI Platform
    aiplatform.init(project=PROJECT_ID, location=LOCATION)
    
    # Get the 27B endpoint
    endpoint = aiplatform.Endpoint(f"projects/{PROJECT_ID}/locations/{LOCATION}/endpoints/{GEMMA_27B_ENDPOINT_ID}")
    
    print(f"Testing endpoint: {endpoint.display_name}")
    print(f"Model: Gemma 2 27B (Large)")
    print(f"💰 Estimated cost: ~$3-4/hour")
    
    # Test scenarios for our grocery voice system
    test_scenarios = [
        {
            "name": "Basic Intent Recognition",
            "prompt": """You are a grocery shopping assistant. Analyze this query and return JSON:

Query: "I need some organic spinach"

Return JSON with intent, entities, and confidence:""",
            "expected": "product_search intent"
        },
        {
            "name": "Voice Add to Cart",
            "prompt": """You are a grocery shopping assistant analyzing voice commands.

Query: "throw that in my basket"
Context: Recent search showed "Organic Baby Spinach"

Analyze the intent and return JSON:
{"intent": "add_to_order", "entities": ["spinach"], "confidence": 0.9}""",
            "expected": "add_to_order intent"
        },
        {
            "name": "Conversational Quantity",
            "prompt": """Grocery voice assistant - analyze this:

Query: "grab me 2 of those"
Context: User just searched for milk

Return JSON with intent and quantity:""",
            "expected": "quantity extraction"
        },
        {
            "name": "Search Alpha Calculation",
            "prompt": """Calculate search alpha (0.1=keyword, 0.8=semantic) for grocery search:

Query: "oatly barista milk"
This is brand-specific, should use keyword search.

Return: {"search_alpha": 0.1, "reasoning": "brand name query"}""",
            "expected": "low alpha for brand"
        }
    ]
    
    print(f"\n🧪 Running {len(test_scenarios)} test scenarios:")
    print("-" * 80)
    
    successful_tests = 0
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        print(f"Expected: {scenario['expected']}")
        
        try:
            # Make prediction
            response = endpoint.predict(
                instances=[{
                    "prompt": scenario["prompt"],
                    "temperature": 0.1,
                    "max_tokens": 200
                }]
            )
            
            if response.predictions:
                result = str(response.predictions[0])
                print(f"✅ Response: {result[:300]}...")
                
                # Check if response looks reasonable
                if any(keyword in result.lower() for keyword in ["intent", "json", "confidence", "alpha"]):
                    successful_tests += 1
                    print(f"   ✅ Test PASSED - Contains expected keywords")
                else:
                    print(f"   ⚠️  Test PARTIAL - Response received but format unclear")
            else:
                print(f"❌ No predictions returned")
                
        except Exception as e:
            error_str = str(e)
            if "warming up" in error_str.lower():
                print(f"🔥 Model still warming up: {error_str}")
            else:
                print(f"❌ Test failed: {error_str[:200]}")
    
    # Summary
    print(f"\n{'='*80}")
    print(f"TEST RESULTS")
    print(f"{'='*80}")
    print(f"Successful tests: {successful_tests}/{len(test_scenarios)}")
    
    if successful_tests >= 3:
        print(f"🎉 EXCELLENT! Gemma 2 27B is working great")
        print(f"✅ Ready for voice interactions")
        
        # Update deployment info for our system
        deployment_info = {
            "project_id": PROJECT_ID,
            "location": LOCATION,
            "endpoint_id": GEMMA_27B_ENDPOINT_ID,
            "endpoint_resource_name": f"projects/{PROJECT_ID}/locations/{LOCATION}/endpoints/{GEMMA_27B_ENDPOINT_ID}",
            "endpoint_display_name": endpoint.display_name,
            "model_size": "27B",
            "created_at": "2025-06-24T22:40:00",
            "fine_tuned": False
        }
        
        import json
        with open("gemma_deployment_info.json", "w") as f:
            json.dump(deployment_info, f, indent=2)
        
        print(f"✅ Updated deployment info for integration")
        
        # Test our actual integration
        print(f"\n🔗 Testing full integration...")
        try:
            from src.integrations.gemma_client_v2 import GemmaClientV2
            
            gemma_client = GemmaClientV2()
            model_info = gemma_client.get_model_info()
            print(f"Integration model: {model_info}")
            
            # Quick integration test
            result = await gemma_client.analyze_query("I'll take that spinach", {
                "recent_products": [{"name": "Organic Spinach", "price": 3.99}]
            })
            
            print(f"Integration test: {result.intent} (confidence: {result.confidence})")
            
        except Exception as e:
            print(f"⚠️  Integration test error: {e}")
        
    elif successful_tests > 0:
        print(f"👍 GOOD - Gemma is responding but may need prompt tuning")
    else:
        print(f"❌ ISSUES - Model may still be warming up")
    
    print(f"\n💰 COST WARNING: 27B model is expensive (~$3-4/hour)")
    print(f"🛑 STOP when done testing:")
    print(f"   python3 manage_vertex_endpoints.py stop {endpoint.display_name}")

if __name__ == "__main__":
    asyncio.run(test_gemma_27b())