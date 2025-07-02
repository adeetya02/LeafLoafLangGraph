#!/usr/bin/env python3
"""
Test Gemma endpoint directly to measure raw inference time
"""
import time
import asyncio
from google.cloud import aiplatform
from google.oauth2 import service_account
import statistics

# Vertex AI configuration
PROJECT_ID = "leafloafai"
LOCATION = "us-central1"
ENDPOINT_ID = "6438719201535328256"

def test_gemma_endpoint():
    """Test Gemma endpoint performance directly"""
    print("=" * 80)
    print("🔬 TESTING GEMMA 2 9B ENDPOINT DIRECTLY")
    print("=" * 80)
    
    # Initialize Vertex AI
    aiplatform.init(project=PROJECT_ID, location=LOCATION)
    
    # Get endpoint
    endpoint = aiplatform.Endpoint(
        endpoint_name=f"projects/{PROJECT_ID}/locations/{LOCATION}/endpoints/{ENDPOINT_ID}"
    )
    
    # Test queries
    test_prompts = [
        "What is the intent of: 'I need organic milk'",
        "What is the intent of: 'add that to my cart'",
        "What is the intent of: 'breakfast suggestions'",
        "Calculate search alpha for: 'oatly barista'",
        "Calculate search alpha for: 'healthy snacks'"
    ]
    
    # Warm up
    print("\n📊 Warming up endpoint...")
    for _ in range(2):
        try:
            instance = {"prompt": "test", "temperature": 0.1, "max_tokens": 50}
            endpoint.predict(instances=[instance])
        except:
            pass
    
    # Test latencies
    latencies = []
    
    print("\n📊 Testing inference latency:")
    print("-" * 80)
    
    for prompt in test_prompts:
        instance = {
            "prompt": prompt,
            "temperature": 0.1,
            "max_tokens": 100,
            "top_p": 0.9,
            "top_k": 40
        }
        
        # Measure 3 times
        prompt_latencies = []
        for i in range(3):
            start = time.time()
            try:
                response = endpoint.predict(instances=[instance])
                latency = (time.time() - start) * 1000
                prompt_latencies.append(latency)
                
                if i == 0:  # Print first response
                    print(f"\nPrompt: {prompt[:50]}...")
                    print(f"Response: {str(response.predictions[0])[:100]}...")
            except Exception as e:
                print(f"Error: {e}")
                latency = (time.time() - start) * 1000
                prompt_latencies.append(latency)
        
        avg_latency = statistics.mean(prompt_latencies)
        latencies.extend(prompt_latencies)
        print(f"Latencies: {[f'{l:.0f}ms' for l in prompt_latencies]} (avg: {avg_latency:.0f}ms)")
    
    # Summary
    print("\n" + "=" * 80)
    print("📈 ENDPOINT PERFORMANCE SUMMARY")
    print("=" * 80)
    
    if latencies:
        print(f"Average latency: {statistics.mean(latencies):.0f}ms")
        print(f"Min latency: {min(latencies):.0f}ms")
        print(f"Max latency: {max(latencies):.0f}ms")
        print(f"P50 latency: {statistics.median(latencies):.0f}ms")
        if len(latencies) > 10:
            print(f"P95 latency: {statistics.quantiles(latencies, n=20)[18]:.0f}ms")
        
        avg = statistics.mean(latencies)
        if avg < 150:
            print("\n✅ EXCELLENT: Gemma 9B performing as expected!")
        elif avg < 250:
            print("\n⚠️  OK: Slightly slower than expected for 9B")
        else:
            print("\n❌ SLOW: This seems more like 27B performance")
    
    print("\n🔍 Optimization Recommendations:")
    print("1. Ensure endpoint has min-instances > 0 (avoid cold starts)")
    print("2. Use batch predictions for multiple queries")
    print("3. Consider regional deployment closer to Cloud Run")
    print("4. Enable GPU acceleration if not already")
    print("5. Use streaming for partial results")

if __name__ == "__main__":
    # Check if we have credentials
    try:
        test_gemma_endpoint()
    except Exception as e:
        print(f"Error: {e}")
        print("\nTo run this test, you need:")
        print("1. gcloud auth application-default login")
        print("2. Or set GOOGLE_APPLICATION_CREDENTIALS")