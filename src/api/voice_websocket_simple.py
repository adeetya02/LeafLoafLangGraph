"""
Simple WebSocket voice endpoint for testing
Minimal implementation to get voice working
"""
import asyncio
import json
import base64
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog
from datetime import datetime

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice-simple")

@router.websocket("/ws")
async def simple_voice_websocket(websocket: WebSocket):
    """Simple WebSocket endpoint that accepts audio and returns responses"""
    await websocket.accept()
    logger.info("Simple voice WebSocket connected")
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "message": "Voice WebSocket connected successfully"
        })
        
        audio_buffer = bytearray()
        
        while True:
            # Receive data
            data = await websocket.receive()
            
            if data["type"] == "websocket.receive":
                if "bytes" in data:
                    # Audio data received
                    audio_data = data["bytes"]
                    audio_buffer.extend(audio_data)
                    
                    # Simple silence detection (process every 1MB of audio)
                    if len(audio_buffer) > 1024 * 1024:
                        # Send mock transcript
                        await websocket.send_json({
                            "type": "transcript",
                            "text": "I heard you say something about groceries",
                            "is_final": True
                        })
                        
                        # Send mock response
                        await websocket.send_json({
                            "type": "response",
                            "text": "I can help you find groceries. What are you looking for?",
                            "products": []
                        })
                        
                        # Clear buffer
                        audio_buffer = bytearray()
                        
                elif "text" in data:
                    # JSON message
                    message = json.loads(data["text"])
                    
                    if message.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                    elif message.get("type") == "text":
                        # Direct text input
                        query = message.get("query", "")
                        await websocket.send_json({
                            "type": "response",
                            "text": f"You asked about: {query}",
                            "products": [
                                {"name": "Organic Milk", "price": 4.99},
                                {"name": "Fresh Bread", "price": 2.99}
                            ]
                        })
                        
    except WebSocketDisconnect:
        logger.info("Simple voice WebSocket disconnected")
    except Exception as e:
        logger.error(f"Simple voice WebSocket error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })

@router.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "service": "voice-simple",
        "timestamp": datetime.utcnow().isoformat()
    }