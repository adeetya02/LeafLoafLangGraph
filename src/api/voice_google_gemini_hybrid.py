"""
Hybrid Voice Streaming: Google STT + Gemini + Google TTS
Real-time streaming for multi-language support
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google.cloud import speech
from google.cloud import texttospeech
import google.generativeai as genai
import json
import asyncio
import base64
import structlog
from typing import Optional
import os
import queue
import threading

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice/hybrid")

# Configure services
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyAGLGwNEXgoksFCawjU_x3pWMC-RFTlhPA")
genai.configure(api_key=GEMINI_API_KEY)

class HybridVoiceSession:
    """Combines Google STT, Gemini, and Google TTS for streaming"""
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.language = "en-US"
        
        # Initialize clients
        self.stt_client = speech.SpeechClient()
        self.tts_client = texttospeech.TextToSpeechClient()
        self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Audio streaming
        self.audio_queue = queue.Queue()
        self.is_listening = False
        self.recognition_thread = None
        
        # Conversation
        self.chat = self.gemini_model.start_chat(history=[])
        self.conversation_context = []
        
    async def handle_connection(self):
        """Main WebSocket handler"""
        await self.websocket.accept()
        
        # Send welcome
        await self.websocket.send_json({
            "type": "connected",
            "message": "Connected to LeafLoaf Voice Assistant",
            "capabilities": {
                "languages": [
                    "en-US", "es-US", "hi-IN", "zh-CN", "ar-SA",
                    "bn-IN", "ta-IN", "ko-KR", "ja-JP", "vi-VN"
                ],
                "streaming": True,
                "multi_turn": True
            }
        })
        
        try:
            while True:
                message = await self.websocket.receive()
                
                if message["type"] == "websocket.receive":
                    if "bytes" in message:
                        # Audio data
                        await self.handle_audio_chunk(message["bytes"])
                    elif "text" in message:
                        # JSON message
                        data = json.loads(message["text"])
                        await self.handle_message(data)
                        
        except WebSocketDisconnect:
            logger.info("Client disconnected")
            self.cleanup()
            
    async def handle_message(self, data: dict):
        """Handle control messages"""
        msg_type = data.get("type")
        
        if msg_type == "start_listening":
            self.start_listening()
            
        elif msg_type == "stop_listening":
            self.stop_listening()
            
        elif msg_type == "text":
            # Direct text input
            await self.process_text(data.get("text", ""))
            
        elif msg_type == "set_language":
            self.language = data.get("language", "en-US")
            await self.websocket.send_json({
                "type": "language_changed",
                "language": self.language
            })
            
    async def handle_audio_chunk(self, audio_bytes: bytes):
        """Add audio to processing queue"""
        if self.is_listening:
            self.audio_queue.put(audio_bytes)
            
    def start_listening(self):
        """Start speech recognition"""
        if not self.is_listening:
            self.is_listening = True
            self.recognition_thread = threading.Thread(target=self._recognition_loop)
            self.recognition_thread.start()
            
            asyncio.create_task(self.websocket.send_json({
                "type": "listening_started"
            }))
            
    def stop_listening(self):
        """Stop speech recognition"""
        if self.is_listening:
            self.is_listening = False
            self.audio_queue.put(None)  # Sentinel
            
            asyncio.create_task(self.websocket.send_json({
                "type": "listening_stopped"
            }))
            
    def _recognition_loop(self):
        """Run speech recognition in separate thread"""
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            sample_rate_hertz=48000,
            language_code=self.language,
            alternative_language_codes=self._get_alternative_languages(),
            enable_automatic_punctuation=True,
            enable_word_time_offsets=True,
            model="latest_short",
            speech_contexts=[
                speech.SpeechContext(
                    phrases=[
                        "LeafLoaf", "organic", "gluten-free", "vegan",
                        "add to cart", "checkout", "my order"
                    ],
                    boost=20.0
                )
            ]
        )
        
        streaming_config = speech.StreamingRecognitionConfig(
            config=config,
            interim_results=True,
            single_utterance=False
        )
        
        def request_generator():
            """Generate requests from audio queue"""
            while self.is_listening:
                chunk = self.audio_queue.get()
                if chunk is None:
                    break
                yield speech.StreamingRecognizeRequest(audio_content=chunk)
        
        try:
            responses = self.stt_client.streaming_recognize(
                streaming_config,
                request_generator()
            )
            
            for response in responses:
                if not response.results:
                    continue
                    
                result = response.results[0]
                if not result.alternatives:
                    continue
                    
                transcript = result.alternatives[0].transcript
                confidence = result.alternatives[0].confidence
                
                # Send transcript
                asyncio.run_coroutine_threadsafe(
                    self.websocket.send_json({
                        "type": "transcript",
                        "text": transcript,
                        "is_final": result.is_final,
                        "confidence": confidence,
                        "language": result.language_code if hasattr(result, 'language_code') else self.language
                    }),
                    asyncio.get_event_loop()
                )
                
                # Process final results
                if result.is_final and transcript:
                    asyncio.run_coroutine_threadsafe(
                        self.process_text(transcript),
                        asyncio.get_event_loop()
                    )
                    
        except Exception as e:
            logger.error(f"Recognition error: {e}")
            asyncio.run_coroutine_threadsafe(
                self.websocket.send_json({
                    "type": "error",
                    "message": f"Recognition error: {str(e)}"
                }),
                asyncio.get_event_loop()
            )
            
    async def process_text(self, text: str):
        """Process text with Gemini and generate response"""
        try:
            # Update status
            await self.websocket.send_json({
                "type": "processing",
                "message": "Thinking..."
            })
            
            # Build context-aware prompt
            prompt = f"""You are LeafLoaf, a friendly grocery shopping assistant.
Current language: {self.language}

Customer said: "{text}"

Previous context: {self._get_context()}

Instructions:
- Respond naturally and conversationally
- Keep responses brief (2-3 sentences max)
- Be helpful with grocery shopping
- Remember previous items mentioned
- Suggest relevant products when appropriate
- Be culturally aware based on language

Respond in the same language the customer is using."""

            # Get Gemini response
            response = self.chat.send_message(prompt)
            response_text = response.text
            
            # Update context
            self.conversation_context.append({
                "user": text,
                "assistant": response_text
            })
            
            # Send text response
            await self.websocket.send_json({
                "type": "response",
                "text": response_text
            })
            
            # Generate TTS
            await self.generate_speech(response_text)
            
        except Exception as e:
            logger.error(f"Processing error: {e}")
            await self.websocket.send_json({
                "type": "error",
                "message": f"Processing error: {str(e)}"
            })
            
    async def generate_speech(self, text: str):
        """Generate speech with Google TTS"""
        try:
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Select voice based on language
            voice = self._get_voice_for_language()
            
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.0,
                pitch=0.0
            )
            
            response = self.tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            # Send audio
            await self.websocket.send_json({
                "type": "audio",
                "data": base64.b64encode(response.audio_content).decode(),
                "format": "mp3"
            })
            
        except Exception as e:
            logger.error(f"TTS error: {e}")
            
    def _get_alternative_languages(self):
        """Get alternative languages based on primary language"""
        alternatives = {
            "en-US": ["es-US", "en-IN"],
            "es-US": ["en-US", "es-MX"],
            "hi-IN": ["en-IN", "bn-IN"],
            "zh-CN": ["en-US"],
            "ar-SA": ["en-US"],
        }
        return alternatives.get(self.language, ["en-US"])[:3]  # Max 3 alternatives
        
    def _get_voice_for_language(self):
        """Get TTS voice for language"""
        voice_map = {
            "en-US": ("en-US-Journey-D", texttospeech.SsmlVoiceGender.NEUTRAL),
            "es-US": ("es-US-Neural2-A", texttospeech.SsmlVoiceGender.FEMALE),
            "hi-IN": ("hi-IN-Neural2-D", texttospeech.SsmlVoiceGender.NEUTRAL),
            "zh-CN": ("cmn-CN-Wavenet-C", texttospeech.SsmlVoiceGender.NEUTRAL),
            "ar-SA": ("ar-XA-Wavenet-D", texttospeech.SsmlVoiceGender.NEUTRAL),
            "bn-IN": ("bn-IN-Wavenet-A", texttospeech.SsmlVoiceGender.FEMALE),
            "ta-IN": ("ta-IN-Wavenet-D", texttospeech.SsmlVoiceGender.NEUTRAL),
            "ko-KR": ("ko-KR-Wavenet-D", texttospeech.SsmlVoiceGender.NEUTRAL),
            "ja-JP": ("ja-JP-Wavenet-D", texttospeech.SsmlVoiceGender.NEUTRAL),
            "vi-VN": ("vi-VN-Wavenet-D", texttospeech.SsmlVoiceGender.NEUTRAL),
        }
        
        voice_name, gender = voice_map.get(self.language, ("en-US-Journey-D", texttospeech.SsmlVoiceGender.NEUTRAL))
        
        return texttospeech.VoiceSelectionParams(
            language_code=self.language,
            name=voice_name,
            ssml_gender=gender
        )
        
    def _get_context(self):
        """Get recent conversation context"""
        if not self.conversation_context:
            return "No previous conversation"
            
        # Last 3 exchanges
        recent = self.conversation_context[-3:]
        context_lines = []
        for exchange in recent:
            if exchange.get("user"):
                context_lines.append(f"Customer: {exchange['user']}")
            if exchange.get("assistant"):
                context_lines.append(f"You: {exchange['assistant']}")
                
        return "\n".join(context_lines)
        
    def cleanup(self):
        """Clean up resources"""
        self.stop_listening()
        if self.recognition_thread:
            self.recognition_thread.join(timeout=1)

@router.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for hybrid voice streaming"""
    session = HybridVoiceSession(websocket)
    await session.handle_connection()

@router.get("/test")
async def test_endpoint():
    """Test if services are working"""
    try:
        # Test STT
        stt_client = speech.SpeechClient()
        
        # Test Gemini
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("Say hello")
        
        # Test TTS
        tts_client = texttospeech.TextToSpeechClient()
        
        return {
            "status": "ok",
            "services": {
                "stt": "Google Cloud Speech-to-Text",
                "llm": "Gemini 1.5 Flash",
                "tts": "Google Cloud Text-to-Speech"
            },
            "gemini_response": response.text[:100]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}