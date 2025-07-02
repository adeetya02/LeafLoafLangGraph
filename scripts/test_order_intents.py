#!/usr/bin/env python3
"""
Test all order-related intents
"""

import asyncio
import aiohttp
import json
import ssl
import certifi
import time
from colorama import init, Fore

init(autoreset=True)

GCP_URL = "https://leafloaf-32905605817.us-central1.run.app"

async def test_order_intents():
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    
    session_id = f"test_intents_{int(time.time())}"
    
    # Test scenarios
    test_cases = [
        # Update scenarios
        ("change milk quantity to 3", "update_order"),
        ("update banana quantity to 5", "update_order"),
        ("modify apple amount to 10", "update_order"),
        ("make it 10", "update_order"),
        ("double the milk quantity", "update_order"),
        
        # Add scenarios
        ("add milk to cart", "add_to_order"),
        ("put 2 bananas in my basket", "add_to_order"),
        ("I'll take 3 apples", "add_to_order"),
        
        # Remove scenarios
        ("remove milk from cart", "remove_from_order"),
        ("delete the bananas", "remove_from_order"),
        ("take out apples", "remove_from_order"),
        
        # List scenarios
        ("show my cart", "list_order"),
        ("what's in my basket", "list_order"),
        ("view my order", "list_order"),
        
        # Confirm scenarios
        ("confirm order", "confirm_order"),
        ("checkout please", "confirm_order"),
        ("that's it, I'm done", "confirm_order"),
        
        # Search scenarios (control)
        ("I need milk", "product_search"),
        ("organic bananas", "product_search"),
        ("healthy breakfast ideas", "product_search"),
    ]
    
    async with aiohttp.ClientSession(connector=connector) as session:
        print(f"{Fore.CYAN}Testing Order Intent Recognition")
        print(f"Session ID: {session_id}")
        print("=" * 80)
        print(f"{'Query':<40} {'Expected':<15} {'Actual':<15} {'Status':<10}")
        print("=" * 80)
        
        passed = 0
        failed = 0
        
        for query, expected_intent in test_cases:
            payload = {
                "query": query,
                "session_id": session_id
            }
            
            try:
                async with session.post(
                    f"{GCP_URL}/api/v1/search",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    data = await response.json()
                    
                    # Get actual intent from execution
                    execution = data.get('execution', {})
                    agents_run = execution.get('agents_run', [])
                    reasoning = execution.get('reasoning_steps', [])
                    
                    # Determine actual intent
                    actual_intent = "unknown"
                    if 'order_agent' in agents_run:
                        # Check reasoning for specific intent
                        for step in reasoning:
                            if "Intent:" in step:
                                if "add_to_order" in step:
                                    actual_intent = "add_to_order"
                                elif "update_order" in step:
                                    actual_intent = "update_order"
                                elif "remove_from_order" in step:
                                    actual_intent = "remove_from_order"
                                elif "list_order" in step:
                                    actual_intent = "list_order"
                                elif "confirm_order" in step:
                                    actual_intent = "confirm_order"
                                else:
                                    actual_intent = "order_agent"
                                break
                        if actual_intent == "unknown":
                            actual_intent = "order_agent"
                    elif 'product_search' in agents_run:
                        actual_intent = "product_search"
                    else:
                        # Check conversation metadata
                        conv = data.get('conversation', {})
                        actual_intent = conv.get('intent', 'unknown')
                    
                    # Check if correct
                    if expected_intent in ["add_to_order", "update_order", "remove_from_order", "list_order", "confirm_order"]:
                        # All order intents should route to order_agent
                        is_correct = actual_intent in ["order_agent", expected_intent]
                    else:
                        is_correct = actual_intent == expected_intent
                    
                    status = f"{Fore.GREEN}✓ PASS" if is_correct else f"{Fore.RED}✗ FAIL"
                    
                    print(f"{query:<40} {expected_intent:<15} {actual_intent:<15} {status:<10}")
                    
                    if is_correct:
                        passed += 1
                    else:
                        failed += 1
                        
            except Exception as e:
                print(f"{query:<40} {expected_intent:<15} {'error':<15} {Fore.RED}✗ ERROR")
                failed += 1
            
            await asyncio.sleep(0.5)  # Rate limiting
        
        print("=" * 80)
        print(f"\nResults: {Fore.GREEN}{passed} passed, {Fore.RED}{failed} failed")
        print(f"Success rate: {(passed/(passed+failed)*100):.1f}%")

if __name__ == "__main__":
    asyncio.run(test_order_intents())