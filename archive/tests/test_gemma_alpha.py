#!/usr/bin/env python3
"""
Test Gemma's alpha calculation directly
"""
import requests
import json

BASE_URL = "https://leafloaf-32905605817.us-central1.run.app"

def test_alpha_calculation():
    """Test different queries to see alpha values"""
    
    test_queries = [
        ("oatly barista", "Should return low alpha (0.1-0.3)"),
        ("organic milk", "Should return medium alpha (0.4-0.6)"),
        ("breakfast ideas", "Should return high alpha (0.7-0.9)"),
        ("horizon organic whole milk", "Should return low alpha (brand specific)"),
        ("healthy snack suggestions", "Should return high alpha (exploratory)"),
    ]
    
    print("=" * 80)
    print("TESTING GEMMA ALPHA CALCULATION")
    print("=" * 80)
    
    for query, expected in test_queries:
        print(f"\nQuery: '{query}'")
        print(f"Expected: {expected}")
        
        response = requests.post(
            f"{BASE_URL}/api/v1/search",
            json={"query": query}
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Check metadata
            metadata = data.get("metadata", {})
            search_config = metadata.get("search_config", {})
            alpha = search_config.get("alpha", "NOT FOUND")
            
            # Check execution reasoning
            execution = data.get("execution", {})
            reasoning = execution.get("reasoning_steps", [])
            
            print(f"Alpha returned: {alpha}")
            print(f"Intent: {data.get('conversation', {}).get('intent', 'unknown')}")
            
            # Look for alpha in reasoning
            for step in reasoning:
                if "Alpha:" in str(step):
                    print(f"Reasoning: {step}")
            
            # Check if Gemma is being used
            if "agent_timings" in execution:
                supervisor_time = execution["agent_timings"].get("supervisor", 0)
                print(f"Supervisor time: {supervisor_time}ms")
                
                if supervisor_time > 200:
                    print("✓ Gemma appears to be active (>200ms)")
                else:
                    print("⚠ Gemma might not be active (<200ms)")
        else:
            print(f"Error: {response.status_code}")
    
    print("\n" + "=" * 80)
    print("DEBUGGING TIPS:")
    print("- If alpha is always 0, Gemma might not be returning it properly")
    print("- If supervisor time is <200ms, might be using fallback")
    print("- Check logs: gcloud run logs read --service=leafloaf")

if __name__ == "__main__":
    test_alpha_calculation()