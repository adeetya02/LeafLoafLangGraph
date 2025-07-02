#!/usr/bin/env python3
"""
Test pattern matching locally to debug
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.constants import ORDER_INTENT_PATTERNS, FAST_MODE
from src.agents.supervisor import SupervisorReactAgent
from colorama import init, Fore

init(autoreset=True)

# Test the instant analysis method directly
supervisor = SupervisorReactAgent()

test_queries = [
    "change milk quantity to 3",
    "update banana quantity to 5",
    "make it 10",
    "double the milk quantity",
    "add milk to cart",
    "I need milk"
]

print(f"{Fore.CYAN}Testing instant analysis...")
print(f"FAST_MODE: {FAST_MODE}")
print(f"Patterns loaded: {list(supervisor.patterns.keys())}")
print("=" * 60)

for query in test_queries:
    result = supervisor._instant_analysis(query)
    print(f"\nQuery: '{query}'")
    print(f"  Intent: {result['intent']}")
    print(f"  Confidence: {result['confidence']}")
    
    # Also test pattern directly
    update_pattern = ORDER_INTENT_PATTERNS["update_order"]
    if update_pattern.search(query):
        print(f"  {Fore.GREEN}✓ Pattern matches!")
    else:
        print(f"  {Fore.RED}✗ Pattern doesn't match")