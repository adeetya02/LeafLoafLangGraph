"""
Deepgram Voice Agent API Implementation
Full conversational AI with function calling for LangGraph integration
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

from src.core.graph import search_graph
from src.utils.id_generator import generate_request_id
from src.config.settings import settings

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice-agent")

# Deepgram configuration
DEEPGRAM_API_KEY = '36a821d351939023aabad9beeaa68b391caa124a'
AGENT_ENDPOINT = "wss://agent.deepgram.com/v1/agent/converse"

class DeepgramVoiceAgent:
    """Manages Deepgram Voice Agent conversation"""
    
    def __init__(self, session_id: str, user_id: str = None):
        self.session_id = session_id
        self.user_id = user_id or f"voice_user_{session_id[:8]}"
        self.agent_websocket = None
        self.current_order = {"items": []}
        self.last_products = []
        
    async def connect_agent(self):
        """Connect to Deepgram Voice Agent API"""
        logger.info(f"Connecting to Deepgram Voice Agent: {AGENT_ENDPOINT}")
        
        # Create headers with proper authorization
        headers = {
            "Authorization": f"token {DEEPGRAM_API_KEY}"
        }
        
        # Create SSL context
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        try:
            # Connect with headers for authentication
            self.agent_websocket = await websockets.connect(
                AGENT_ENDPOINT, 
                additional_headers=headers,
                ssl=ssl_context
            )
            logger.info("Deepgram Voice Agent connected successfully")
            
            # Send initial settings
            await self.configure_agent()
            
        except Exception as e:
            logger.error(f"Voice Agent connection error: {type(e).__name__}: {e}")
            raise
            
    async def configure_agent(self):
        """Configure the Voice Agent with our settings"""
        settings_msg = {
            "type": "settings",
            "audio": {
                "input": {
                    "encoding": "linear16",
                    "sample_rate": 16000
                },
                "output": {
                    "encoding": "linear16", 
                    "sample_rate": 24000,
                    "container": "none"
                }
            },
            "agent": {
                "listen": {
                    "model": "nova-2"
                },
                "speak": {
                    "model": "aura-helios-en"
                },
                "think": {
                    "provider": {
                        "type": "open_ai"
                    },
                    "model": "gpt-4o-mini",
                    "instructions": """You are a helpful grocery shopping assistant for Leaf & Loaf grocery store. 
                    Your role is to help customers find products, manage their shopping cart, and complete orders.
                    
                    When customers ask about products, use the search_products function.
                    When they want to add/remove items from cart, use the appropriate cart functions.
                    Be conversational, friendly, and helpful.
                    
                    Available functions:
                    - search_products: Search for grocery products
                    - add_to_cart: Add items to the shopping cart
                    - remove_from_cart: Remove items from the cart
                    - update_quantity: Update quantity of items in cart
                    - get_cart: View current cart contents
                    - checkout: Complete the order
                    """,
                    "functions": [
                        {
                            "name": "search_products",
                            "description": "Search for grocery products",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "The product search query"
                                    }
                                },
                                "required": ["query"]
                            }
                        },
                        {
                            "name": "add_to_cart",
                            "description": "Add a product to the shopping cart",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "product_id": {
                                        "type": "string",
                                        "description": "The product ID to add"
                                    },
                                    "quantity": {
                                        "type": "integer",
                                        "description": "Quantity to add",
                                        "default": 1
                                    }
                                },
                                "required": ["product_id"]
                            }
                        },
                        {
                            "name": "remove_from_cart",
                            "description": "Remove a product from the shopping cart",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "product_id": {
                                        "type": "string",
                                        "description": "The product ID to remove"
                                    }
                                },
                                "required": ["product_id"]
                            }
                        },
                        {
                            "name": "update_quantity",
                            "description": "Update quantity of a product in cart",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "product_id": {
                                        "type": "string",
                                        "description": "The product ID"
                                    },
                                    "quantity": {
                                        "type": "integer",
                                        "description": "New quantity"
                                    }
                                },
                                "required": ["product_id", "quantity"]
                            }
                        },
                        {
                            "name": "get_cart",
                            "description": "Get current cart contents",
                            "parameters": {
                                "type": "object",
                                "properties": {}
                            }
                        },
                        {
                            "name": "checkout",
                            "description": "Complete the order and checkout",
                            "parameters": {
                                "type": "object",
                                "properties": {}
                            }
                        }
                    ]
                }
            }
        }
        
        await self.agent_websocket.send(json.dumps(settings_msg))
        logger.info("Voice Agent configured with grocery shopping functions")
        
    async def handle_function_call(self, function_call: Dict[str, Any]) -> Dict[str, Any]:
        """Handle function calls from the Voice Agent"""
        function_name = function_call.get("name")
        parameters = function_call.get("parameters", {})
        
        logger.info(f"Handling function call: {function_name}", parameters=parameters)
        
        try:
            if function_name == "search_products":
                # Use our search graph
                query = parameters.get("query", "")
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
                    "source": "voice_agent",
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
                
                result = await search_graph.ainvoke(state)
                products = result.get("search_results", [])[:5]  # Top 5 results
                self.last_products = products
                
                # Format response
                if products:
                    product_list = []
                    for i, p in enumerate(products):
                        product_list.append({
                            "id": p.get("product_id"),
                            "name": p.get("product_name"),
                            "price": p.get("price"),
                            "supplier": p.get("supplier", ""),
                            "category": p.get("category", "")
                        })
                    
                    return {
                        "success": True,
                        "products": product_list,
                        "message": f"Found {len(products)} products matching '{query}'"
                    }
                else:
                    return {
                        "success": False,
                        "message": f"No products found for '{query}'"
                    }
                    
            elif function_name == "add_to_cart":
                product_id = parameters.get("product_id")
                quantity = parameters.get("quantity", 1)
                
                # Find product from last search
                product = None
                for p in self.last_products:
                    if p.get("product_id") == product_id:
                        product = p
                        break
                        
                if product:
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
                        
                    return {
                        "success": True,
                        "message": message,
                        "cart_total": sum(item["price"] * item["quantity"] for item in self.current_order["items"])
                    }
                else:
                    return {
                        "success": False,
                        "message": "Product not found. Please search for it first."
                    }
                    
            elif function_name == "remove_from_cart":
                product_id = parameters.get("product_id")
                
                # Find and remove
                for i, item in enumerate(self.current_order["items"]):
                    if item["product_id"] == product_id:
                        removed = self.current_order["items"].pop(i)
                        return {
                            "success": True,
                            "message": f"Removed {removed['product_name']} from cart"
                        }
                        
                return {
                    "success": False,
                    "message": "Product not found in cart"
                }
                
            elif function_name == "update_quantity":
                product_id = parameters.get("product_id")
                quantity = parameters.get("quantity")
                
                for item in self.current_order["items"]:
                    if item["product_id"] == product_id:
                        if quantity <= 0:
                            self.current_order["items"].remove(item)
                            return {
                                "success": True,
                                "message": f"Removed {item['product_name']} from cart"
                            }
                        else:
                            item["quantity"] = quantity
                            return {
                                "success": True,
                                "message": f"Updated {item['product_name']} quantity to {quantity}"
                            }
                            
                return {
                    "success": False,
                    "message": "Product not found in cart"
                }
                
            elif function_name == "get_cart":
                if not self.current_order["items"]:
                    return {
                        "success": True,
                        "message": "Your cart is empty",
                        "items": [],
                        "total": 0
                    }
                    
                items_summary = []
                for item in self.current_order["items"]:
                    items_summary.append(f"{item['quantity']} × {item['product_name']} (${item['price']:.2f})")
                    
                total = sum(item["price"] * item["quantity"] for item in self.current_order["items"])
                
                return {
                    "success": True,
                    "message": f"You have {len(self.current_order['items'])} items in your cart",
                    "items": items_summary,
                    "total": total
                }
                
            elif function_name == "checkout":
                if not self.current_order["items"]:
                    return {
                        "success": False,
                        "message": "Your cart is empty. Add some items before checking out."
                    }
                    
                total = sum(item["price"] * item["quantity"] for item in self.current_order["items"])
                item_count = len(self.current_order["items"])
                
                # Clear cart after checkout
                self.current_order = {"items": []}
                
                return {
                    "success": True,
                    "message": f"Order confirmed! {item_count} items totaling ${total:.2f}. Your order will be ready for pickup in 20 minutes.",
                    "order_id": str(uuid.uuid4())[:8]
                }
                
            else:
                return {
                    "success": False,
                    "message": f"Unknown function: {function_name}"
                }
                
        except Exception as e:
            logger.error(f"Function call error: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }


class VoiceAgentHandler:
    """WebSocket handler for Voice Agent conversations"""
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.session_id = str(uuid.uuid4())
        self.agent = None
        self.audio_buffer = bytearray()
        
    async def handle_connection(self):
        """Handle WebSocket connection lifecycle"""
        await self.websocket.accept()
        
        try:
            # Initialize Voice Agent
            self.agent = DeepgramVoiceAgent(self.session_id)
            await self.agent.connect_agent()
            
            # Send welcome
            await self.send_message({
                "type": "session_started",
                "session_id": self.session_id,
                "message": "Connected to Leaf & Loaf Voice Shopping Assistant"
            })
            
            # Start parallel processing
            await asyncio.gather(
                self.receive_from_client(),
                self.receive_from_agent(),
                return_exceptions=True
            )
            
        except WebSocketDisconnect:
            logger.info(f"Voice agent session ended: {self.session_id}")
        except Exception as e:
            logger.error(f"Voice agent error: {e}")
            await self.send_error(str(e))
        finally:
            await self.cleanup()
            
    async def receive_from_client(self):
        """Receive audio/messages from client and forward to agent"""
        while True:
            try:
                # Try to receive binary (audio) first
                try:
                    audio_data = await self.websocket.receive_bytes()
                    # Forward audio to agent
                    if self.agent.agent_websocket:
                        await self.agent.agent_websocket.send(audio_data)
                except:
                    # Try JSON message
                    data = await self.websocket.receive_json()
                    # Handle client control messages if any
                    logger.info(f"Client message: {data}")
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Client receive error: {e}")
                break
                
    async def receive_from_agent(self):
        """Receive messages from agent and forward to client"""
        while self.agent.agent_websocket:
            try:
                message = await self.agent.agent_websocket.recv()
                
                # Check if it's binary (audio) or text (JSON)
                if isinstance(message, bytes):
                    # Forward audio to client
                    await self.websocket.send_bytes(message)
                else:
                    # Parse JSON message
                    data = json.loads(message)
                    msg_type = data.get("type")
                    
                    logger.info(f"Agent message: {msg_type}")
                    
                    if msg_type == "functionCallRequest":
                        # Handle function call
                        function_call_id = data.get("functionCallId")
                        function_call = data.get("functionCall", {})
                        
                        # Execute function
                        result = await self.agent.handle_function_call(function_call)
                        
                        # Send response back to agent
                        response = {
                            "type": "functionCallResponse",
                            "functionCallId": function_call_id,
                            "result": result
                        }
                        await self.agent.agent_websocket.send(json.dumps(response))
                        
                        # Also inform client
                        await self.send_message({
                            "type": "function_executed",
                            "function": function_call.get("name"),
                            "result": result
                        })
                        
                    elif msg_type == "conversationText":
                        # Forward conversation text to client
                        await self.send_message({
                            "type": "conversation",
                            "role": data.get("role"),
                            "content": data.get("content")
                        })
                        
                    elif msg_type == "userStartedSpeaking":
                        await self.send_message({
                            "type": "user_speaking",
                            "status": "started"
                        })
                        
                    elif msg_type == "agentStartedSpeaking":
                        await self.send_message({
                            "type": "agent_speaking",
                            "status": "started"
                        })
                        
                    elif msg_type == "agentAudioDone":
                        await self.send_message({
                            "type": "agent_speaking",
                            "status": "ended"
                        })
                        
                    elif msg_type == "agentThinking":
                        await self.send_message({
                            "type": "agent_thinking"
                        })
                        
                    elif msg_type == "agentError":
                        await self.send_error(data.get("error", "Agent error occurred"))
                        
            except Exception as e:
                logger.error(f"Agent receive error: {e}")
                break
                
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
        if self.agent and self.agent.agent_websocket:
            await self.agent.agent_websocket.close()


@router.websocket("/connect")
async def voice_agent_endpoint(websocket: WebSocket):
    """WebSocket endpoint for Voice Agent conversations"""
    handler = VoiceAgentHandler(websocket)
    await handler.handle_connection()


@router.get("/health")
async def voice_agent_health():
    """Health check for Voice Agent"""
    return {
        "status": "healthy",
        "service": "deepgram_voice_agent",
        "features": [
            "real-time-stt",
            "gpt-4o-mini",
            "function-calling",
            "cart-management",
            "product-search",
            "conversational-ai"
        ]
    }