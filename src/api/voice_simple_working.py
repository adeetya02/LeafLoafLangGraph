"""
Simple Working Voice Implementation
Direct STT + LLM + TTS pipeline using Deepgram
"""
import asyncio
import json
import uuid
import ssl
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog
import websockets
import httpx

from src.core.graph import search_graph
from src.utils.id_generator import generate_request_id
from src.config.settings import settings

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice-simple")

# Deepgram configuration
DEEPGRAM_API_KEY = '36a821d351939023aabad9beeaa68b391caa124a'

class SimpleVoiceHandler:
    """Simple voice handler with STT + LLM + TTS"""
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.session_id = str(uuid.uuid4())
        self.stt_websocket = None
        self.current_order = {"items": []}
        self.last_products = []
        self.conversation_history = []
        
    async def handle_connection(self):
        """Handle WebSocket connection"""
        await self.websocket.accept()
        
        try:
            # Connect to Deepgram STT
            await self.connect_deepgram_stt()
            
            # Send welcome
            await self.send_message({
                "type": "session_started",
                "session_id": self.session_id,
                "message": "🎙️ Voice assistant ready! Try saying 'search for milk' or 'hello'"
            })
            
            # Start processing
            await asyncio.gather(
                self.receive_from_client(),
                self.process_deepgram_transcripts(),
                return_exceptions=True
            )
            
        except WebSocketDisconnect:
            logger.info(f"Voice session ended: {self.session_id}")
        except Exception as e:
            logger.error(f"Voice session error: {e}")
            await self.send_error(str(e))
        finally:
            await self.cleanup()
            
    async def connect_deepgram_stt(self):
        """Connect to Deepgram STT"""
        url = "wss://api.deepgram.com/v1/listen"
        params = {
            "model": "nova-2",
            "language": "en-US",
            "punctuate": "true",
            "interim_results": "true",
            "utterance_end_ms": "1000",
            "vad_events": "true",
            "encoding": "linear16",
            "sample_rate": "16000"
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        full_url = f"{url}?{query_string}"
        
        # Use subprotocols for authentication
        subprotocols = ["token", DEEPGRAM_API_KEY]
        
        # Create SSL context
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        try:
            self.stt_websocket = await websockets.connect(
                full_url, 
                subprotocols=subprotocols,
                ssl=ssl_context
            )
            logger.info("Connected to Deepgram STT")
        except Exception as e:
            logger.error(f"STT connection error: {e}")
            raise
            
    async def receive_from_client(self):
        """Receive audio from client and forward to Deepgram"""
        while True:
            try:
                audio_data = await self.websocket.receive_bytes()
                
                # Forward to Deepgram STT
                if self.stt_websocket:
                    await self.stt_websocket.send(audio_data)
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Client receive error: {e}")
                break
                
    async def process_deepgram_transcripts(self):
        """Process transcripts from Deepgram"""
        while self.stt_websocket:
            try:
                message = await self.stt_websocket.recv()
                data = json.loads(message)
                
                if data.get("type") == "Results":
                    await self.handle_transcript(data)
                elif data.get("type") == "SpeechStarted":
                    await self.send_message({
                        "type": "user_speaking",
                        "status": "started"
                    })
                elif data.get("type") == "UtteranceEnd":
                    await self.send_message({
                        "type": "user_speaking",
                        "status": "ended"
                    })
                    
            except Exception as e:
                logger.error(f"Transcript processing error: {e}")
                break
                
    async def handle_transcript(self, data: Dict):
        """Handle final transcripts"""
        channel = data.get("channel", {})
        alternatives = channel.get("alternatives", [])
        
        if not alternatives:
            return
            
        best = alternatives[0]
        transcript = best.get("transcript", "").strip()
        is_final = data.get("is_final", False)
        confidence = best.get("confidence", 0.0)
        
        # Send interim results
        if not is_final:
            await self.send_message({
                "type": "interim_transcript",
                "text": transcript,
                "confidence": confidence
            })
            return
            
        # Process final transcript
        if not transcript:
            return
            
        logger.info(f"Processing: '{transcript}' (confidence: {confidence:.2f})")
        
        # Send final transcript
        await self.send_message({
            "type": "final_transcript",
            "text": transcript,
            "confidence": confidence
        })
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": transcript,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Process with LLM
        response = await self.process_with_llm(transcript)
        
        # Add assistant response to history
        self.conversation_history.append({
            "role": "assistant", 
            "content": response["text"],
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Send response to client
        await self.send_message({
            "type": "assistant_response",
            "text": response["text"],
            "products": response.get("products", []),
            "order": response.get("order"),
            "action": response.get("action")
        })
        
        # Generate and send TTS audio
        await self.generate_tts(response["text"])
        
    async def process_with_llm(self, transcript: str) -> Dict[str, Any]:
        """Process transcript with our LangGraph system"""
        
        # Check if this is a greeting
        greeting_words = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]
        if any(word in transcript.lower() for word in greeting_words):
            return {
                "text": "Hello! Welcome to Leaf & Loaf. I can help you search for products, manage your cart, or answer questions. What would you like to do?",
                "action": "greeting"
            }
            
        # Check if this is cart-related
        cart_words = ["cart", "add", "remove", "checkout", "order"]
        if any(word in transcript.lower() for word in cart_words):
            return await self.handle_cart_operation(transcript)
            
        # Otherwise, treat as product search
        return await self.handle_product_search(transcript)
        
    async def handle_product_search(self, query: str) -> Dict[str, Any]:
        """Handle product search"""
        try:
            # Create state for LangGraph
            state = {
                "messages": [{
                    "role": "human",
                    "content": query,
                    "tool_calls": None,
                    "tool_call_id": None
                }],
                "query": query,
                "request_id": generate_request_id(),
                "timestamp": datetime.utcnow(),
                "session_id": self.session_id,
                "user_id": f"voice_user_{self.session_id[:8]}",
                "source": "voice_simple",
                "search_params": {},
                "current_order": self.current_order,
                "alpha_value": 0.5,
                "search_strategy": "hybrid",
                "routing_decision": None,
                "search_results": [],
                "completed_tool_calls": [],
                "agent_timings": {},
                "agent_status": {},
                "next_action": None,
                "reasoning": [],
                "should_search": True,
                "search_metadata": {},
                "pending_tool_calls": [],
                "enhanced_query": None,
                "order_metadata": {},
                "user_context": {"user_id": f"voice_user_{self.session_id[:8]}"},
                "preferences": [],
                "filters": {},
                "total_execution_time": 0,
                "trace_id": str(uuid.uuid4()),
                "span_ids": {},
                "should_continue": True,
                "final_response": {},
                "error": None,
                "intent": None,
                "confidence": 0.0
            }
            
            # Execute search
            result = await search_graph.ainvoke(state)
            products = result.get("search_results", [])[:5]  # Top 5
            self.last_products = products
            
            if products:
                # Generate conversational response
                if len(products) == 1:
                    p = products[0]
                    text = f"I found {p['product_name']} from {p.get('supplier', 'our store')} for ${p['price']:.2f}. Would you like me to add it to your cart?"
                elif len(products) <= 3:
                    text = f"I found {len(products)} options: "
                    text += ", ".join([f"{p['product_name']} for ${p['price']:.2f}" for p in products])
                    text += ". Which one interests you?"
                else:
                    text = f"I found {len(products)} products. The top options are: "
                    text += ", ".join([f"{p['product_name']} for ${p['price']:.2f}" for p in products[:3]])
                    text += f", and {len(products) - 3} more. Would you like to hear about any specific one?"
                    
                return {
                    "text": text,
                    "products": products,
                    "action": "search"
                }
            else:
                return {
                    "text": f"I couldn't find any products matching '{query}'. Could you try a different search term?",
                    "action": "search_no_results"
                }
                
        except Exception as e:
            logger.error(f"Search error: {e}")
            return {
                "text": "I'm having trouble with that search. Could you try again?",
                "action": "error"
            }
            
    async def handle_cart_operation(self, query: str) -> Dict[str, Any]:
        """Handle cart operations"""
        query_lower = query.lower()
        
        if "add" in query_lower and self.last_products:
            # Simple: add first product from last search
            product = self.last_products[0]
            
            # Check if already in cart
            existing = None
            for item in self.current_order["items"]:
                if item["product_id"] == product["product_id"]:
                    existing = item
                    break
                    
            if existing:
                existing["quantity"] += 1
                text = f"Updated {product['product_name']} quantity to {existing['quantity']} in your cart."
            else:
                self.current_order["items"].append({
                    "product_id": product["product_id"],
                    "product_name": product["product_name"],
                    "price": product["price"],
                    "quantity": 1
                })
                text = f"Added {product['product_name']} to your cart for ${product['price']:.2f}."
                
            return {
                "text": text,
                "action": "add_to_cart",
                "order": self.current_order
            }
            
        elif "cart" in query_lower or "show" in query_lower:
            if not self.current_order["items"]:
                return {
                    "text": "Your cart is empty. Would you like me to help you find some products?",
                    "action": "show_cart",
                    "order": self.current_order
                }
            else:
                items = self.current_order["items"]
                total = sum(item["price"] * item["quantity"] for item in items)
                text = f"You have {len(items)} items in your cart: "
                text += ", ".join([f"{item['quantity']} {item['product_name']}" for item in items])
                text += f". Total: ${total:.2f}."
                
                return {
                    "text": text,
                    "action": "show_cart",
                    "order": self.current_order
                }
                
        elif "checkout" in query_lower:
            if not self.current_order["items"]:
                return {
                    "text": "Your cart is empty. Add some items before checking out.",
                    "action": "checkout_empty"
                }
            else:
                total = sum(item["price"] * item["quantity"] for item in self.current_order["items"])
                item_count = len(self.current_order["items"])
                
                # Clear cart
                self.current_order = {"items": []}
                
                return {
                    "text": f"Perfect! Your order of {item_count} items totaling ${total:.2f} has been confirmed. It will be ready for pickup in about 20 minutes. Thank you for shopping with Leaf & Loaf!",
                    "action": "checkout_complete"
                }
                
        else:
            return {
                "text": "I can help you add items to your cart, show your cart, or checkout. What would you like to do?",
                "action": "cart_help"
            }
            
    async def generate_tts(self, text: str):
        """Generate TTS audio and send to client"""
        try:
            url = "https://api.deepgram.com/v1/speak"
            params = {
                "model": "aura-helios-en",
                "encoding": "linear16",
                "container": "wav",
                "sample_rate": "24000"
            }
            
            headers = {
                "Authorization": f"Token {DEEPGRAM_API_KEY}",
                "Content-Type": "application/json"
            }
            
            body = {
                "text": text
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    params=params,
                    headers=headers,
                    json=body,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    # Send audio in chunks
                    audio_data = response.content
                    chunk_size = 4096
                    
                    await self.send_message({
                        "type": "audio_start"
                    })
                    
                    for i in range(0, len(audio_data), chunk_size):
                        chunk = audio_data[i:i + chunk_size]
                        await self.websocket.send_bytes(chunk)
                        await asyncio.sleep(0.01)
                        
                    await self.send_message({
                        "type": "audio_end"
                    })
                    
        except Exception as e:
            logger.error(f"TTS error: {e}")
            
    async def send_message(self, message: Dict):
        """Send JSON message to client"""
        try:
            await self.websocket.send_json(message)
        except Exception as e:
            logger.error(f"Send message error: {e}")
            
    async def send_error(self, error: str):
        """Send error message"""
        await self.send_message({
            "type": "error",
            "message": error
        })
        
    async def cleanup(self):
        """Clean up resources"""
        if self.stt_websocket:
            await self.stt_websocket.close()


@router.websocket("/connect")
async def simple_voice_endpoint(websocket: WebSocket):
    """WebSocket endpoint for simple voice chat"""
    handler = SimpleVoiceHandler(websocket)
    await handler.handle_connection()


@router.get("/health")
async def simple_voice_health():
    """Health check for simple voice"""
    return {
        "status": "healthy",
        "service": "simple_voice",
        "features": [
            "deepgram-stt",
            "deepgram-tts", 
            "langgraph-integration",
            "cart-management",
            "product-search"
        ]
    }