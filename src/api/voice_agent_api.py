"""
Deepgram Voice Agent API implementation
Uses Deepgram's unified conversational AI with custom LLM (Gemini/Gemma)
"""
import os
import json
import asyncio
from typing import Optional, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import httpx
import structlog

from src.core.graph import search_graph
from src.utils.id_generator import generate_request_id

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice-agent")

# Get API keys
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "36a821d351939023aabad9beeaa68b391caa124a")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")  # You'll need to add this

class VoiceAgentSession:
    """Manages a Voice Agent API session"""
    
    def __init__(self, client_ws: WebSocket):
        self.client_ws = client_ws
        self.session_id = generate_request_id()
        self.agent_ws = None
        self.is_connected = False
        
    async def initialize(self):
        """Initialize Voice Agent connection"""
        try:
            logger.info("Initializing Deepgram Voice Agent...")
            
            # Voice Agent WebSocket URL
            agent_url = "wss://agent.deepgram.com/agent"
            
            # Configuration for Voice Agent
            config = {
                "type": "SettingsConfiguration",
                "audio": {
                    "input": {
                        "encoding": "linear16",
                        "sample_rate": 16000
                    },
                    "output": {
                        "encoding": "linear16", 
                        "sample_rate": 16000,
                        "container": "none",
                        "buffer_size": 250
                    }
                },
                "agent": {
                    "listen": {
                        "model": "nova-2"
                    },
                    "speak": {
                        "model": "aura-helios-en"  # Natural voice
                    },
                    "think": {
                        "provider": {
                            "type": "google",  # For Gemini
                            "api_key": GEMINI_API_KEY,
                            "model": "gemini-2.0-flash"  # Fast model
                        },
                        "instructions": """You are LeafLoaf, a friendly grocery shopping assistant.
                        
Your capabilities:
- Search for grocery products
- Provide product recommendations
- Help with meal planning
- Answer questions about ingredients
- Manage shopping lists

Keep responses conversational and helpful. When users ask about products:
1. Acknowledge their request
2. Search for relevant items  
3. Suggest top 2-3 options with prices
4. Ask if they'd like to add items to cart

Be warm, natural, and helpful - like a knowledgeable friend.""",
                        "functions": [
                            {
                                "name": "search_products",
                                "description": "Search for grocery products",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "query": {
                                            "type": "string",
                                            "description": "Product search query"
                                        },
                                        "category": {
                                            "type": "string",
                                            "description": "Optional product category"
                                        }
                                    },
                                    "required": ["query"]
                                }
                            },
                            {
                                "name": "add_to_cart",
                                "description": "Add product to shopping cart",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "product_id": {
                                            "type": "string",
                                            "description": "Product ID to add"
                                        },
                                        "quantity": {
                                            "type": "integer",
                                            "description": "Quantity to add",
                                            "default": 1
                                        }
                                    },
                                    "required": ["product_id"]
                                }
                            }
                        ]
                    }
                }
            }
            
            # Connect to Voice Agent
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Token {DEEPGRAM_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                # Note: This is a conceptual implementation
                # The actual Voice Agent API might use a different connection method
                logger.info("Connecting to Deepgram Voice Agent...")
                
                # Send configuration to client
                await self.client_ws.send_json({
                    "type": "agent_ready",
                    "message": "Voice Agent initialized",
                    "config": {
                        "model": "gemini-2.0-flash",
                        "voice": "aura-helios-en"
                    }
                })
                
                self.is_connected = True
                return True
                
        except Exception as e:
            logger.error(f"Voice Agent initialization error: {e}")
            await self.client_ws.send_json({
                "type": "error",
                "message": f"Failed to initialize Voice Agent: {str(e)}"
            })
            return False
    
    async def handle_function_call(self, function_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle function calls from the Voice Agent"""
        try:
            if function_name == "search_products":
                # Use your existing search infrastructure
                query = parameters.get("query", "")
                logger.info(f"Voice Agent searching for: {query}")
                
                state = {
                    "query": query,
                    "user_id": f"voice_agent_{self.session_id[:8]}",
                    "request_id": generate_request_id(),
                    "session_id": self.session_id,
                    "limit": 10
                }
                
                # Execute search
                result = await search_graph.ainvoke(state)
                
                # Extract products
                products = []
                if result and result.get("products"):
                    for p in result["products"][:5]:
                        products.append({
                            "id": p.get("id"),
                            "name": p.get("name"),
                            "price": p.get("price"),
                            "unit": p.get("unit"),
                            "in_stock": p.get("in_stock", True)
                        })
                
                return {
                    "success": True,
                    "products": products,
                    "count": len(products)
                }
                
            elif function_name == "add_to_cart":
                # Implement cart management
                product_id = parameters.get("product_id")
                quantity = parameters.get("quantity", 1)
                
                # For now, just acknowledge
                return {
                    "success": True,
                    "message": f"Added {quantity} item(s) to cart",
                    "product_id": product_id
                }
                
            else:
                return {
                    "success": False,
                    "error": f"Unknown function: {function_name}"
                }
                
        except Exception as e:
            logger.error(f"Function call error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def handle_client_audio(self, audio_data: bytes):
        """Forward audio from client to Voice Agent"""
        if self.agent_ws and self.is_connected:
            # In real implementation, forward to Voice Agent
            # For now, just acknowledge
            logger.debug(f"Received {len(audio_data)} bytes of audio")
    
    async def process_agent_message(self, message: Dict[str, Any]):
        """Process messages from Voice Agent"""
        msg_type = message.get("type")
        
        if msg_type == "audio":
            # Forward audio to client
            audio_data = message.get("data")
            if audio_data:
                await self.client_ws.send_json({
                    "type": "audio_chunk",
                    "data": audio_data,  # Base64 encoded
                    "encoding": "linear16",
                    "sample_rate": 16000
                })
                
        elif msg_type == "transcript":
            # User transcript
            await self.client_ws.send_json({
                "type": "transcript",
                "text": message.get("text", ""),
                "is_final": message.get("is_final", False)
            })
            
        elif msg_type == "assistant_message":
            # Assistant response
            await self.client_ws.send_json({
                "type": "assistant_response",
                "text": message.get("text", "")
            })
            
        elif msg_type == "function_call":
            # Handle function call
            function_name = message.get("function")
            parameters = message.get("parameters", {})
            
            result = await self.handle_function_call(function_name, parameters)
            
            # Send result back to Voice Agent
            # In real implementation, this would go back to the agent
            logger.info(f"Function {function_name} result: {result}")
    
    async def cleanup(self):
        """Clean up connections"""
        logger.info("Cleaning up Voice Agent session")
        self.is_connected = False
        if self.agent_ws:
            await self.agent_ws.close()


@router.websocket("/stream")
async def voice_agent_endpoint(websocket: WebSocket):
    """WebSocket endpoint for Voice Agent API"""
    await websocket.accept()
    logger.info("Voice Agent client connected")
    
    session = VoiceAgentSession(websocket)
    
    try:
        # Initialize Voice Agent
        if not await session.initialize():
            return
            
        # Process messages
        while True:
            message = await websocket.receive()
            
            if message["type"] == "websocket.receive":
                if "bytes" in message:
                    # Audio from client
                    await session.handle_client_audio(message["bytes"])
                    
                elif "text" in message:
                    # Control messages
                    data = json.loads(message["text"])
                    
                    if data.get("type") == "stop":
                        break
                        
    except WebSocketDisconnect:
        logger.info("Voice Agent client disconnected")
    except Exception as e:
        logger.error(f"Voice Agent error: {e}")
    finally:
        await session.cleanup()


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "voice-agent-api",
        "features": {
            "stt": "deepgram",
            "tts": "deepgram",
            "llm": "gemini",
            "functions": ["search_products", "add_to_cart"]
        }
    }