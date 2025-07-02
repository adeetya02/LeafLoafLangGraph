#!/usr/bin/env python3
"""
Test the updated update_order pattern
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.constants import ORDER_INTENT_PATTERNS
from colorama import init, Fore

init(autoreset=True)

# Test cases for update_order pattern
test_cases = [
    # Should match - new pattern
    ("change milk quantity to 3", True),
    ("update banana quantity to 5", True),
    ("modify apple amount to 10", True),
    ("change oatly quantity into 2", True),
    
    # Should match - existing patterns
    ("change the quantity", True),
    ("update my cart", True),
    ("modify that amount", True),
    ("make it 5", True),
    ("double the quantity", True),
    ("triple that", True),
    
    # Should NOT match
    ("I need milk", False),
    ("add milk to cart", False),
    ("remove milk", False),
    ("show my cart", False),
]

print(f"{Fore.CYAN}Testing update_order pattern...")
print("=" * 60)

update_pattern = ORDER_INTENT_PATTERNS["update_order"]
all_passed = True

for query, should_match in test_cases:
    match = update_pattern.search(query)
    matched = match is not None
    
    if matched == should_match:
        status = f"{Fore.GREEN}✓ PASS"
    else:
        status = f"{Fore.RED}✗ FAIL"
        all_passed = False
    
    print(f"{status} | '{query}' | Expected: {should_match} | Got: {matched}")

print("=" * 60)
if all_passed:
    print(f"{Fore.GREEN}All tests passed!")
else:
    print(f"{Fore.RED}Some tests failed!")

# Also test against all patterns to ensure no false positives
print(f"\n{Fore.CYAN}Testing for false positives with other patterns...")
print("=" * 60)

test_query = "change milk quantity to 3"
print(f"Query: '{test_query}'")
for pattern_name, pattern in ORDER_INTENT_PATTERNS.items():
    if pattern.search(test_query):
        print(f"  {Fore.YELLOW}Matches: {pattern_name}")