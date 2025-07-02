#!/usr/bin/env python3
"""
Test voice-like commands for intent recognition
"""

import asyncio
import httpx
import json
import uuid

async def test_voice_intents():
    """Test various voice-like commands"""
    
    print("="*80)
    print("VOICE INTENT RECOGNITION TEST")
    print("="*80)
    
    base_url = "http://localhost:8080"
    session_id = f"voice-test-{uuid.uuid4()}"
    
    # Test cases simulating voice commands
    test_cases = [
        # First search for products
        ("I need some spinach", "Should recognize as product search"),
        
        # Various ways to add to cart
        ("throw that in my basket", "Should recognize as add_to_order"),
        ("I'll take two of those", "Should recognize as add_to_order with quantity"),
        ("grab me some", "Should recognize as add_to_order"),
        ("yes please", "Should recognize as add_to_order (with context)"),
        ("sounds good, get it", "Should recognize as add_to_order"),
        ("yeah I want that", "Should recognize as add_to_order"),
        ("put it in", "Should recognize as add_to_order"),
        
        # Removal variations
        ("actually, forget the spinach", "Should recognize as remove_from_order"),
        ("nah, take it out", "Should recognize as remove_from_order"),
        ("drop that", "Should recognize as remove_from_order"),
        
        # Updates
        ("make it three instead", "Should recognize as update_order"),
        ("double that", "Should recognize as update_order"),
        
        # Cart viewing
        ("what do I have so far?", "Should recognize as list_order"),
        ("show me my stuff", "Should recognize as list_order"),
        
        # Confirmation
        ("that's all for now", "Should recognize as confirm_order"),
        ("looks good, I'm done", "Should recognize as confirm_order"),
        ("checkout please", "Should recognize as confirm_order"),
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for query, description in test_cases:
            print(f"\n{'='*60}")
            print(f"Query: \"{query}\"")
            print(f"Expected: {description}")
            print("-"*60)
            
            resp = await client.post(
                f"{base_url}/api/v1/search",
                json={"query": query, "session_id": session_id}
            )
            
            if resp.status_code == 200:
                data = resp.json()
                conv = data.get('conversation', {})
                
                print(f"Intent: {conv.get('intent', 'unknown')}")
                print(f"Confidence: {conv.get('confidence', 0.0)}")
                print(f"Success: {data.get('success')}")
                print(f"Message: {data.get('message', '')[:100]}...")
                
                # For order operations, show cart status
                if 'order' in data and data['order']:
                    items = data['order'].get('items', [])
                    if items:
                        print(f"Cart: {len(items)} items")
                        for item in items:
                            print(f"  - {item['name']} x{item['quantity']}")
            else:
                print(f"Error: {resp.status_code}")
    
    print("\n" + "="*80)
    print("Test complete!")

if __name__ == "__main__":
    asyncio.run(test_voice_intents())