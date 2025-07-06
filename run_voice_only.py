#!/usr/bin/env python3
"""
Minimal server for Deepgram conversational voice
No heavy imports - starts instantly
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
from dotenv import load_dotenv
import os
from pathlib import Path

# Load environment variables
load_dotenv()

# Create minimal app
app = FastAPI(
    title="LeafLoaf Voice Server",
    description="Lightweight conversational voice with Deepgram"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import only the lightweight voice router
from src.api.voice_conversational_light import router as voice_router
app.include_router(voice_router)

# Serve static files for the test interface
static_dir = Path(__file__).parent / "src" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir), html=True), name="static")

@app.get("/")
async def root():
    return {
        "service": "LeafLoaf Voice Server",
        "status": "running",
        "endpoints": {
            "websocket": "/api/v1/voice-conv/stream",
            "health": "/api/v1/voice-conv/health",
            "test_interface": "/static/voice_test_conversational.html"
        },
        "description": "Conversational voice assistant with Deepgram STT/TTS"
    }

if __name__ == "__main__":
    print("\n🎤 LeafLoaf Voice Server (Lightweight)")
    print("=" * 50)
    print("Starting conversational voice server...")
    print(f"Deepgram API Key: {'✓ Configured' if os.getenv('DEEPGRAM_API_KEY') else '✗ Not found'}")
    print("\nEndpoints:")
    print("- WebSocket: ws://localhost:8084/api/v1/voice-conv/stream")
    print("- Test UI: http://localhost:8084/static/voice_test_conversational.html")
    print("- Health: http://localhost:8084/api/v1/voice-conv/health")
    print("\nNOTE: Make sure the main LeafLoaf server is running on port 8080")
    print("      for product search to work!")
    print("=" * 50)
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8084,
        ws="websockets"
    )