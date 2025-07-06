"""
Multilingual voice streaming with language-specific TTS
Supports: English (Deepgram), Hindi, Gujarati, Korean (Google Cloud TTS)
"""
import asyncio
import json
import os
import time
import re
from typing import Dict, List, Tuple
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn
import structlog
import requests
import base64
from langdetect import detect, LangDetectException

# Enable LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "voice-multilingual"
os.environ["LANGCHAIN_API_KEY"] = "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"

from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)

# Configure logging
import logging
logging.basicConfig(level=logging.DEBUG)
logger = structlog.get_logger()

# API Keys
DEEPGRAM_API_KEY = "36a821d351939023aabad9beeaa68b391caa124a"
GEMINI_API_KEY = "AIzaSyCdbX90Q337x0dg2MIF2g0id7CMnGQSVgg"
ELEVENLABS_API_KEY = "sk_1a54eb09ff3f6cf41a3c2538a1aba969ba17d29f6c7b0032"

app = FastAPI(title="Multilingual Voice Debug")

class MultilingualVoiceSession:
    def __init__(self, websocket: WebSocket, session_id: str):
        self.websocket = websocket
        self.session_id = session_id
        self.deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        self.dg_connection = None
        self.audio_chunks_received = 0
        self.audio_bytes_received = 0
        
        # Track conversation
        self.current_utterance = ""
        self.conversation_history = []
        self.detected_language = "en"
        
    async def initialize(self) -> bool:
        try:
            logger.info("Creating Deepgram connection...")
            self.dg_connection = self.deepgram.listen.asyncwebsocket.v("1")
            
            # Register handlers
            logger.info("Registering event handlers...")
            self.dg_connection.on("open", self.on_open)
            self.dg_connection.on("transcript", self.on_transcript)
            self.dg_connection.on("error", self.on_error)
            self.dg_connection.on("UtteranceEnd", self.on_utterance_end)
            
            # Multi-language options
            options = LiveOptions(
                model="nova-3",
                language="multi",  # Enable multilingual
                encoding="linear16",
                sample_rate=16000,
                channels=1,
                smart_format=True,
                punctuate=True,
                interim_results=True,
                utterance_end_ms=1000,
                vad_events=True,
                endpointing=300,
            )
            
            logger.info("Starting Deepgram connection...")
            success = await self.dg_connection.start(options)
            logger.info(f"Deepgram start result: {success}")
            
            if success:
                await asyncio.sleep(0.5)
                await self.websocket.send_json({
                    "type": "system",
                    "message": "Multilingual voice ready - speak in any language!",
                    "languages": ["English", "हिन्दी", "ગુજરાતી", "한국어"]
                })
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Initialize error: {e}", exc_info=True)
            return False
    
    async def on_open(self, *args, **kwargs):
        logger.info("=== DEEPGRAM OPEN EVENT FIRED ===")
        await self.websocket.send_json({
            "type": "system",
            "message": "Connected - ready for multilingual input"
        })
    
    async def on_transcript(self, *args, **kwargs):
        logger.info(f"=== TRANSCRIPT EVENT === Args: {args}, Kwargs: {kwargs}")
        result = kwargs.get("result")
        
        if result and result.channel:
            transcript = result.channel.alternatives[0].transcript
            
            if transcript:
                self.current_utterance = transcript
                
                # Detect language
                try:
                    self.detected_language = self.detect_language(transcript)
                except:
                    self.detected_language = "en"
            
            await self.websocket.send_json({
                "type": "transcript",
                "text": transcript,
                "is_final": result.is_final,
                "language": self.detected_language
            })
    
    def detect_language(self, text: str) -> str:
        """Detect primary language of text"""
        # Check for scripts first
        if re.search(r'[\u0900-\u097F]', text):  # Devanagari (Hindi)
            return "hi"
        elif re.search(r'[\u0A80-\u0AFF]', text):  # Gujarati
            return "gu"
        elif re.search(r'[\uAC00-\uD7AF]', text):  # Hangul (Korean)
            return "ko"
        
        # Use langdetect for romanized text
        try:
            detected = detect(text)
            if detected in ['hi', 'gu', 'ko']:
                return detected
        except LangDetectException:
            pass
        
        return "en"  # Default to English
    
    def detect_code_switching(self, text: str) -> List[Tuple[str, str]]:
        """Detect language segments in mixed text"""
        segments = []
        
        # Pattern to split by script changes
        # Matches: Devanagari | Gujarati | Hangul | Latin+spaces+punctuation
        pattern = r'([\u0900-\u097F\s]+|[\u0A80-\u0AFF\s]+|[\uAC00-\uD7AF\s]+|[a-zA-Z\s.,!?]+)'
        
        import regex
        parts = regex.findall(pattern, text)
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
                
            if re.search(r'[\u0900-\u097F]', part):
                segments.append((part, 'hi'))
            elif re.search(r'[\u0A80-\u0AFF]', part):
                segments.append((part, 'gu'))
            elif re.search(r'[\uAC00-\uD7AF]', part):
                segments.append((part, 'ko'))
            else:
                segments.append((part, 'en'))
        
        return segments
    
    async def on_utterance_end(self, *args, **kwargs):
        """Handle utterance end - respond with appropriate language TTS"""
        logger.info(f"=== UTTERANCE END === Text: {self.current_utterance}, Language: {self.detected_language}")
        
        if not self.current_utterance or len(self.current_utterance.strip()) == 0:
            return
        
        try:
            # Get LLM response with intent
            full_response = await self.get_llm_response(self.current_utterance, self.detected_language)
            
            # Parse intent
            intent = "unknown"
            response_text = full_response
            
            if full_response.startswith("[") and "]" in full_response:
                intent_end = full_response.index("]")
                intent = full_response[1:intent_end]
                response_text = full_response[intent_end + 1:].strip()
            
            logger.info(f"Intent: {intent}, Language: {self.detected_language}")
            
            # Send intent
            await self.websocket.send_json({
                "type": "intent_detected",
                "intent": intent,
                "utterance": self.current_utterance,
                "language": self.detected_language
            })
            
            # Check for code-switching
            segments = self.detect_code_switching(response_text)
            logger.info(f"Code-switching segments: {segments}")
            
            # Convert to speech with appropriate service
            if len(segments) > 1:
                # Multiple languages detected - use multilingual TTS
                audio_data = await self.multilingual_tts(response_text)
            else:
                # Single language - use language-specific TTS
                audio_data = await self.text_to_speech(response_text, self.detected_language)
            
            if audio_data:
                await self.websocket.send_json({
                    "type": "tts_audio",
                    "text": response_text,
                    "audio": base64.b64encode(audio_data).decode('utf-8'),
                    "intent": intent,
                    "language": self.detected_language
                })
                logger.info(f"Sent TTS response in {self.detected_language}")
                
            # Add to history
            self.conversation_history.append({
                "user": self.current_utterance,
                "assistant": response_text,
                "intent": intent,
                "language": self.detected_language
            })
            
            self.current_utterance = ""
            
        except Exception as e:
            logger.error(f"Error in utterance_end: {e}", exc_info=True)
    
    async def text_to_speech(self, text: str, language: str) -> bytes:
        """Convert text to speech using appropriate service based on language"""
        
        if language in ["en", "es"]:
            # Use Deepgram for English/Spanish
            return await self.deepgram_tts(text)
        else:
            # Use ElevenLabs multilingual for other languages
            return await self.elevenlabs_tts(text, language)
    
    async def deepgram_tts(self, text: str) -> bytes:
        """Deepgram TTS for English/Spanish"""
        url = "https://api.deepgram.com/v1/speak"
        
        headers = {
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": "application/json"
        }
        
        params = {
            "model": "aura-asteria-en",
            "encoding": "mp3"
        }
        
        payload = {"text": text}
        
        logger.info(f"Calling Deepgram TTS for: {text[:50]}...")
        
        response = requests.post(url, headers=headers, params=params, json=payload)
        
        if response.status_code == 200:
            logger.info("Deepgram TTS successful")
            return response.content
        else:
            logger.error(f"Deepgram TTS error: {response.status_code} - {response.text}")
            return None
    
    async def elevenlabs_tts(self, text: str, language: str) -> bytes:
        """ElevenLabs multilingual TTS for Hindi, Gujarati, Korean"""
        url = "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM"  # Rachel voice
        
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }
        
        # Language-specific voice settings
        voice_settings = {
            "hi": {"stability": 0.5, "similarity_boost": 0.75},  # Hindi
            "gu": {"stability": 0.5, "similarity_boost": 0.75},  # Gujarati
            "ko": {"stability": 0.6, "similarity_boost": 0.8},   # Korean
            "default": {"stability": 0.5, "similarity_boost": 0.5}
        }
        
        settings = voice_settings.get(language, voice_settings["default"])
        
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": settings
        }
        
        logger.info(f"Calling ElevenLabs TTS for {language}: {text[:50]}...")
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            logger.info(f"ElevenLabs TTS successful for {language}")
            return response.content
        else:
            logger.error(f"ElevenLabs TTS error: {response.status_code} - {response.text}")
            # Fallback to Deepgram with English pronunciation
            return await self.deepgram_tts(text)
    
    async def multilingual_tts(self, text: str) -> bytes:
        """Handle code-switched text with multiple languages"""
        # For now, use ElevenLabs multilingual which can handle mixed text
        return await self.elevenlabs_tts(text, "multi")
    
    async def get_llm_response(self, user_input: str, language: str) -> str:
        """Get response from Gemini Pro in the same language"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={GEMINI_API_KEY}"
        
        # Language-specific prompts
        language_prompts = {
            "hi": """आप LeafLoaf के लिए एक सहायक किराना खरीदारी सहायक हैं।
हिंदी में जवाब दें। संक्षिप्त और मैत्रीपूर्ण रहें।

महत्वपूर्ण: हर उत्तर की शुरुआत intent से करें [greeting], [product_search], [add_to_cart], [view_cart], [checkout], [help], [unknown]

भारतीय किराने के बारे में जानकारी: दाल, पनीर, घी, मसाला, आटा, चावल""",
            
            "gu": """તમે LeafLoaf માટે મદદરૂપ કરિયાણા ખરીદી સહાયક છો।
ગુજરાતીમાં જવાબ આપો. સંક્ષિપ્ત અને મૈત્રીપૂર્ણ રહો।

મહત્વપૂર્ણ: દરેક જવાબની શરૂઆત intent સાથે કરો [greeting], [product_search], [add_to_cart], [view_cart], [checkout], [help], [unknown]

ગુજરાતી કરિયાણા: ઘી, દાળ, આટો, ચોખા, મસાલા""",
            
            "ko": """당신은 LeafLoaf의 도움이 되는 식료품 쇼핑 도우미입니다.
한국어로 답변하세요. 간결하고 친근하게 대답하세요.

중요: 모든 답변을 의도로 시작하세요 [greeting], [product_search], [add_to_cart], [view_cart], [checkout], [help], [unknown]

한국 식료품: 김치, 고추장, 된장, 라면, 김""",
            
            "en": """You are a helpful grocery shopping assistant for LeafLoaf.
Respond in English. Be concise and friendly.

IMPORTANT: Start every response with intent [greeting], [product_search], [add_to_cart], [view_cart], [checkout], [help], [unknown]"""
        }
        
        # Build conversation
        conversation = language_prompts.get(language, language_prompts["en"])
        conversation += "\n\n"
        
        # Add recent history
        for exchange in self.conversation_history[-3:]:
            conversation += f"User: {exchange['user']}\nAssistant: {exchange['assistant']}\n\n"
        
        conversation += f"User: {user_input}\nAssistant:"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": conversation
                }]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 150,
                "topP": 0.8
            }
        }
        
        logger.info(f"Calling Gemini for {language}: {user_input}")
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            if "candidates" in data and len(data["candidates"]) > 0:
                llm_response = data["candidates"][0]["content"]["parts"][0]["text"]
                logger.info(f"Gemini response: {llm_response[:50]}...")
                return llm_response
            else:
                logger.error(f"Unexpected Gemini response: {data}")
                if language == "hi":
                    return "[unknown] मुझे समझ नहीं आया। कृपया फिर से कहें।"
                elif language == "gu":
                    return "[unknown] મને સમજાયું નહીં. કૃપા કરીને ફરીથી કહો."
                elif language == "ko":
                    return "[unknown] 이해하지 못했습니다. 다시 말씀해 주세요."
                else:
                    return "[unknown] I didn't understand. Please try again."
                
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return "[unknown] I'm having trouble connecting. Please try again."
    
    async def on_error(self, *args, **kwargs):
        error = kwargs.get("error")
        logger.error(f"=== DEEPGRAM ERROR === {error}")
        await self.websocket.send_json({
            "type": "error",
            "message": str(error)
        })
    
    async def send_audio(self, audio_data: bytes):
        self.audio_chunks_received += 1
        self.audio_bytes_received += len(audio_data)
        
        if self.audio_chunks_received % 10 == 0:
            logger.info(f"Audio stats: {self.audio_chunks_received} chunks, {self.audio_bytes_received} bytes")
        
        if self.dg_connection:
            await self.dg_connection.send(audio_data)
    
    async def cleanup(self):
        logger.info(f"Cleanup: Received {self.audio_chunks_received} chunks, {self.audio_bytes_received} bytes total")
        if self.dg_connection:
            await self.dg_connection.finish()


@app.get("/")
async def home():
    with open("test_multilingual.html", "r") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = f"multilingual_{int(time.time())}"
    logger.info(f"=== NEW SESSION: {session_id} ===")
    
    session = MultilingualVoiceSession(websocket, session_id)
    
    try:
        if not await session.initialize():
            logger.error("Failed to initialize")
            await websocket.close()
            return
        
        while True:
            message = await websocket.receive()
            
            if "bytes" in message:
                await session.send_audio(message["bytes"])
            elif "text" in message:
                data = json.loads(message["text"])
                logger.info(f"Control message: {data}")
                
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    finally:
        await session.cleanup()


if __name__ == "__main__":
    print("\n🌍 Multilingual Voice Server")
    print("📍 http://localhost:7777")
    print("\nSupported languages:")
    print("  - English (Deepgram)")
    print("  - हिन्दी (ElevenLabs)")
    print("  - ગુજરાતી (ElevenLabs)")
    print("  - 한국어 (ElevenLabs)")
    print("\nCode-switching supported!\n")
    
    uvicorn.run(app, host="0.0.0.0", port=7777, log_level="info")