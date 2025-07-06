"""
Lightweight conversational AI with Deepgram STT and TTS
No graph imports - uses HTTP API for search
Real-time voice assistant for grocery shopping
"""
import asyncio
import json
import os
import certifi
import base64
import httpx
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
    SpeakOptions,
)
import structlog
import uuid

# Fix SSL for macOS
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice-conv")

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "36a821d351939023aabad9beeaa68b391caa124a")

class ConversationalAssistant:
    """Handles full conversational flow with STT and TTS"""
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.deepgram = DeepgramClient(
            DEEPGRAM_API_KEY,
            DeepgramClientOptions(options={"keepalive": "true"})
        )
        self.conversation_history = []
        self.is_processing = False
        self.dg_connection = None
        self.tts_connection = None
        self.api_base_url = os.getenv("API_BASE_URL", "http://localhost:8080")
        
    async def initialize(self):
        """Initialize both STT and TTS connections"""
        try:
            # Initialize STT
            self.dg_connection = self.deepgram.listen.asyncwebsocket.v("1")
            
            # Register STT event handlers
            self.dg_connection.on(LiveTranscriptionEvents.Open, self.on_stt_open)
            self.dg_connection.on(LiveTranscriptionEvents.Transcript, self.on_transcript)
            self.dg_connection.on(LiveTranscriptionEvents.UtteranceEnd, self.on_utterance_end)
            self.dg_connection.on(LiveTranscriptionEvents.Error, self.on_error)
            
            # STT options for conversational AI
            stt_options = LiveOptions(
                model="nova-2",
                language="en-US",
                smart_format=True,
                encoding="linear16",
                sample_rate=16000,
                channels=1,
                interim_results=True,
                utterance_end_ms=1000,
                vad_events=True,
                endpointing=300
            )
            
            # Start STT
            if await self.dg_connection.start(stt_options):
                logger.info("STT connection established")
                
                # Initialize TTS
                self.tts_connection = self.deepgram.speak.asyncwebsocket.v("1")
                
                # Register TTS event handlers
                self.tts_connection.on("Open", self.on_tts_open)
                self.tts_connection.on("AudioData", self.on_audio_data)
                self.tts_connection.on("Metadata", self.on_tts_metadata)
                self.tts_connection.on("Flushed", self.on_tts_flushed)
                self.tts_connection.on("Close", self.on_tts_close)
                self.tts_connection.on("Error", self.on_tts_error)
                
                # TTS options as dictionary
                tts_options = {
                    "model": "aura-asteria-en",  # Natural conversational voice
                    "encoding": "linear16",
                    "sample_rate": "16000"
                }
                
                # Start TTS
                if await self.tts_connection.start(tts_options):
                    logger.info("TTS connection established")
                    
                    # Send welcome message
                    await self.speak("Hello! I'm your LeafLoaf shopping assistant. What can I help you find today?")
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            return False
    
    async def on_stt_open(self, *args, **kwargs):
        """STT connection opened"""
        logger.info("STT WebSocket opened")
        await self.websocket.send_json({
            "type": "system",
            "message": "Voice assistant ready"
        })
    
    async def on_transcript(self, *args, **kwargs):
        """Handle transcript from Deepgram STT"""
        result = kwargs.get("result", {})
        
        sentence = result.channel.alternatives[0].transcript
        if not sentence:
            return
            
        is_final = result.is_final
        
        # Send transcript to client
        await self.websocket.send_json({
            "type": "transcript",
            "text": sentence,
            "is_final": is_final
        })
        
        # Store final transcript
        if is_final:
            self.current_transcript = sentence
            logger.info(f"User said: {sentence}")
    
    async def on_utterance_end(self, *args, **kwargs):
        """User finished speaking - process and respond"""
        if hasattr(self, 'current_transcript') and self.current_transcript and not self.is_processing:
            self.is_processing = True
            
            try:
                user_input = self.current_transcript
                self.current_transcript = ""
                
                # Add to conversation history
                self.conversation_history.append({"role": "user", "content": user_input})
                
                # Process the input
                response = await self.process_user_input(user_input)
                
                # Add response to history
                self.conversation_history.append({"role": "assistant", "content": response})
                
                # Speak the response
                await self.speak(response)
                
            finally:
                self.is_processing = False
    
    async def process_user_input(self, user_input: str) -> str:
        """Process user input and generate response"""
        try:
            # Check if it's a product search query
            if any(word in user_input.lower() for word in ['show', 'find', 'need', 'want', 'looking for', 'have', 'get']):
                # Search for products
                products = await self.search_products(user_input)
                
                if products:
                    # Generate conversational response about products
                    product_list = "\n".join([f"- {p['name']}: ${p['price']:.2f}" for p in products[:5]])
                    
                    # Simple response generation without LLM
                    if len(products) == 1:
                        response = f"I found {products[0]['name']} for ${products[0]['price']:.2f}. Would you like me to add it to your cart?"
                    elif len(products) > 5:
                        response = f"I found {len(products)} options for you. The top choices are {products[0]['name']} at ${products[0]['price']:.2f}, and {products[1]['name']} at ${products[1]['price']:.2f}. Would you like to hear about more options?"
                    else:
                        response = f"I found {len(products)} products. The best match is {products[0]['name']} for ${products[0]['price']:.2f}. Would you like to add any of these to your cart?"
                    
                    return response
                else:
                    return f"I couldn't find any products matching '{user_input}'. Could you try describing it differently?"
            
            # Handle general conversation
            else:
                # Simple conversational responses without LLM
                lower_input = user_input.lower()
                
                if any(greeting in lower_input for greeting in ['hello', 'hi', 'hey', 'good morning', 'good afternoon']):
                    return "Hello! What can I help you find today?"
                elif 'thank' in lower_input:
                    return "You're welcome! Is there anything else you need?"
                elif 'bye' in lower_input or 'goodbye' in lower_input:
                    return "Goodbye! Have a great day and happy shopping!"
                elif 'help' in lower_input:
                    return "I can help you find products, check prices, and add items to your cart. Just tell me what you're looking for!"
                else:
                    return "I can help you find products in our store. What would you like to search for?"
                
        except Exception as e:
            logger.error(f"Error processing input: {e}")
            return "I'm sorry, I had trouble understanding that. Could you please try again?"
    
    async def search_products(self, query: str) -> list:
        """Search products via HTTP API"""
        try:
            # Call the search API endpoint
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base_url}/api/v1/search",
                    json={
                        "query": query,
                        "limit": 10,
                        "user_id": "voice_user",
                        "session_id": str(uuid.uuid4())
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    products = data.get("products", [])
                    
                    # Format products
                    return [
                        {
                            "name": p.get("product_name", p.get("name", "Unknown")),
                            "price": float(p.get("price", 0)),
                            "unit": p.get("unit", ""),
                            "category": p.get("category", "")
                        }
                        for p in products[:10]
                    ]
                else:
                    logger.error(f"Search API error: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    async def speak(self, text: str):
        """Send text to TTS and stream audio back"""
        try:
            logger.info(f"Speaking: {text}")
            
            # Send text to TTS
            await self.tts_connection.send_text(text)
            
            # Flush to ensure all audio is sent
            await self.tts_connection.flush()
            
            # Send response text to client
            await self.websocket.send_json({
                "type": "assistant_response",
                "text": text
            })
            
        except Exception as e:
            logger.error(f"TTS error: {e}")
    
    async def on_audio_data(self, *args, **kwargs):
        """Handle audio data from TTS"""
        audio_data = kwargs.get("data")
        if audio_data:
            # Send audio to client as base64
            await self.websocket.send_json({
                "type": "audio",
                "data": audio_data  # Already base64 encoded from Deepgram
            })
    
    async def on_tts_open(self, *args, **kwargs):
        """TTS connection opened"""
        logger.info("TTS WebSocket opened")
    
    async def on_tts_metadata(self, *args, **kwargs):
        """TTS metadata received"""
        metadata = kwargs.get("metadata", {})
        logger.debug(f"TTS metadata: {metadata}")
    
    async def on_tts_flushed(self, *args, **kwargs):
        """TTS flushed - all audio sent"""
        logger.debug("TTS audio flushed")
    
    async def on_tts_close(self, *args, **kwargs):
        """TTS connection closed"""
        logger.info("TTS WebSocket closed")
    
    async def on_tts_error(self, *args, **kwargs):
        """TTS error"""
        error = kwargs.get("error", "Unknown error")
        logger.error(f"TTS error: {error}")
    
    async def on_error(self, *args, **kwargs):
        """STT error"""
        error = kwargs.get("error", "Unknown error")
        logger.error(f"STT error: {error}")
    
    async def handle_audio(self, audio_data: bytes):
        """Forward audio to STT"""
        if self.dg_connection:
            await self.dg_connection.send(audio_data)
    
    async def cleanup(self):
        """Clean up connections"""
        if self.dg_connection:
            await self.dg_connection.finish()
        if self.tts_connection:
            await self.tts_connection.finish()


@router.websocket("/stream")
async def conversational_endpoint(websocket: WebSocket):
    """WebSocket endpoint for conversational AI"""
    await websocket.accept()
    logger.info("Client connected for conversational AI")
    
    assistant = ConversationalAssistant(websocket)
    
    try:
        # Initialize assistant
        if not await assistant.initialize():
            await websocket.send_json({
                "type": "error",
                "message": "Failed to initialize voice assistant"
            })
            return
        
        # Process messages
        while True:
            message = await websocket.receive()
            
            if message["type"] == "websocket.receive":
                if "bytes" in message:
                    # Audio data
                    await assistant.handle_audio(message["bytes"])
                elif "text" in message:
                    # Control messages
                    data = json.loads(message["text"])
                    if data.get("type") == "stop":
                        break
                        
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await assistant.cleanup()

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "voice-conversational-light",
        "deepgram_configured": bool(DEEPGRAM_API_KEY)
    }