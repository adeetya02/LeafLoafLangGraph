#!/usr/bin/env python3
"""
Test the enhanced Aloha-based intent recognition
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.yaml')

async def test_aloha_integration():
    """Test enhanced conversational understanding with Aloha approach"""
    
    print("="*80)
    print("ALOHA CONVERSATIONAL INTENT TEST")
    print("="*80)
    
    try:
        from src.integrations.gemma_client_v2 import GemmaClientV2
        
        print("\n1. Initializing Gemma Client...")
        gemma = GemmaClientV2()
        model_info = gemma.get_model_info()
        print(f"Using: {model_info['type']} - {model_info['model']}")
        
        # Enhanced test scenarios for voice interactions
        test_scenarios = [
            {
                "query": "I need some organic spinach",
                "context": None,
                "expected": "product_search",
                "description": "Initial product search"
            },
            {
                "query": "yeah, throw that in my basket",
                "context": {
                    "recent_products": [
                        {"name": "Organic Baby Spinach", "sku": "SP001", "price": 3.99}
                    ],
                    "last_intent": "product_search"
                },
                "expected": "add_to_order",
                "description": "Conversational add after search"
            },
            {
                "query": "grab me 2 of those",
                "context": {
                    "recent_products": [
                        {"name": "Organic Baby Spinach", "sku": "SP001", "price": 3.99}
                    ]
                },
                "expected": "add_to_order",
                "description": "Quantity with reference"
            },
            {
                "query": "sounds good",
                "context": {
                    "recent_products": [
                        {"name": "Horizon Organic Milk", "sku": "ML001", "price": 4.99}
                    ]
                },
                "expected": "add_to_order",
                "description": "Affirmative response with context"
            },
            {
                "query": "what's in my cart?",
                "context": {
                    "current_cart": [{"name": "Spinach", "qty": 2}]
                },
                "expected": "list_order",
                "description": "Cart inquiry"
            },
            {
                "query": "actually, forget the spinach",
                "context": {
                    "current_cart": [{"name": "Spinach", "qty": 2}]
                },
                "expected": "remove_from_order",
                "description": "Conversational removal"
            },
            {
                "query": "that's it, checkout please",
                "context": {
                    "current_cart": [{"name": "Milk", "qty": 1}]
                },
                "expected": "confirm_order",
                "description": "Checkout with politeness"
            }
        ]
        
        print("\n2. Testing Aloha Intent Recognition:")
        print("="*80)
        
        correct_predictions = 0
        total_tests = len(test_scenarios)
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n🧪 Test {i}: {scenario['description']}")
            print(f"Query: \"{scenario['query']}\"")
            
            if scenario['context']:
                context_desc = []
                if scenario['context'].get('recent_products'):
                    context_desc.append(f"Recent: {scenario['context']['recent_products'][0]['name']}")
                if scenario['context'].get('current_cart'):
                    context_desc.append(f"Cart: {len(scenario['context']['current_cart'])} items")
                print(f"Context: {', '.join(context_desc)}")
            
            try:
                # Analyze with Aloha approach
                result = await gemma.analyze_query(scenario['query'], scenario['context'])
                
                # Check prediction
                predicted_intent = result.intent
                expected_intent = scenario['expected']
                is_correct = predicted_intent == expected_intent
                
                if is_correct:
                    correct_predictions += 1
                    status = "✅ CORRECT"
                else:
                    status = "❌ INCORRECT"
                
                print(f"{status} - Intent: {predicted_intent} (expected: {expected_intent})")
                print(f"Confidence: {result.confidence:.2f}")
                
                # Show enhanced details
                if result.metadata:
                    if result.metadata.get('entities'):
                        print(f"Entities: {result.metadata['entities']}")
                    if result.metadata.get('quantities'):
                        print(f"Quantities: {result.metadata['quantities']}")
                    if result.metadata.get('reasoning'):
                        print(f"Reasoning: {result.metadata['reasoning']}")
                
            except Exception as e:
                print(f"❌ ERROR: {str(e)}")
        
        # Summary
        accuracy = (correct_predictions / total_tests) * 100
        print(f"\n{'='*80}")
        print(f"ALOHA INTEGRATION RESULTS")
        print(f"{'='*80}")
        print(f"Accuracy: {correct_predictions}/{total_tests} ({accuracy:.1f}%)")
        
        if accuracy >= 80:
            print("🎉 EXCELLENT: Ready for voice interactions!")
        elif accuracy >= 60:
            print("👍 GOOD: Suitable for most use cases")
        else:
            print("⚠️ NEEDS IMPROVEMENT: Consider fine-tuning")
        
        # Test alpha calculation
        print(f"\n3. Testing Dynamic Alpha Calculation:")
        print("-" * 60)
        
        alpha_tests = [
            ("oatly barista milk", "Brand-specific (low alpha)"),
            ("organic breakfast ideas", "Exploratory (high alpha)"),
            ("spinach", "Simple product (medium alpha)")
        ]
        
        for query, description in alpha_tests:
            try:
                alpha = await gemma.calculate_dynamic_alpha(query)
                print(f"'{query}' → α={alpha:.2f} ({description})")
            except Exception as e:
                print(f"'{query}' → Error: {e}")
        
    except Exception as e:
        print(f"\n❌ INTEGRATION ERROR: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Ensure Gemma endpoint is deployed and running")
        print("2. Check GCP authentication: gcloud auth list")
        print("3. Verify .env.yaml has correct project settings")

if __name__ == "__main__":
    asyncio.run(test_aloha_integration())