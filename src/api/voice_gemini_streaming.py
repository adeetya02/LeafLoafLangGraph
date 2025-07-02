"""
Gemini Native Voice Streaming
Multimodal voice support for diverse languages and accents
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import google.generativeai as genai
from google.cloud import texttospeech
import json
import base64
import asyncio
import structlog
from typing import Optional
import os

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice/gemini-stream")

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyAGLGwNEXgoksFCawjU_x3pWMC-RFTlhPA")
genai.configure(api_key=GEMINI_API_KEY)

# TTS client for response audio
tts_client = texttospeech.TextToSpeechClient()

class GeminiVoiceSession:
    """Handles a Gemini voice streaming session"""
    
    def __init__(self, websocket: WebSocket, language: str = "en-US"):
        self.websocket = websocket
        self.language = language
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.conversation = []
        self.audio_buffer = bytearray()
        
    async def handle_connection(self):
        """Handle WebSocket connection"""
        await self.websocket.accept()
        
        # Send welcome
        await self.websocket.send_json({
            "type": "connected",
            "message": "Connected to Gemini Voice Streaming",
            "supported_languages": [
                "en-US", "es-US", "hi-IN", "zh-CN", "ar-SA",
                "bn-IN", "ta-IN", "te-IN", "mr-IN", "gu-IN",
                "ml-IN", "pa-IN", "ur-PK", "vi-VN", "th-TH",
                "ko-KR", "ja-JP", "id-ID", "ms-MY", "tl-PH"
            ]
        })
        
        try:
            while True:
                data = await self.websocket.receive_json()
                
                if data["type"] == "audio_chunk":
                    # Add to buffer
                    audio_bytes = base64.b64decode(data["data"])
                    self.audio_buffer.extend(audio_bytes)
                    
                    # Process when we have enough audio (e.g., 1 second)
                    if len(self.audio_buffer) > 48000:  # ~1 sec at 48kHz
                        await self.process_audio()
                        
                elif data["type"] == "audio_complete":
                    # Process remaining audio
                    if len(self.audio_buffer) > 0:
                        await self.process_audio()
                        
                elif data["type"] == "text":
                    # Direct text input
                    await self.process_text(data["text"])
                    
                elif data["type"] == "set_language":
                    self.language = data["language"]
                    await self.websocket.send_json({
                        "type": "language_changed",
                        "language": self.language
                    })
                    
        except WebSocketDisconnect:
            logger.info("Client disconnected")
        except Exception as e:
            logger.error(f"Session error: {e}")
            await self.websocket.send_json({
                "type": "error",
                "message": str(e)
            })
            
    async def process_audio(self):
        """Process audio buffer with Gemini"""
        try:
            # Convert audio buffer to base64
            audio_data = bytes(self.audio_buffer)
            self.audio_buffer = bytearray()  # Clear buffer
            
            # Create audio part for Gemini
            audio_part = {
                "inline_data": {
                    "mime_type": "audio/webm",
                    "data": base64.b64encode(audio_data).decode()
                }
            }
            
            # Build prompt with language context
            prompt = f"""You are a helpful grocery shopping assistant for LeafLoaf.
            The user is speaking in {self.language}.
            
            Listen to the audio and:
            1. Transcribe what the user said
            2. Provide a helpful response about grocery shopping
            3. Be culturally aware and sensitive to dietary preferences
            
            Previous conversation context: {self.get_conversation_context()}
            
            Respond in JSON format:
            {{
                "transcript": "what the user said",
                "response": "your helpful response",
                "intent": "greeting|product_search|help|other",
                "language_detected": "detected language code"
            }}"""
            
            # Send to Gemini
            response = self.model.generate_content([prompt, audio_part])
            
            # Parse response
            try:
                result = json.loads(response.text)
            except:
                # Fallback if JSON parsing fails
                result = {
                    "transcript": "Audio received",
                    "response": response.text,
                    "intent": "other",
                    "language_detected": self.language
                }
            
            # Update conversation
            self.conversation.append({
                "user": result.get("transcript", ""),
                "assistant": result.get("response", "")
            })
            
            # Send transcript
            await self.websocket.send_json({
                "type": "transcript",
                "text": result.get("transcript", ""),
                "language": result.get("language_detected", self.language)
            })
            
            # Generate TTS for response
            audio_response = await self.generate_speech(
                result.get("response", ""),
                result.get("language_detected", self.language)
            )
            
            # Send response with audio
            await self.websocket.send_json({
                "type": "response",
                "text": result.get("response", ""),
                "audio": base64.b64encode(audio_response).decode(),
                "intent": result.get("intent", "other")
            })
            
        except Exception as e:
            logger.error(f"Audio processing error: {e}")
            await self.websocket.send_json({
                "type": "error",
                "message": f"Processing error: {str(e)}"
            })
            
    async def process_text(self, text: str):
        """Process text input with Gemini"""
        try:
            prompt = f"""You are a helpful grocery shopping assistant for LeafLoaf.
            The user said: "{text}"
            Language preference: {self.language}
            
            Previous conversation: {self.get_conversation_context()}
            
            Provide a helpful response about grocery shopping.
            Be culturally aware and consider dietary preferences.
            
            Respond in JSON format:
            {{
                "response": "your helpful response",
                "intent": "greeting|product_search|help|other",
                "suggestions": ["product1", "product2"] // optional product suggestions
            }}"""
            
            response = self.model.generate_content(prompt)
            
            try:
                result = json.loads(response.text)
            except:
                result = {
                    "response": response.text,
                    "intent": "other"
                }
            
            # Update conversation
            self.conversation.append({
                "user": text,
                "assistant": result.get("response", "")
            })
            
            # Generate TTS
            audio_response = await self.generate_speech(
                result.get("response", ""),
                self.language
            )
            
            # Send response
            await self.websocket.send_json({
                "type": "response",
                "text": result.get("response", ""),
                "audio": base64.b64encode(audio_response).decode(),
                "intent": result.get("intent", "other"),
                "suggestions": result.get("suggestions", [])
            })
            
        except Exception as e:
            logger.error(f"Text processing error: {e}")
            await self.websocket.send_json({
                "type": "error",
                "message": str(e)
            })
            
    async def generate_speech(self, text: str, language: str) -> bytes:
        """Generate speech using Google TTS"""
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        # Select voice based on language
        voice_map = {
            "en-US": "en-US-Journey-D",
            "es-US": "es-US-Neural2-A",
            "hi-IN": "hi-IN-Neural2-D",
            "zh-CN": "cmn-CN-Wavenet-A",
            "ar-SA": "ar-XA-Wavenet-A",
            "bn-IN": "bn-IN-Wavenet-A",
            "ta-IN": "ta-IN-Wavenet-A",
            "ko-KR": "ko-KR-Wavenet-A",
            "ja-JP": "ja-JP-Wavenet-D",
            "vi-VN": "vi-VN-Wavenet-A",
        }
        
        voice_name = voice_map.get(language)
        voice = texttospeech.VoiceSelectionParams(
            language_code=language,
            name=voice_name if voice_name else None,
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,
            pitch=0.0
        )
        
        response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        return response.audio_content
        
    def get_conversation_context(self) -> str:
        """Get recent conversation context"""
        if not self.conversation:
            return "No previous conversation"
        
        # Get last 3 exchanges
        recent = self.conversation[-3:]
        context = []
        for exchange in recent:
            if exchange.get("user"):
                context.append(f"User: {exchange['user']}")
            if exchange.get("assistant"):
                context.append(f"Assistant: {exchange['assistant']}")
        
        return "\n".join(context)

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, language: str = "en-US"):
    """WebSocket endpoint for Gemini voice streaming"""
    session = GeminiVoiceSession(websocket, language)
    await session.handle_connection()

@router.get("/test")
async def test_gemini():
    """Test Gemini multimodal capabilities"""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("Say hello in JSON format with a greeting field")
        return {
            "status": "ok",
            "gemini_response": response.text,
            "model": "gemini-1.5-flash"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }