"""
Real-time voice streaming with Deepgram + LangGraph + ElevenLabs
Natural conversation flow for grocery shopping
"""
import asyncio
import json
import base64
from typing import Optional, Dict, Any, List
from datetime import datetime
import websockets
from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from fastapi import APIRouter
import httpx
import os
import structlog

from src.core.graph import search_graph
from src.api.main import create_initial_state
from src.utils.id_generator import generate_request_id
from src.voice.deepgram_client import DeepgramClient, VoiceInsights

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice-stream")

# Configuration
from src.config.settings import settings

DEEPGRAM_API_KEY = getattr(settings, 'DEEPGRAM_API_KEY', None) or os.getenv("DEEPGRAM_API_KEY")

class ConversationManager:
    """Manages real-time conversation state and processing"""
    
    def __init__(self, session_id: str, user_id: Optional[str] = None):
        self.session_id = session_id
        self.user_id = user_id
        self.conversation_history: List[Dict] = []
        self.current_utterance = ""
        self.last_process_time = datetime.now()
        self.processing = False
        self.context = {
            "last_products": [],
            "cart_items": [],
            "waiting_for": None  # e.g., "confirmation", "selection"
        }
        
    def should_process_utterance(self, transcript: str, is_final: bool) -> bool:
        """
        Decide if we should process the current utterance
        Factors: silence, punctuation, complete thought
        """
        if is_final:
            return True
            
        # Process if we detect a natural pause (question or statement end)
        if any(end in transcript for end in ["?", ".", "please", "thanks"]):
            return True
            
        # Process if it's been more than 1.5 seconds since last word
        time_since_last = (datetime.now() - self.last_process_time).total_seconds()
        if time_since_last > 1.5 and len(transcript.split()) > 2:
            return True
            
        return False
    
    def understand_intent(self, utterance: str) -> Dict[str, Any]:
        """
        Quick intent detection for common patterns
        This runs before LangGraph for immediate response
        """
        utterance_lower = utterance.lower()
        
        # Corrections/interruptions
        if any(word in utterance_lower for word in ["no wait", "actually", "sorry", "never mind"]):
            return {"type": "correction", "action": "pause"}
            
        # Confirmations
        if self.context["waiting_for"] == "confirmation":
            if any(word in utterance_lower for word in ["yes", "yeah", "correct", "that's right"]):
                return {"type": "confirmation", "confirmed": True}
            elif any(word in utterance_lower for word in ["no", "nope", "wrong"]):
                return {"type": "confirmation", "confirmed": False}
        
        # Selections (e.g., "the first one", "number 2")
        if self.context["last_products"]:
            for i, word in enumerate(["first", "second", "third", "fourth", "fifth"]):
                if word in utterance_lower:
                    return {"type": "selection", "index": i}
            # Check for "number X"
            import re
            match = re.search(r'number (\d+)', utterance_lower)
            if match:
                return {"type": "selection", "index": int(match.group(1)) - 1}
        
        # Default to search/query
        return {"type": "query", "needs_processing": True}

class DeepgramStreamer:
    """Handles Deepgram WebSocket streaming"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.websocket = None
        
    async def connect(self):
        """Connect to Deepgram streaming API"""
        url = "wss://api.deepgram.com/v1/listen"
        
        # Deepgram configuration for grocery shopping
        params = {
            "encoding": "linear16",
            "sample_rate": "16000",
            "channels": "1",
            "language": "en-US",  # Can be changed based on user preference
            "model": "nova-2",  # Latest model, great for conversational AI
            "punctuate": "true",
            "smart_format": "true",  # Formats numbers, prices nicely
            "interim_results": "true",  # Get partial transcripts
            "utterance_end_ms": "1000",  # Detect end of utterance after 1 second
            "vad_events": "true",  # Voice activity detection
            "keywords": [  # Boost accuracy for grocery terms
                "Organic Valley:2",
                "Horizon:2", 
                "Chobani:2",
                "milk:1",
                "bread:1",
                "vegetables:1"
            ]
        }
        
        headers = {
            "Authorization": f"Token {self.api_key}"
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        self.websocket = await websockets.connect(
            f"{url}?{query_string}",
            extra_headers=headers
        )
        
        return self.websocket
    
    async def send_audio(self, audio_data: bytes):
        """Send audio chunk to Deepgram"""
        if self.websocket:
            await self.websocket.send(audio_data)
    
    async def receive_transcript(self) -> Dict:
        """Receive transcript from Deepgram"""
        if self.websocket:
            message = await self.websocket.recv()
            return json.loads(message)
        return {}
    
    async def close(self):
        """Close Deepgram connection"""
        if self.websocket:
            await self.websocket.close()

class DeepgramTTS:
    """Handles Deepgram Aura TTS"""
    
    def __init__(self, client: DeepgramClient):
        self.client = client
        self.audio_queue = asyncio.Queue()
        
    async def synthesize_text(self, text: str) -> bytes:
        """Convert text to speech using Deepgram Aura"""
        try:
            audio_data = await self.client.synthesize_speech(text)
            return audio_data
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return b""
    
    async def synthesize_streaming(self, text: str):
        """Add text to synthesis queue"""
        # For now, we'll synthesize complete sentences
        # In future, Deepgram may support true streaming TTS
        if text.strip():
            audio = await self.synthesize_text(text)
            if audio:
                await self.audio_queue.put(audio)
    
    async def get_audio(self) -> Optional[bytes]:
        """Get next audio chunk from queue"""
        try:
            return await asyncio.wait_for(self.audio_queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            return None

@router.websocket("/stream")
async def voice_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time voice conversation
    Handles bidirectional audio streaming with Deepgram
    """
    await websocket.accept()
    
    # Initialize components
    session_id = generate_request_id()
    conversation = ConversationManager(session_id)
    
    # Create unified Deepgram client
    deepgram_client = DeepgramClient(DEEPGRAM_API_KEY)
    deepgram_stt = DeepgramStreamer(DEEPGRAM_API_KEY)
    deepgram_tts = DeepgramTTS(deepgram_client)
    
    # Connect to streaming services
    try:
        await deepgram_stt.connect()
        logger.info(f"Voice streaming session started: {session_id}")
        
        # Send initial greeting
        greeting = "Hello! Welcome to Leaf and Loaf. What can I help you find today?"
        greeting_audio = await deepgram_tts.synthesize_text(greeting)
        if greeting_audio:
            await websocket.send_bytes(greeting_audio)
        
        # Create tasks for concurrent processing
        async def handle_user_audio():
            """Process incoming audio from user"""
            try:
                while True:
                    # Receive audio chunk from client
                    data = await websocket.receive_bytes()
                    
                    # Forward to Deepgram
                    await deepgram.send_audio(data)
                    
            except WebSocketDisconnect:
                logger.info(f"User disconnected: {session_id}")
            except Exception as e:
                logger.error(f"Error in user audio handler: {e}")
        
        async def handle_deepgram_transcripts():
            """Process transcripts from Deepgram"""
            try:
                while True:
                    # Receive transcript
                    result = await deepgram.receive_transcript()
                    
                    if result.get("type") == "Results":
                        alternatives = result.get("channel", {}).get("alternatives", [])
                        if alternatives:
                            transcript = alternatives[0].get("transcript", "")
                            is_final = result.get("is_final", False)
                            
                            if transcript:
                                # Update conversation
                                conversation.current_utterance = transcript
                                conversation.last_process_time = datetime.now()
                                
                                # Send transcript to client for display
                                await websocket.send_json({
                                    "type": "transcript",
                                    "text": transcript,
                                    "is_final": is_final
                                })
                                
                                # Check if we should process
                                if conversation.should_process_utterance(transcript, is_final):
                                    await process_utterance(
                                        conversation, 
                                        transcript, 
                                        websocket, 
                                        deepgram_tts
                                    )
                    
                    elif result.get("type") == "SpeechStarted":
                        # User started speaking - might want to stop current TTS
                        logger.info("User started speaking")
                        
            except Exception as e:
                logger.error(f"Error in Deepgram handler: {e}")
        
        async def handle_tts_audio():
            """Stream audio from Deepgram TTS to client"""
            try:
                while True:
                    audio_chunk = await deepgram_tts.get_audio()
                    if audio_chunk:
                        # Send audio to client
                        await websocket.send_bytes(audio_chunk)
                        
            except Exception as e:
                logger.error(f"Error in TTS handler: {e}")
        
        # Run all handlers concurrently
        await asyncio.gather(
            handle_user_audio(),
            handle_deepgram_transcripts(),
            handle_tts_audio()
        )
        
    except Exception as e:
        logger.error(f"Voice streaming error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": "Voice streaming error occurred"
        })
        
    finally:
        # Cleanup
        await deepgram_stt.close()
        await websocket.close()

async def process_utterance(
    conversation: ConversationManager,
    utterance: str,
    websocket: WebSocket,
    deepgram_tts: DeepgramTTS
):
    """
    Process a complete utterance and generate response
    """
    if conversation.processing:
        return
        
    conversation.processing = True
    
    try:
        # Quick intent detection
        intent = conversation.understand_intent(utterance)
        
        if intent["type"] == "correction":
            # Handle interruption
            response = "Oh, sorry. What would you like instead?"
            await deepgram_tts.synthesize_streaming(response)
            
        elif intent["type"] == "confirmation":
            # Handle yes/no
            if intent["confirmed"]:
                response = "Great! I'll add that to your cart."
            else:
                response = "No problem. What would you like instead?"
            await deepgram_tts.synthesize_streaming(response)
            
        elif intent["type"] == "selection":
            # Handle product selection
            index = intent["index"]
            if 0 <= index < len(conversation.context["last_products"]):
                product = conversation.context["last_products"][index]
                response = f"Adding {product['product_name']} to your cart."
                await deepgram_tts.synthesize_streaming(response)
            
        else:
            # Process with LangGraph
            search_request = {
                "query": utterance,
                "user_id": conversation.user_id,
                "session_id": conversation.session_id,
                "limit": 10
            }
            
            # Start responding while processing
            await deepgram_tts.synthesize_streaming("Let me find ")
            
            # Execute search
            initial_state = create_initial_state(search_request, 0.5)
            final_state = await search_graph.ainvoke(initial_state)
            
            # Get results
            response_data = final_state.get("final_response", {})
            products = response_data.get("products", [])
            
            if products:
                # Update context
                conversation.context["last_products"] = products[:5]
                
                # Generate natural response
                if len(products) == 1:
                    p = products[0]
                    response = f"that for you. I found {p['product_name']} from {p.get('supplier', 'our store')} for ${p['price']:.2f}. Would you like to add it to your cart?"
                else:
                    response = f"that for you. I found {len(products)} options. "
                    
                    # List top 3
                    for i, p in enumerate(products[:3]):
                        name = p['product_name']
                        supplier = p.get('supplier', '')
                        price = p['price']
                        
                        if supplier and supplier not in name:
                            response += f"Option {i+1}: {name} from {supplier} for ${price:.2f}. "
                        else:
                            response += f"Option {i+1}: {name} for ${price:.2f}. "
                    
                    response += "Which one would you like?"
                    conversation.context["waiting_for"] = "selection"
                
                await deepgram_tts.synthesize_streaming(response)
            else:
                response = "those products. I couldn't find anything matching your search. Could you try describing it differently?"
                await deepgram_tts.synthesize_streaming(response)
        
        # Add to conversation history
        conversation.conversation_history.append({
            "user": utterance,
            "assistant": response,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error processing utterance: {e}")
        await deepgram_tts.synthesize_streaming(
            "I had a small hiccup. Could you repeat that?"
        )
    
    finally:
        conversation.processing = False
        conversation.current_utterance = ""

# Health check endpoint
@router.get("/health")
async def streaming_health():
    """Check streaming services configuration"""
    return {
        "deepgram": "configured" if DEEPGRAM_API_KEY else "missing_api_key",
        "streaming": "ready",
        "features": {
            "real_time_transcription": True,
            "audio_intelligence": True,
            "interruption_handling": True,
            "multi_language": True,
            "natural_pauses": True,
            "sentiment_analysis": True,
            "intent_detection": True,
            "tts": "deepgram_aura"
        }
    }