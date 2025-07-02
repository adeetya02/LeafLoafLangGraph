"""
ElevenLabs Conversational AI Integration
Natural voice conversations with function calling for grocery shopping
"""
import asyncio
import json
import uuid
import base64
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
import structlog
import websockets
import httpx

from src.core.graph import search_graph
from src.utils.id_generator import generate_request_id
from src.config.settings import settings

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/elevenlabs")

# ElevenLabs configuration
ELEVENLABS_API_KEY = settings.elevenlabs_api_key
ELEVENLABS_WS_BASE = "wss://api.elevenlabs.io/v1/convai/conversation"

class ElevenLabsConversationHandler:
    """Manages ElevenLabs Conversational AI sessions"""
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.session_id = str(uuid.uuid4())
        self.elevenlabs_ws = None
        self.agent_id = None
        self.current_order = {"items": []}
        self.last_products = []
        self.conversation_history = []
        self.user_id = f"voice_user_{self.session_id[:8]}"
        
    async def handle_connection(self):
        """Handle WebSocket connection lifecycle"""
        await self.websocket.accept()
        
        try:
            # First, create an ElevenLabs agent for this session
            await self.create_agent()
            
            # Connect to ElevenLabs WebSocket
            await self.connect_elevenlabs()
            
            # Send welcome message
            await self.send_to_client({
                "type": "session_started",
                "session_id": self.session_id,
                "agent_id": self.agent_id,
                "message": "🎙️ ElevenLabs Voice Assistant ready! Natural conversations enabled."
            })
            
            # Start parallel processing
            await asyncio.gather(
                self.receive_from_client(),
                self.receive_from_elevenlabs(),
                return_exceptions=True
            )
            
        except WebSocketDisconnect:
            logger.info(f"ElevenLabs session ended: {self.session_id}")
        except Exception as e:
            logger.error(f"ElevenLabs session error: {e}")
            await self.send_error(str(e))
        finally:
            await self.cleanup()
            
    async def create_agent(self):
        """Create ElevenLabs agent with grocery shopping configuration"""
        url = "https://api.elevenlabs.io/v1/convai/agents"
        
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }
        
        agent_config = {
            "name": f"Grocery Assistant {self.session_id[:8]}",
            "prompt": """You are a helpful grocery shopping assistant for Leaf & Loaf grocery store. 
            Your role is to help customers find products, manage their shopping cart, and complete orders.
            
            You have access to these functions:
            - search_products: When customers ask about products, use this to find items
            - add_to_cart: Add products to the customer's shopping cart
            - remove_from_cart: Remove items from the cart
            - update_quantity: Change quantity of items in cart
            - get_cart: Show current cart contents
            - checkout: Complete the order
            
            Be conversational, friendly, and helpful. Ask clarifying questions when needed.
            Always confirm actions like adding items to cart.
            Provide product details like price and supplier when available.
            """,
            "language": "en",
            "voice": {
                "voice_id": "EXAVITQu4vr4xnSDxMaL",  # Bella - warm, friendly female voice
                "model": "turbo_v2_5",
                "stability": 0.5,
                "similarity_boost": 0.8,
                "style": 0.2,
                "use_speaker_boost": True
            },
            "conversation_config": {
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 800
                }
            },
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "search_products",
                        "description": "Search for grocery products in the store",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The product search query (e.g., 'organic milk', 'fresh apples')"
                                }
                            },
                            "required": ["query"]
                        }
                    }
                },
                {
                    "type": "function", 
                    "function": {
                        "name": "add_to_cart",
                        "description": "Add a product to the shopping cart",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "product_id": {
                                    "type": "string",
                                    "description": "The product ID to add to cart"
                                },
                                "quantity": {
                                    "type": "integer",
                                    "description": "Quantity to add (default: 1)",
                                    "default": 1
                                }
                            },
                            "required": ["product_id"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "remove_from_cart", 
                        "description": "Remove a product from the shopping cart",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "product_id": {
                                    "type": "string",
                                    "description": "The product ID to remove from cart"
                                }
                            },
                            "required": ["product_id"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_cart",
                        "description": "Get current cart contents and total",
                        "parameters": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "checkout",
                        "description": "Complete the order and checkout",
                        "parameters": {
                            "type": "object", 
                            "properties": {}
                        }
                    }
                }
            ]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=agent_config,
                    timeout=30.0
                )
                
                if response.status_code == 201:
                    data = response.json()
                    self.agent_id = data["agent_id"]
                    logger.info(f"Created ElevenLabs agent: {self.agent_id}")
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Failed to create agent: {response.text}"
                    )
                    
        except Exception as e:
            logger.error(f"Agent creation error: {e}")
            raise
            
    async def connect_elevenlabs(self):
        """Connect to ElevenLabs WebSocket"""
        if not self.agent_id:
            raise ValueError("Agent ID required for WebSocket connection")
            
        ws_url = f"{ELEVENLABS_WS_BASE}?agent_id={self.agent_id}"
        
        try:
            self.elevenlabs_ws = await websockets.connect(ws_url)
            logger.info(f"Connected to ElevenLabs WebSocket: {self.agent_id}")
        except Exception as e:
            logger.error(f"ElevenLabs WebSocket connection error: {e}")
            raise
            
    async def receive_from_client(self):
        """Receive audio from client and forward to ElevenLabs"""
        while True:
            try:
                data = await self.websocket.receive_bytes()
                
                # Convert to base64 and send to ElevenLabs
                if self.elevenlabs_ws:
                    audio_message = {
                        "type": "user_audio_chunk",
                        "audio": base64.b64encode(data).decode('utf-8')
                    }
                    await self.elevenlabs_ws.send(json.dumps(audio_message))
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Client receive error: {e}")
                break
                
    async def receive_from_elevenlabs(self):
        """Receive messages from ElevenLabs and handle function calls"""
        while self.elevenlabs_ws:
            try:
                message = await self.elevenlabs_ws.recv()
                data = json.loads(message)
                
                await self.handle_elevenlabs_message(data)
                
            except Exception as e:
                logger.error(f"ElevenLabs receive error: {e}")
                break
                
    async def handle_elevenlabs_message(self, data: Dict):
        """Handle different message types from ElevenLabs"""
        msg_type = data.get("type")
        
        logger.info(f"ElevenLabs message: {msg_type}")
        
        if msg_type == "conversation_initiation_metadata":
            # Initial connection established
            await self.send_to_client({
                "type": "agent_ready",
                "conversation_id": data.get("conversation_id")
            })
            
        elif msg_type == "audio":
            # Agent speaking - forward audio to client
            audio_data = base64.b64decode(data["audio"])
            await self.websocket.send_bytes(audio_data)
            
        elif msg_type == "user_transcript":
            # User speech transcription
            await self.send_to_client({
                "type": "transcript",
                "text": data.get("text", ""),
                "is_final": data.get("is_final", False)
            })
            
        elif msg_type == "agent_response":
            # Agent text response
            await self.send_to_client({
                "type": "agent_response", 
                "text": data.get("text", "")
            })
            
        elif msg_type == "function_call":
            # Handle function calls
            await self.handle_function_call(data)
            
        elif msg_type == "conversation_ended":
            # Conversation finished
            await self.send_to_client({
                "type": "conversation_ended"
            })
            
        elif msg_type == "error":
            # Error from ElevenLabs
            await self.send_to_client({
                "type": "error",
                "message": data.get("message", "Unknown error")
            })
            
    async def handle_function_call(self, data: Dict):
        """Execute function calls and send results back to ElevenLabs"""
        function_call = data.get("function_call", {})
        function_name = function_call.get("name")
        arguments = function_call.get("arguments", {})
        call_id = data.get("call_id")
        
        logger.info(f"Function call: {function_name}", arguments=arguments)
        
        try:
            result = await self.execute_function(function_name, arguments)
            
            # Send result back to ElevenLabs
            response_message = {
                "type": "function_call_result",
                "call_id": call_id,
                "result": result
            }
            
            await self.elevenlabs_ws.send(json.dumps(response_message))
            
            # Also inform client
            await self.send_to_client({
                "type": "function_executed",
                "function": function_name,
                "arguments": arguments,
                "result": result
            })
            
        except Exception as e:
            # Send error back to ElevenLabs
            error_message = {
                "type": "function_call_result",
                "call_id": call_id,
                "error": str(e)
            }
            
            await self.elevenlabs_ws.send(json.dumps(error_message))
            logger.error(f"Function call error: {e}")
            
    async def execute_function(self, function_name: str, arguments: Dict) -> Dict[str, Any]:
        """Execute the requested function"""
        
        if function_name == "search_products":
            return await self.search_products(arguments.get("query", ""))
            
        elif function_name == "add_to_cart":
            return await self.add_to_cart(
                arguments.get("product_id"),
                arguments.get("quantity", 1)
            )
            
        elif function_name == "remove_from_cart":
            return await self.remove_from_cart(arguments.get("product_id"))
            
        elif function_name == "get_cart":
            return await self.get_cart()
            
        elif function_name == "checkout":
            return await self.checkout()
            
        else:
            raise ValueError(f"Unknown function: {function_name}")
            
    async def search_products(self, query: str) -> Dict[str, Any]:
        """Search for products using LangGraph"""
        try:
            # Create state for LangGraph search
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
                "user_id": self.user_id,
                "source": "elevenlabs_voice",
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
                "user_context": {"user_id": self.user_id},
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
            products = result.get("search_results", [])[:10]  # Top 10
            self.last_products = products
            
            if products:
                return {
                    "success": True,
                    "products": [
                        {
                            "id": p.get("product_id"),
                            "name": p.get("product_name"),
                            "price": p.get("price"),
                            "supplier": p.get("supplier", ""),
                            "category": p.get("category", ""),
                            "description": p.get("product_description", "")
                        } for p in products
                    ],
                    "count": len(products),
                    "message": f"Found {len(products)} products for '{query}'"
                }
            else:
                return {
                    "success": False,
                    "products": [],
                    "count": 0,
                    "message": f"No products found for '{query}'"
                }
                
        except Exception as e:
            logger.error(f"Search error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Search failed"
            }
            
    async def add_to_cart(self, product_id: str, quantity: int = 1) -> Dict[str, Any]:
        """Add product to cart"""
        try:
            # Find product from last search
            product = None
            for p in self.last_products:
                if p.get("product_id") == product_id:
                    product = p
                    break
                    
            if not product:
                return {
                    "success": False,
                    "message": "Product not found. Please search for it first."
                }
                
            # Check if already in cart
            existing = None
            for item in self.current_order["items"]:
                if item["product_id"] == product_id:
                    existing = item
                    break
                    
            if existing:
                existing["quantity"] += quantity
                message = f"Updated {product['product_name']} quantity to {existing['quantity']}"
            else:
                self.current_order["items"].append({
                    "product_id": product_id,
                    "product_name": product["product_name"],
                    "price": product["price"],
                    "quantity": quantity
                })
                message = f"Added {quantity} {product['product_name']} to cart"
                
            total = sum(item["price"] * item["quantity"] for item in self.current_order["items"])
            
            return {
                "success": True,
                "message": message,
                "cart_total": total,
                "cart_items": len(self.current_order["items"])
            }
            
        except Exception as e:
            logger.error(f"Add to cart error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to add to cart"
            }
            
    async def remove_from_cart(self, product_id: str) -> Dict[str, Any]:
        """Remove product from cart"""
        try:
            for i, item in enumerate(self.current_order["items"]):
                if item["product_id"] == product_id:
                    removed = self.current_order["items"].pop(i)
                    total = sum(item["price"] * item["quantity"] for item in self.current_order["items"])
                    
                    return {
                        "success": True,
                        "message": f"Removed {removed['product_name']} from cart",
                        "cart_total": total,
                        "cart_items": len(self.current_order["items"])
                    }
                    
            return {
                "success": False,
                "message": "Product not found in cart"
            }
            
        except Exception as e:
            logger.error(f"Remove from cart error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to remove from cart"
            }
            
    async def get_cart(self) -> Dict[str, Any]:
        """Get current cart contents"""
        try:
            if not self.current_order["items"]:
                return {
                    "success": True,
                    "items": [],
                    "total": 0,
                    "count": 0,
                    "message": "Your cart is empty"
                }
                
            total = sum(item["price"] * item["quantity"] for item in self.current_order["items"])
            
            return {
                "success": True,
                "items": self.current_order["items"],
                "total": total,
                "count": len(self.current_order["items"]),
                "message": f"You have {len(self.current_order['items'])} items in your cart totaling ${total:.2f}"
            }
            
        except Exception as e:
            logger.error(f"Get cart error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to get cart"
            }
            
    async def checkout(self) -> Dict[str, Any]:
        """Complete the order"""
        try:
            if not self.current_order["items"]:
                return {
                    "success": False,
                    "message": "Your cart is empty. Add some items before checking out."
                }
                
            total = sum(item["price"] * item["quantity"] for item in self.current_order["items"])
            item_count = len(self.current_order["items"])
            order_id = str(uuid.uuid4())[:8]
            
            # Clear cart after successful checkout
            self.current_order = {"items": []}
            
            return {
                "success": True,
                "order_id": order_id,
                "total": total,
                "item_count": item_count,
                "message": f"Order {order_id} confirmed! {item_count} items totaling ${total:.2f}. Ready for pickup in 20 minutes."
            }
            
        except Exception as e:
            logger.error(f"Checkout error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Checkout failed"
            }
            
    async def send_to_client(self, message: Dict):
        """Send JSON message to client"""
        try:
            await self.websocket.send_json(message)
        except Exception as e:
            logger.error(f"Send to client error: {e}")
            
    async def send_error(self, error: str):
        """Send error message to client"""
        await self.send_to_client({
            "type": "error",
            "message": error
        })
        
    async def cleanup(self):
        """Clean up resources"""
        if self.elevenlabs_ws:
            await self.elevenlabs_ws.close()
            
        # Optionally delete the agent (for temporary sessions)
        if self.agent_id:
            try:
                url = f"https://api.elevenlabs.io/v1/convai/agents/{self.agent_id}"
                headers = {"xi-api-key": ELEVENLABS_API_KEY}
                
                async with httpx.AsyncClient() as client:
                    await client.delete(url, headers=headers, timeout=10.0)
                    
                logger.info(f"Deleted ElevenLabs agent: {self.agent_id}")
            except Exception as e:
                logger.warning(f"Failed to delete agent: {e}")


@router.websocket("/connect")
async def elevenlabs_voice_endpoint(websocket: WebSocket):
    """WebSocket endpoint for ElevenLabs Conversational AI"""
    handler = ElevenLabsConversationHandler(websocket)
    await handler.handle_connection()


@router.get("/health")
async def elevenlabs_health():
    """Health check for ElevenLabs integration"""
    return {
        "status": "healthy",
        "service": "elevenlabs_conversational_ai",
        "features": [
            "natural-voice-quality",
            "advanced-turn-taking",
            "function-calling",
            "real-time-streaming",
            "langgraph-integration"
        ]
    }