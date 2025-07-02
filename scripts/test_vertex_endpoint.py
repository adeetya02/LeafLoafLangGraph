#!/usr/bin/env python3
"""
Test Vertex AI endpoint directly
"""

import os
import json
import httpx
import asyncio
from google.auth.transport.requests import Request
import google.auth

async def test_endpoints():
    # Test both endpoint IDs
    endpoints = [
        ("Code endpoint", "1487855836171599872"),
        ("Env endpoint", "6438719201535328256")
    ]
    
    project_number = "32905605817"
    location = "us-central1"
    
    print("Testing Vertex AI endpoints...")
    print("=" * 60)
    
    for name, endpoint_id in endpoints:
        print(f"\nTesting {name}: {endpoint_id}")
        
        endpoint_domain = f"{endpoint_id}.{location}-{project_number}.prediction.vertexai.goog"
        url = f"https://{endpoint_domain}/v1/projects/{project_number}/locations/{location}/endpoints/{endpoint_id}:predict"
        
        print(f"URL: {url}")
        
        try:
            # Get auth token
            credentials, _ = google.auth.default()
            auth_req = Request()
            credentials.refresh(auth_req)
            token = credentials.token
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "instances": [{
                    "prompt": "Test connection"
                }],
                "parameters": {
                    "temperature": 0.1,
                    "maxOutputTokens": 10
                }
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                print(f"Status: {response.status_code}")
                if response.status_code == 200:
                    print("✓ Endpoint is UP")
                else:
                    print(f"✗ Endpoint error: {response.text[:200]}")
                    
        except Exception as e:
            print(f"✗ Connection error: {str(e)}")

if __name__ == "__main__":
    # Set auth for testing
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        print("Note: Running without Google Cloud credentials")
        print("Set GOOGLE_APPLICATION_CREDENTIALS to test properly")
    
    asyncio.run(test_endpoints())