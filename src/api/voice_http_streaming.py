"""
HTTP Streaming Voice API - Production ready without WebSocket
"""
import asyncio
import base64
import json
import uuid
from typing import Dict, Any
from fastapi import APIRouter, File, UploadFile, Form
from fastapi.responses import StreamingResponse
import structlog
import requests

from src.core.graph import search_graph
from src.utils.id_generator import generate_request_id

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice")

# Deepgram configuration
DEEPGRAM_API_KEY = '36a821d351939023aabad9beeaa68b391caa124a'

class HTTPStreamingHandler:
    """HTTP streaming handler for voice processing"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        
    async def process_audio_stream(self, audio_file: UploadFile):
        """Process audio and yield streaming events"""
        
        try:
            # Step 1: Transcribe audio using Deepgram
            yield self.create_event("status", {"message": "🎤 Transcribing speech..."})
            
            audio_data = await audio_file.read()
            transcript = await self.transcribe_audio(audio_data)
            
            if not transcript:
                yield self.create_event("error", {"message": "Could not understand speech"})
                return
                
            # Step 2: Send transcript to user
            yield self.create_event("transcript", {"text": transcript})
            yield self.create_event("status", {"message": "🧠 Searching products..."})
            
            # Step 3: Process with your production pipeline
            response_data = await self.process_with_search_graph(transcript)
            
            # Step 4: Send response
            if response_data.get("success"):
                products = response_data.get("products", [])
                message = response_data.get("message", "Here's what I found!")
                
                yield self.create_event("response", {
                    "text": message,
                    "products": products[:6]  # Limit for demo
                })
                
                # Step 5: Generate voice response
                yield self.create_event("status", {"message": "🔊 Generating voice..."})
                audio_response = await self.generate_voice_response(message)
                
                if audio_response:
                    yield self.create_event("audio", {"audio": audio_response})
                    
            else:
                yield self.create_event("response", {
                    "text": "I couldn't find what you're looking for. Try asking differently!",
                    "products": []
                })
                
            yield self.create_event("status", {"message": "✅ Complete - Ready for next request"})
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield self.create_event("error", {"message": f"Processing failed: {str(e)}"})
    
    def create_event(self, event_type: str, data: Dict[str, Any]) -> str:
        """Create Server-Sent Event format"""
        event_data = {"type": event_type, **data}
        return f"data: {json.dumps(event_data)}\\n\\n"
    
    async def transcribe_audio(self, audio_data: bytes) -> str:
        """Transcribe audio using Deepgram API"""
        try:
            url = "https://api.deepgram.com/v1/listen"
            headers = {
                "Authorization": f"Token {DEEPGRAM_API_KEY}",
                "Content-Type": "audio/webm"
            }
            params = {
                "model": "nova-2",
                "smart_format": "true",
                "punctuate": "true"
            }
            
            # Use requests for synchronous HTTP call
            response = requests.post(
                url, 
                headers=headers, 
                params=params, 
                data=audio_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                transcript = result["results"]["channels"][0]["alternatives"][0]["transcript"]
                return transcript.strip()
            else:
                logger.error(f"Deepgram error: {response.status_code} - {response.text}")
                return ""
                
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""
    
    async def process_with_search_graph(self, transcript: str) -> Dict[str, Any]:
        """Process transcript using your production search graph"""
        try:
            # Create state for search graph
            state = {
                "messages": [{
                    "role": "human",
                    "content": transcript,
                    "tool_calls": None,
                    "tool_call_id": None
                }],
                "query": transcript,
                "request_id": generate_request_id(),
                "session_id": self.session_id,
                "user_id": f"voice_user_{self.session_id[:8]}",
                "source": "http_voice_streaming"
            }
            
            # Run through your search graph
            result = await search_graph.ainvoke(state)
            
            # Extract results
            final_response = result.get("final_response", {})
            return final_response
            
        except Exception as e:
            logger.error(f"Search graph error: {e}")
            return {
                "success": False,
                "message": "Search temporarily unavailable",
                "products": []
            }
    
    async def generate_voice_response(self, text: str) -> str:
        """Generate TTS using Deepgram (returns base64 audio)"""
        try:
            url = "https://api.deepgram.com/v1/speak"
            headers = {
                "Authorization": f"Token {DEEPGRAM_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "text": text,
                "model": "aura-luna-en",
                "encoding": "mp3"
            }
            
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                # Return base64 encoded audio
                return base64.b64encode(response.content).decode('utf-8')
            else:
                logger.error(f"TTS error: {response.status_code}")
                return ""
                
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return ""

@router.post("/process-stream")
async def process_voice_stream(
    audio: UploadFile = File(...),
    session_id: str = Form(...)
):
    """HTTP streaming voice processing endpoint"""
    
    handler = HTTPStreamingHandler(session_id)
    
    async def generate_stream():
        async for event in handler.process_audio_stream(audio):
            yield event
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )

@router.get("/stream-health")
async def stream_health():
    """Health check for streaming endpoint"""
    return {
        "status": "ok",
        "service": "http-voice-streaming",
        "deepgram_configured": bool(DEEPGRAM_API_KEY)
    }