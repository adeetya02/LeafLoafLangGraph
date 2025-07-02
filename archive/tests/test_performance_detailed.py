#!/usr/bin/env python3
"""Detailed performance test to identify bottlenecks"""

import asyncio
import httpx
import time
import statistics

async def test_performance():
    base_url = 'https://leafloaf-32905605817.us-central1.run.app'
    
    # Warm up the service
    print('=== Warming up service ===')
    async with httpx.AsyncClient(timeout=30.0) as client:
        await client.post(f'{base_url}/api/v1/search', json={'query': 'test'})
    
    # Test multiple queries
    print('\n=== Performance Test (10 queries) ===')
    queries = [
        'spinach',
        'tomatoes', 
        'organic milk',
        'apples',
        'berries',
        'chicken breast',
        'pasta',
        'rice',
        'bread',
        'eggs'
    ]
    
    all_times = []
    exec_times = []
    network_times = []
    
    for query in queries:
        start = time.time()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f'{base_url}/api/v1/search',
                json={'query': query}
            )
        total_time = (time.time() - start) * 1000
        
        if response.status_code == 200:
            data = response.json()
            exec_time = data.get('execution', {}).get('total_time_ms', 0)
            network_time = total_time - exec_time
            
            all_times.append(total_time)
            exec_times.append(exec_time)
            network_times.append(network_time)
            
            print(f'{query:15} Total: {total_time:6.0f}ms | Exec: {exec_time:6.0f}ms | Network: {network_time:6.0f}ms | Products: {len(data.get("products", []))}')
    
    # Calculate statistics
    print('\n=== Performance Summary ===')
    print(f'Average total time:     {statistics.mean(all_times):.0f}ms')
    print(f'Average execution time: {statistics.mean(exec_times):.0f}ms')
    print(f'Average network time:   {statistics.mean(network_times):.0f}ms')
    print(f'Median total time:      {statistics.median(all_times):.0f}ms')
    print(f'Min total time:         {min(all_times):.0f}ms')
    print(f'Max total time:         {max(all_times):.0f}ms')
    
    # Check agent timings for a sample query
    print('\n=== Agent Timing Breakdown (last query) ===')
    if response.status_code == 200:
        data = response.json()
        agent_timings = data.get('execution', {}).get('agent_timings', {})
        for agent, time_ms in agent_timings.items():
            print(f'{agent:20} {time_ms:.1f}ms')
    
    # Performance verdict
    avg = statistics.mean(all_times)
    if avg < 300:
        print('\n✅ MEETING <300ms REQUIREMENT!')
    else:
        print(f'\n⚠️  Average {avg:.0f}ms - Need to reduce by {avg-300:.0f}ms')

if __name__ == "__main__":
    asyncio.run(test_performance())