"""
Gemini 2.0 Flash Voice Implementation
Real-time conversational voice with native audio understanding
"""
import asyncio
import json
import base64
import uuid
import websockets
from typing import Optional, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog
import os
from google.auth import default
import google.auth.transport.requests
import aiohttp

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice/gemini-2-flash")

# Configuration
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "leafloafai")
REGION = os.getenv("GCP_REGION", "us-central1")

# Gemini 2.0 WebSocket endpoint
GEMINI_WS_URL = f"wss://{REGION}-aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/{REGION}/publishers/google/models/gemini-2.0-flash-exp:streamMultiModalContent"

class Gemini2FlashAssistant:
    """Gemini 2.0 Flash voice assistant with native audio understanding"""
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.session_id = str(uuid.uuid4())
        self.gemini_ws = None
        self.access_token = None
        
    async def get_access_token(self) -> str:
        """Get access token for Gemini API"""
        try:
            credentials, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
            credentials.refresh(google.auth.transport.requests.Request())
            return credentials.token
        except Exception as e:
            logger.error(f"Failed to get access token: {e}")
            # Fallback to environment variable if ADC fails
            return os.getenv("GOOGLE_ACCESS_TOKEN", "")
    
    async def connect_to_gemini(self):
        """Establish WebSocket connection to Gemini 2.0"""
        self.access_token = await self.get_access_token()
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        # Connect to Gemini WebSocket
        self.gemini_ws = await websockets.connect(
            GEMINI_WS_URL,
            extra_headers=headers
        )
        
        # Send setup message
        setup_message = {
            "setup": {
                "model": "models/gemini-2.0-flash-exp",
                "generationConfig": {
                    "responseModalities": ["AUDIO", "TEXT"],
                    "speechConfig": {
                        "voiceConfig": {
                            "prebuiltVoiceConfig": {
                                "voiceName": "Aoede"  # Natural voice
                            }
                        }
                    }
                },
                "systemInstruction": {
                    "parts": [{
                        "text": """You are LeafLoaf, a friendly and helpful grocery shopping assistant.
                        
Your personality:
- Warm, conversational, and helpful
- Knowledgeable about groceries and cooking
- Attentive to customer needs
- Responds naturally to emotions and urgency

Your capabilities:
- Help find products
- Suggest recipes and ingredients
- Answer questions about groceries
- Provide cooking tips
- Understand multiple languages (Hindi, Korean, Gujarati, English)

Always be conversational and natural. Match the user's energy and tone.
Keep responses concise for voice interaction."""
                    }]
                }
            }
        }
        
        await self.gemini_ws.send(json.dumps(setup_message))
        logger.info(f"Connected to Gemini 2.0 Flash for session: {self.session_id}")
    
    async def handle_connection(self):
        """Main WebSocket handler"""
        await self.websocket.accept()
        logger.info(f"Gemini 2.0 voice session started: {self.session_id}")
        
        try:
            # Connect to Gemini
            await self.connect_to_gemini()
            
            # Start listening to both WebSockets
            client_task = asyncio.create_task(self.handle_client_messages())
            gemini_task = asyncio.create_task(self.handle_gemini_messages())
            
            # Wait for either to complete
            await asyncio.gather(client_task, gemini_task)
            
        except WebSocketDisconnect:
            logger.info("Client disconnected")
        except Exception as e:
            logger.error(f"Session error: {e}")
            await self.websocket.send_json({
                "type": "error",
                "message": "Sorry, I encountered an error. Please try again."
            })
        finally:
            await self.cleanup()
    
    async def handle_client_messages(self):
        """Handle messages from the client"""
        try:
            while True:
                # Receive from client
                data = await self.websocket.receive()
                
                if "bytes" in data:
                    # Audio data from client
                    audio_data = data["bytes"]
                    await self.send_audio_to_gemini(audio_data)
                    
                elif "text" in data:
                    # Control messages
                    message = json.loads(data["text"])
                    if message.get("type") == "end":
                        break
                    elif message.get("type") == "text":
                        # Text input (fallback)
                        await self.send_text_to_gemini(message.get("text", ""))
                        
        except WebSocketDisconnect:
            logger.info("Client WebSocket disconnected")
        except Exception as e:
            logger.error(f"Client handler error: {e}")
    
    async def handle_gemini_messages(self):
        """Handle messages from Gemini"""
        try:
            while self.gemini_ws:
                # Receive from Gemini
                message = await self.gemini_ws.recv()
                data = json.loads(message)
                
                if "audio" in data:
                    # Audio response from Gemini
                    audio_base64 = data["audio"]["data"]
                    audio_bytes = base64.b64decode(audio_base64)
                    
                    # Send audio to client
                    await self.websocket.send_bytes(audio_bytes)
                    
                elif "text" in data:
                    # Text response (for transcript)
                    text = data["text"]
                    await self.websocket.send_json({
                        "type": "assistant_message",
                        "text": text
                    })
                    
                elif "error" in data:
                    # Error from Gemini
                    logger.error(f"Gemini error: {data['error']}")
                    await self.websocket.send_json({
                        "type": "error",
                        "message": "I'm having trouble understanding. Please try again."
                    })
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("Gemini WebSocket disconnected")
        except Exception as e:
            logger.error(f"Gemini handler error: {e}")
    
    async def send_audio_to_gemini(self, audio_data: bytes):
        """Send audio to Gemini"""
        if not self.gemini_ws:
            return
            
        # Convert audio to base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        # Send audio message
        message = {
            "realtimeInput": {
                "mediaChunks": [{
                    "mimeType": "audio/pcm;rate=16000",
                    "data": audio_base64
                }]
            }
        }
        
        await self.gemini_ws.send(json.dumps(message))
    
    async def send_text_to_gemini(self, text: str):
        """Send text to Gemini (fallback)"""
        if not self.gemini_ws:
            return
            
        message = {
            "realtimeInput": {
                "text": text
            }
        }
        
        await self.gemini_ws.send(json.dumps(message))
    
    async def cleanup(self):
        """Clean up connections"""
        try:
            if self.gemini_ws:
                await self.gemini_ws.close()
            await self.websocket.close()
        except:
            pass

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for Gemini 2.0 Flash voice"""
    assistant = Gemini2FlashAssistant(websocket)
    await assistant.handle_connection()

@router.get("/test")
async def test_gemini():
    """Test Gemini 2.0 connection"""
    try:
        # Test authentication
        credentials, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        credentials.refresh(google.auth.transport.requests.Request())
        
        # Test REST API call
        url = f"https://{REGION}-aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/{REGION}/publishers/google/models/gemini-2.0-flash-exp:generateContent"
        
        headers = {
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "contents": [{
                "parts": [{
                    "text": "Say 'Gemini 2.0 Flash is working!'"
                }]
            }]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                result = await response.json()
                
                if response.status == 200:
                    return {
                        "status": "success",
                        "response": result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No response"),
                        "model": "gemini-2.0-flash-exp",
                        "features": [
                            "Native audio understanding",
                            "Multilingual support",
                            "Real-time streaming",
                            "Emotion detection",
                            "Natural conversation"
                        ]
                    }
                else:
                    return {
                        "status": "error",
                        "message": result.get("error", {}).get("message", "Unknown error"),
                        "code": response.status
                    }
                    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@router.get("/languages")
async def supported_languages():
    """Get supported languages"""
    return {
        "languages": [
            {"code": "en", "name": "English", "native": "English"},
            {"code": "hi", "name": "Hindi", "native": "हिंदी"},
            {"code": "ko", "name": "Korean", "native": "한국어"},
            {"code": "gu", "name": "Gujarati", "native": "ગુજરાતી"},
            {"code": "es", "name": "Spanish", "native": "Español"},
            {"code": "fr", "name": "French", "native": "Français"},
            {"code": "zh", "name": "Chinese", "native": "中文"},
            {"code": "ja", "name": "Japanese", "native": "日本語"},
            {"code": "ar", "name": "Arabic", "native": "العربية"},
            {"code": "pt", "name": "Portuguese", "native": "Português"}
        ],
        "features": {
            "code_switching": True,
            "accent_detection": True,
            "emotion_recognition": True,
            "cultural_context": True
        }
    }