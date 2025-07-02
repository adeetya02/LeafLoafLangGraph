"""
Full conversational AI with Deepgram STT and TTS
Real-time voice assistant for grocery shopping
"""
import asyncio
import json
import os
import certifi
import base64
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

# Fix SSL for macOS
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

from src.core.graph import search_graph
from src.utils.id_generator import generate_request_id
from src.integrations.gemma_client import GemmaOptimizedClient

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice-conversational")

DEEPGRAM_API_KEY = "36a821d351939023aabad9beeaa68b391caa124a"

class ConversationalAssistant:
    """Handles full conversational flow with STT and TTS"""
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.deepgram = DeepgramClient(
            DEEPGRAM_API_KEY,
            DeepgramClientOptions(options={"keepalive": "true"})
        )
        self.llm = GemmaOptimizedClient()
        self.conversation_history = []
        self.is_processing = False
        self.dg_connection = None
        self.tts_connection = None
        
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
                
                # TTS options
                tts_options = SpeakOptions(
                    model="aura-asteria-en",  # Natural conversational voice
                    encoding="linear16",
                    sample_rate=16000
                )
                
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
                    product_list = "\n".join([f"- {p['name']}: ${p['price']:.2f} {p['unit']}" for p in products[:5]])
                    
                    prompt = f"""You are a friendly grocery store assistant. The customer said: "{user_input}"
                    
Here are the relevant products we have:
{product_list}

Generate a natural, conversational response (2-3 sentences max) that:
1. Acknowledges their request
2. Highlights 2-3 best options with prices
3. Asks if they'd like to add any to their cart or need more info

Keep it friendly and concise for voice output."""
                    
                    response = await self.llm.generate(prompt)
                    return response.strip()
                else:
                    return f"I couldn't find any products matching '{user_input}'. Could you try describing it differently?"
            
            # Handle general conversation
            else:
                # Generate conversational response
                prompt = f"""You are a friendly grocery store voice assistant called LeafLoaf Assistant. 
                
Conversation history:
{self._format_history()}

Customer just said: "{user_input}"

Generate a brief, natural response (1-2 sentences) that:
- Is conversational and friendly
- Helps guide them to shop for groceries
- Suggests they can ask about specific products

Keep it concise for voice output."""
                
                response = await self.llm.generate(prompt)
                return response.strip()
                
        except Exception as e:
            logger.error(f"Error processing input: {e}")
            return "I'm sorry, I had trouble understanding that. Could you please try again?"
    
    async def search_products(self, query: str) -> list:
        """Search for products using LeafLoaf search"""
        try:
            # Create search state
            initial_state = {
                "query": query,
                "user_id": "voice_user",
                "request_id": generate_request_id(),
                "limit": 10,
                "session_id": "voice_session"
            }
            
            # Execute search
            result = await asyncio.to_thread(
                search_graph.invoke,
                initial_state
            )
            
            # Extract products
            products = []
            if result.get("products"):
                products = [
                    {
                        "name": p.get("name", "Unknown"),
                        "price": float(p.get("price", 0)),
                        "unit": p.get("unit", ""),
                        "category": p.get("category", "")
                    }
                    for p in result["products"][:10]
                ]
            
            return products
            
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
    
    def _format_history(self) -> str:
        """Format conversation history for LLM"""
        # Keep last 5 exchanges
        recent = self.conversation_history[-10:]
        return "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent])
    
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
                    # Audio data from client
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
        logger.info("Cleaned up conversational session")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "voice-conversational-ai",
        "features": {
            "stt": True,
            "tts": True,
            "llm": True,
            "search": True
        }
    }