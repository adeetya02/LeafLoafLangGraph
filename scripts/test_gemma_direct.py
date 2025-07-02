#!/usr/bin/env python3
"""
Test Gemma directly to see what it returns
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.integrations.gemma_optimized_client import GemmaOptimizedClient
from colorama import init, Fore

init(autoreset=True)

async def test_gemma():
    client = GemmaOptimizedClient()
    
    test_queries = [
        "change milk quantity to 3",
        "update banana quantity to 5",
        "make it 10",
        "add milk to cart",
        "remove milk from cart",
        "show my cart",
        "checkout",
        "I need milk"
    ]
    
    print(f"{Fore.CYAN}Testing Gemma Intent Recognition")
    print("=" * 80)
    print(f"{'Query':<40} {'Intent':<20} {'Confidence':<10} {'Alpha':<10}")
    print("=" * 80)
    
    for query in test_queries:
        try:
            response = await client.analyze_query(query)
            intent = response.get("intent", "unknown")
            confidence = response.get("confidence", 0)
            alpha = response.get("metadata", {}).get("search_alpha", 0)
            
            print(f"{query:<40} {intent:<20} {confidence:<10.2f} {alpha:<10.2f}")
            
        except Exception as e:
            print(f"{query:<40} {'error':<20} {str(e)}")
        
        await asyncio.sleep(0.5)  # Rate limiting

if __name__ == "__main__":
    asyncio.run(test_gemma())