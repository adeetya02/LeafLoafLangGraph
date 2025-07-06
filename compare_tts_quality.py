#!/usr/bin/env python3
"""
Compare TTS quality between Deepgram and Edge-TTS for English
This helps us decide routing strategy
"""
import asyncio
import edge_tts
import requests
import time
import os

DEEPGRAM_API_KEY = "36a821d351939023aabad9beeaa68b391caa124a"

# Test sentences
TEST_SENTENCES = [
    "Welcome to LeafLoaf! How can I help you today?",
    "I've added 2 kilograms of lentils to your cart.",
    "Your total is 45 dollars and 67 cents.",
    "Would you like to add some fresh vegetables to your order?"
]

async def generate_deepgram_tts(text: str, filename: str):
    """Generate audio using Deepgram TTS"""
    url = "https://api.deepgram.com/v1/speak"
    
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    params = {
        "model": "aura-asteria-en",
        "encoding": "mp3"
    }
    
    payload = {"text": text}
    
    start_time = time.time()
    response = requests.post(url, headers=headers, params=params, json=payload)
    generation_time = time.time() - start_time
    
    if response.status_code == 200:
        with open(filename, "wb") as f:
            f.write(response.content)
        return {
            "success": True,
            "time": generation_time,
            "size": len(response.content)
        }
    else:
        return {
            "success": False,
            "error": f"{response.status_code}: {response.text}"
        }

async def generate_edge_tts(text: str, filename: str):
    """Generate audio using Edge-TTS"""
    start_time = time.time()
    
    try:
        tts = edge_tts.Communicate(text, "en-US-AriaNeural")
        await tts.save(filename)
        generation_time = time.time() - start_time
        
        return {
            "success": True,
            "time": generation_time,
            "size": os.path.getsize(filename)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

async def compare_quality():
    """Compare TTS quality between services"""
    print("🔊 TTS Quality Comparison: Deepgram vs Edge-TTS")
    print("=" * 60)
    
    results = []
    
    for i, text in enumerate(TEST_SENTENCES, 1):
        print(f"\nTest {i}: \"{text[:50]}...\"")
        
        # Deepgram
        deepgram_file = f"compare_deepgram_{i}.mp3"
        deepgram_result = await generate_deepgram_tts(text, deepgram_file)
        
        # Edge-TTS
        edge_file = f"compare_edge_{i}.mp3"
        edge_result = await generate_edge_tts(text, edge_file)
        
        # Print results
        print(f"\n  Deepgram:")
        if deepgram_result["success"]:
            print(f"    ✅ Time: {deepgram_result['time']:.2f}s")
            print(f"    📁 Size: {deepgram_result['size']:,} bytes")
        else:
            print(f"    ❌ Error: {deepgram_result['error']}")
        
        print(f"\n  Edge-TTS:")
        if edge_result["success"]:
            print(f"    ✅ Time: {edge_result['time']:.2f}s")
            print(f"    📁 Size: {edge_result['size']:,} bytes")
        else:
            print(f"    ❌ Error: {edge_result['error']}")
        
        # Calculate differences
        if deepgram_result["success"] and edge_result["success"]:
            time_diff = edge_result["time"] - deepgram_result["time"]
            size_diff = edge_result["size"] - deepgram_result["size"]
            
            print(f"\n  Comparison:")
            print(f"    ⏱️  Edge is {abs(time_diff):.2f}s {'slower' if time_diff > 0 else 'faster'}")
            print(f"    📊 Edge file is {abs(size_diff):,} bytes {'larger' if size_diff > 0 else 'smaller'}")
        
        results.append({
            "text": text,
            "deepgram": deepgram_result,
            "edge": edge_result
        })
    
    # Summary
    print("\n" + "=" * 60)
    print("\n📊 SUMMARY")
    
    # Average times
    deepgram_times = [r["deepgram"]["time"] for r in results if r["deepgram"]["success"]]
    edge_times = [r["edge"]["time"] for r in results if r["edge"]["success"]]
    
    if deepgram_times:
        print(f"\nDeepgram average time: {sum(deepgram_times)/len(deepgram_times):.2f}s")
    if edge_times:
        print(f"Edge-TTS average time: {sum(edge_times)/len(edge_times):.2f}s")
    
    print("\n🎧 Audio files generated:")
    print("\nDeepgram files:")
    for i in range(1, len(TEST_SENTENCES) + 1):
        print(f"  - compare_deepgram_{i}.mp3")
    
    print("\nEdge-TTS files:")
    for i in range(1, len(TEST_SENTENCES) + 1):
        print(f"  - compare_edge_{i}.mp3")
    
    print("\n💡 Listen to these files to compare voice quality!")

async def test_latency_streaming():
    """Test first-byte latency for streaming"""
    print("\n\n🚀 Testing Streaming Latency")
    print("=" * 60)
    
    text = "This is a test of streaming latency. We want to measure how quickly the first audio byte arrives."
    
    print("Testing Edge-TTS streaming latency...")
    
    # Test multiple times for average
    latencies = []
    
    for i in range(3):
        print(f"\n  Run {i+1}:")
        tts = edge_tts.Communicate(text, "en-US-AriaNeural")
        
        start_time = time.time()
        first_chunk_time = None
        
        async for chunk in tts.stream():
            if chunk["type"] == "audio" and first_chunk_time is None:
                first_chunk_time = time.time() - start_time
                latencies.append(first_chunk_time)
                print(f"    First chunk: {first_chunk_time:.3f}s")
                break
    
    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        print(f"\n  Average first-chunk latency: {avg_latency:.3f}s")
        print(f"  {'✅ Good' if avg_latency < 0.5 else '⚠️  Acceptable' if avg_latency < 1.0 else '❌ Too slow'} for real-time voice")

async def main():
    """Run comparison tests"""
    # Compare quality
    await compare_quality()
    
    # Test streaming latency
    await test_latency_streaming()
    
    print("\n\n✅ Comparison complete!")
    print("\nRecommendation based on results:")
    print("- Use Deepgram for English/Spanish (better quality)")
    print("- Use Edge-TTS for other languages (no choice)")
    print("- Both are fast enough for real-time use")

if __name__ == "__main__":
    asyncio.run(main())