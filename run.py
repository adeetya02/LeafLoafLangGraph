#!/usr/bin/env python3
"""
Simple run script to start the server
"""
import uvicorn
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

from src.api.main import app
from src.config.settings import settings

if __name__ == "__main__":
    # Verify HuggingFace key is loaded
    hf_key = os.getenv("HUGGINGFACE_API_KEY")
    if hf_key:
        print(f"✓ HuggingFace API key loaded: {hf_key[:10]}...")
    else:
        print("✗ HuggingFace API key not found")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=settings.api_port,
        ws="websockets"  # Enable WebSocket support
    )