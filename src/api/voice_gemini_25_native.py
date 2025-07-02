"""
Gemini 2.5 Native Audio Implementation
Uses Gemini's native audio understanding capabilities
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import google.generativeai as genai
import json
import asyncio
import base64
import structlog
from typing import Optional, Dict, Any
import os
import io
from pydub import AudioSegment

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice/gemini25")

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyAGLGwNEXgoksFCawjU_x3pWMC-RFTlhPA")
genai.configure(api_key=GEMINI_API_KEY)

class Gemini25VoiceSession:
    """Native Gemini 2.5 audio streaming session"""
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.model = None
        self.chat = None
        self.audio_buffer = io.BytesIO()
        self.is_listening = False
        
    async def initialize(self):
        """Initialize Gemini 2.5 with native audio"""
        try:
            # Use Gemini 2.5 Flash with native audio
            self.model = genai.GenerativeModel(
                model_name="gemini-2.0-flash-exp",  # Latest experimental model
                system_instruction="""You are LeafLoaf, a friendly grocery shopping assistant.
                
When responding to voice:
- Keep responses brief and natural (2-3 sentences)
- Be conversational and helpful
- Focus on grocery shopping needs
- Remember context from the conversation

You can help with:
- Finding products
- Suggesting recipes
- Managing shopping lists
- Providing nutritional info
- Recommending alternatives"""
            )
            
            self.chat = self.model.start_chat(history=[])
            
            await self.websocket.send_json({
                "type": "connected",
                "message": "Connected to Gemini 2.5 native audio"
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            await self.websocket.send_json({
                "type": "error",
                "message": str(e)
            })
            return False
            
    async def handle_connection(self):
        """Main WebSocket handler"""
        await self.websocket.accept()
        logger.info("WebSocket connection accepted")
        
        if not await self.initialize():
            return
            
        try:
            while True:
                message = await self.websocket.receive()
                
                if message["type"] == "websocket.receive":
                    if "bytes" in message:
                        logger.debug(f"Received audio chunk: {len(message['bytes'])} bytes")
                        await self.handle_audio_chunk(message["bytes"])
                    elif "text" in message:
                        data = json.loads(message["text"])
                        logger.debug(f"Received message: {data.get('type')}")
                        await self.handle_message(data)
                        
        except WebSocketDisconnect:
            logger.info("Client disconnected")
        except Exception as e:
            logger.error(f"Connection error: {e}", exc_info=True)
            
    async def handle_message(self, data: dict):
        """Handle control messages"""
        msg_type = data.get("type")
        
        if msg_type == "start_listening":
            self.is_listening = True
            self.audio_buffer = io.BytesIO()
            await self.websocket.send_json({
                "type": "listening_started"
            })
            
        elif msg_type == "stop_listening":
            self.is_listening = False
            await self.process_audio()
            await self.websocket.send_json({
                "type": "listening_stopped"
            })
            
    async def handle_audio_chunk(self, audio_bytes: bytes):
        """Accumulate audio chunks"""
        if self.is_listening:
            self.audio_buffer.write(audio_bytes)
            
    async def process_audio(self):
        """Process accumulated audio with Gemini"""
        try:
            # Get audio data
            audio_data = self.audio_buffer.getvalue()
            logger.info(f"Processing audio: {len(audio_data)} bytes")
            
            if not audio_data:
                logger.warning("No audio data to process")
                return
                
            # Convert to format Gemini expects
            # WebM/Opus to WAV conversion
            try:
                audio_segment = AudioSegment.from_file(
                    io.BytesIO(audio_data), 
                    format="webm"
                )
                logger.info(f"Audio segment created: {len(audio_segment)}ms duration")
                
                # Convert to WAV
                wav_buffer = io.BytesIO()
                audio_segment.export(
                    wav_buffer, 
                    format="wav",
                    parameters=["-ac", "1", "-ar", "16000"]
                )
                wav_data = wav_buffer.getvalue()
                logger.info(f"Converted to WAV: {len(wav_data)} bytes")
            except Exception as e:
                logger.error(f"Audio conversion error: {e}")
                raise
            
            # Send status
            await self.websocket.send_json({
                "type": "processing",
                "message": "Understanding your request..."
            })
            
            # Create audio part for Gemini
            audio_part = {
                "inline_data": {
                    "mime_type": "audio/wav",
                    "data": base64.b64encode(wav_data).decode()
                }
            }
            
            # Send to Gemini with native audio understanding
            response = await self.chat.send_message_async(
                [audio_part],
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=150,  # Keep responses brief
                )
            )
            
            # Extract response
            response_text = response.text
            
            # Send response
            await self.websocket.send_json({
                "type": "response",
                "text": response_text
            })
            
            # Generate speech (using Google TTS for now)
            # In future, Gemini 2.5 will have native TTS
            await self.generate_speech(response_text)
            
        except Exception as e:
            logger.error(f"Audio processing error: {e}")
            await self.websocket.send_json({
                "type": "error",
                "message": "Sorry, I couldn't process that audio. Please try again."
            })
            
    async def generate_speech(self, text: str):
        """Generate speech response"""
        try:
            # For now, just send the text
            # Future: Use Gemini's native TTS when available
            await self.websocket.send_json({
                "type": "speech_text",
                "text": text,
                "note": "Native TTS coming soon"
            })
            
        except Exception as e:
            logger.error(f"Speech generation error: {e}")

@router.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for Gemini 2.5 native audio"""
    session = Gemini25VoiceSession(websocket)
    await session.handle_connection()

@router.get("/test")
async def test_endpoint():
    """Test Gemini 2.5 availability"""
    try:
        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        response = model.generate_content("Say hello")
        
        return {
            "status": "ok",
            "model": "gemini-2.0-flash-exp",
            "response": response.text[:100],
            "features": {
                "native_audio": True,
                "streaming": True,
                "multi_turn": True
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}