#!/usr/bin/env python3
"""
Test context-aware cart operations
Verify that the system understands contextual queries like:
- "add more" (after searching)
- "double it" (after adding to cart)
- "remove the milk" (understands what milk was added)
"""

import asyncio
import httpx
import json
import uuid
import time
from typing import Dict, List

class ContextualCartTester:
    def __init__(self):
        self.base_url = 'https://leafloaf-32905605817.us-central1.run.app'
        self.session_id = str(uuid.uuid4())
        self.results = []
    
    async def make_request(self, query: str, expect_intent: str = None) -> Dict:
        """Make a request and track timing"""
        start = time.time()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f'{self.base_url}/api/v1/search',
                json={
                    'query': query,
                    'session_id': self.session_id
                }
            )
        
        elapsed = (time.time() - start) * 1000
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract intent from execution reasoning
            detected_intent = None
            reasoning = data.get('execution', {}).get('reasoning_steps', [])
            for step in reasoning:
                if 'Intent:' in step:
                    parts = step.split('Intent:')[1].strip().split(',')
                    if parts:
                        detected_intent = parts[0].strip()
            
            result = {
                'query': query,
                'expected_intent': expect_intent,
                'detected_intent': detected_intent,
                'response_time': elapsed,
                'products_found': len(data.get('products', [])),
                'message': data.get('message', ''),
                'success': data.get('success', False),
                'intent_correct': detected_intent == expect_intent if expect_intent else None
            }
            
            self.results.append(result)
            return result
        else:
            result = {
                'query': query,
                'error': f'HTTP {response.status_code}',
                'response_time': elapsed
            }
            self.results.append(result)
            return result
    
    async def run_scenario(self, name: str, steps: List[Dict]):
        """Run a contextual scenario"""
        print(f"\n{'='*80}")
        print(f"SCENARIO: {name}")
        print(f"Session: {self.session_id}")
        print(f"{'='*80}")
        
        for step in steps:
            query = step['query']
            expected = step.get('expect_intent')
            print(f"\n➤ Query: '{query}'")
            if expected:
                print(f"  Expected intent: {expected}")
            
            result = await self.make_request(query, expected)
            
            print(f"  ✓ Response time: {result['response_time']:.0f}ms")
            if 'detected_intent' in result:
                print(f"  ✓ Detected intent: {result['detected_intent']}")
                if result.get('intent_correct') is not None:
                    status = "✅" if result['intent_correct'] else "❌"
                    print(f"  {status} Intent match: {result['intent_correct']}")
            
            if result.get('products_found', 0) > 0:
                print(f"  ✓ Products found: {result['products_found']}")
            
            if result.get('message'):
                print(f"  ✓ Message: {result['message'][:100]}...")
            
            await asyncio.sleep(0.5)  # Small delay between requests

async def main():
    """Run comprehensive contextual cart tests"""
    
    print("="*80)
    print("CONTEXTUAL CART OPERATIONS TEST")
    print("="*80)
    
    # Test 1: Basic context understanding
    tester1 = ContextualCartTester()
    await tester1.run_scenario(
        "Basic Context Understanding",
        [
            {'query': 'I need spinach', 'expect_intent': 'product_search'},
            {'query': 'add 2 bags to cart', 'expect_intent': 'add_to_order'},
            {'query': 'actually make it 3', 'expect_intent': 'update_order'},
            {'query': 'show me tomatoes', 'expect_intent': 'product_search'},
            {'query': 'add those too', 'expect_intent': 'add_to_order'},
            {'query': 'remove the spinach', 'expect_intent': 'remove_from_order'},
            {'query': 'what\'s in my cart?', 'expect_intent': 'list_order'},
        ]
    )
    
    # Test 2: Quantity context
    tester2 = ContextualCartTester()
    await tester2.run_scenario(
        "Quantity Context Understanding",
        [
            {'query': 'show me apples', 'expect_intent': 'product_search'},
            {'query': 'I\'ll take 5', 'expect_intent': 'add_to_order'},
            {'query': 'double that', 'expect_intent': 'update_order'},
            {'query': 'add 3 more', 'expect_intent': 'update_order'},
            {'query': 'actually just 6 total', 'expect_intent': 'update_order'},
        ]
    )
    
    # Test 3: Product reference context
    tester3 = ContextualCartTester()
    await tester3.run_scenario(
        "Product Reference Context",
        [
            {'query': 'find organic milk', 'expect_intent': 'product_search'},
            {'query': 'add the first one', 'expect_intent': 'add_to_order'},
            {'query': 'do you have berries?', 'expect_intent': 'product_search'},
            {'query': 'add strawberries and blueberries', 'expect_intent': 'add_to_order'},
            {'query': 'remove the milk', 'expect_intent': 'remove_from_order'},
            {'query': 'add it back', 'expect_intent': 'add_to_order'},
        ]
    )
    
    # Test 4: Conversational flow
    tester4 = ContextualCartTester()
    await tester4.run_scenario(
        "Natural Conversation Flow",
        [
            {'query': 'I\'m making pasta tonight', 'expect_intent': 'product_search'},
            {'query': 'add pasta to my order', 'expect_intent': 'add_to_order'},
            {'query': 'I\'ll need sauce too', 'expect_intent': 'product_search'},
            {'query': 'add 2 jars', 'expect_intent': 'add_to_order'},
            {'query': 'oh and garlic bread', 'expect_intent': 'product_search'},
            {'query': 'perfect, add one', 'expect_intent': 'add_to_order'},
            {'query': 'that\'s everything', 'expect_intent': 'confirm_order'},
        ]
    )
    
    # Summary
    print("\n" + "="*80)
    print("CONTEXTUAL UNDERSTANDING SUMMARY")
    print("="*80)
    
    all_results = []
    for tester in [tester1, tester2, tester3, tester4]:
        all_results.extend(tester.results)
    
    # Calculate statistics
    intent_results = [r for r in all_results if 'intent_correct' in r and r['intent_correct'] is not None]
    correct_intents = sum(1 for r in intent_results if r['intent_correct'])
    
    print(f"\nIntent Recognition Accuracy: {correct_intents}/{len(intent_results)} ({correct_intents/len(intent_results)*100:.1f}%)")
    
    # Response time analysis
    times = [r['response_time'] for r in all_results if 'response_time' in r]
    if times:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        under_300 = sum(1 for t in times if t < 300)
        
        print(f"\nResponse Time Analysis:")
        print(f"  Average: {avg_time:.0f}ms")
        print(f"  Min: {min_time:.0f}ms")
        print(f"  Max: {max_time:.0f}ms")
        print(f"  Under 300ms: {under_300}/{len(times)} ({under_300/len(times)*100:.1f}%)")
    
    # Intent breakdown
    print("\nIntent Detection by Type:")
    intent_types = {}
    for r in all_results:
        if 'expected_intent' in r and r['expected_intent']:
            intent = r['expected_intent']
            if intent not in intent_types:
                intent_types[intent] = {'total': 0, 'correct': 0}
            intent_types[intent]['total'] += 1
            if r.get('intent_correct', False):
                intent_types[intent]['correct'] += 1
    
    for intent, stats in intent_types.items():
        accuracy = stats['correct'] / stats['total'] * 100 if stats['total'] > 0 else 0
        print(f"  {intent}: {stats['correct']}/{stats['total']} ({accuracy:.0f}%)")

if __name__ == "__main__":
    asyncio.run(main())