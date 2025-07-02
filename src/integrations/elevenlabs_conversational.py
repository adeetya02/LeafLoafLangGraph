"""
11Labs Conversational AI Integration
Uses their WebSocket API for natural voice conversations
"""
import os
import json
import asyncio
import websockets
from typing import Optional, Dict, Any, Callable
import structlog
from datetime import datetime

logger = structlog.get_logger()

class ElevenLabsConversationalAgent:
    """11Labs Conversational AI WebSocket client"""
    
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.agent_id = os.getenv("ELEVENLABS_AGENT_ID")  # You'll need to create an agent
        self.ws_url = "wss://api.elevenlabs.io/v1/convai/conversation"
        self.webhook_url = os.getenv("LEAFLOAF_WEBHOOK_URL", "http://localhost:8080/api/v1/voice/webhook")
        
    async def create_conversation_config(self) -> Dict[str, Any]:
        """Create configuration for 11Labs conversation"""
        return {
            "agent": {
                "prompt": {
                    "prompt": """You are a helpful shopping assistant for Leaf and Loaf, an organic grocery store. 
                    Your role is to help customers find products, add items to their cart, and complete orders.
                    
                    You have access to these tools:
                    - search_products: Search for products in our catalog
                    - add_to_cart: Add items to the customer's shopping cart
                    - show_cart: Show current cart contents
                    - confirm_order: Confirm and place the order
                    
                    Be friendly, helpful, and guide customers through their shopping experience.
                    When they ask for products, search for them. When they want to add items, help them add to cart.
                    Always confirm what you're adding before doing so.""",
                    "tools": [
                        {
                            "type": "webhook",
                            "name": "search_products",
                            "description": "Search for products in the catalog",
                            "url": f"{self.webhook_url}/search",
                            "method": "POST",
                            "headers": {
                                "Content-Type": "application/json"
                            },
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "Product search query"
                                    }
                                },
                                "required": ["query"]
                            }
                        },
                        {
                            "type": "webhook", 
                            "name": "add_to_cart",
                            "description": "Add items to shopping cart",
                            "url": f"{self.webhook_url}/add_to_cart",
                            "method": "POST",
                            "headers": {
                                "Content-Type": "application/json"
                            },
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "items": {
                                        "type": "array",
                                        "description": "Items to add to cart"
                                    }
                                },
                                "required": ["items"]
                            }
                        },
                        {
                            "type": "webhook",
                            "name": "show_cart",
                            "description": "Show current cart contents",
                            "url": f"{self.webhook_url}/show_cart",
                            "method": "POST"
                        },
                        {
                            "type": "webhook",
                            "name": "confirm_order",
                            "description": "Confirm and place the order",
                            "url": f"{self.webhook_url}/confirm_order",
                            "method": "POST"
                        }
                    ]
                },
                "voice": os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"),
                "language": "en",
                "model": "eleven_turbo_v2"
            },
            "asr": {
                "model": "whisper",
                "language": "en"
            },
            "tts": {
                "model": "eleven_turbo_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "use_speaker_boost": True
                }
            }
        }
        
    async def start_conversation(
        self,
        session_id: str,
        on_transcript: Optional[Callable] = None,
        on_audio: Optional[Callable] = None,
        on_metadata: Optional[Callable] = None
    ):
        """Start a conversational AI session"""
        
        if not self.api_key:
            logger.error("11Labs API key not configured")
            return
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        config = await self.create_conversation_config()
        
        try:
            async with websockets.connect(
                self.ws_url,
                extra_headers=headers
            ) as websocket:
                
                # Send initial configuration
                await websocket.send(json.dumps({
                    "type": "conversation_initiation",
                    "conversation_config": config
                }))
                
                logger.info(f"Started 11Labs conversation for session {session_id}")
                
                # Handle messages
                async for message in websocket:
                    data = json.loads(message)
                    
                    if data["type"] == "conversation_initiation_response":
                        if data["status"] == "success":
                            logger.info("Conversation initialized successfully")
                        else:
                            logger.error(f"Conversation init failed: {data.get('error')}")
                            
                    elif data["type"] == "audio":
                        # Audio chunk from 11Labs
                        if on_audio:
                            await on_audio(data["audio"])
                            
                    elif data["type"] == "transcript":
                        # User or agent transcript
                        if on_transcript:
                            await on_transcript({
                                "role": data["role"],
                                "text": data["text"],
                                "timestamp": data.get("timestamp")
                            })
                            
                    elif data["type"] == "tool_call":
                        # Agent is calling a tool
                        logger.info(f"Tool call: {data['tool_name']} with {data.get('input')}")
                        
                    elif data["type"] == "metadata":
                        # Conversation metadata
                        if on_metadata:
                            await on_metadata(data)
                            
                    elif data["type"] == "error":
                        logger.error(f"Conversation error: {data.get('error')}")
                        
        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}")
            raise
            
    async def send_audio(self, websocket, audio_data: bytes):
        """Send audio data to 11Labs"""
        await websocket.send(json.dumps({
            "type": "audio",
            "audio": audio_data.hex()  # Convert to hex string
        }))
        
    async def interrupt(self, websocket):
        """Interrupt the agent's speech"""
        await websocket.send(json.dumps({
            "type": "interrupt"
        }))
        
    async def end_conversation(self, websocket):
        """End the conversation"""
        await websocket.send(json.dumps({
            "type": "conversation_end"
        }))


class LeafLoafVoiceAgent:
    """Wrapper for 11Labs agent with LeafLoaf business logic"""
    
    def __init__(self):
        self.client = ElevenLabsConversationalAgent()
        self.sessions = {}
        
    async def handle_conversation(self, session_id: str, user_id: str):
        """Handle a complete voice conversation"""
        
        # Track session
        self.sessions[session_id] = {
            "user_id": user_id,
            "started_at": datetime.utcnow(),
            "transcript": [],
            "cart": {"items": []},
            "search_results": []
        }
        
        async def on_transcript(transcript):
            """Handle transcript updates"""
            self.sessions[session_id]["transcript"].append(transcript)
            logger.info(f"{transcript['role']}: {transcript['text']}")
            
        async def on_audio(audio_chunk):
            """Handle audio chunks - send to client"""
            # In production, stream this to the user's browser
            pass
            
        async def on_metadata(metadata):
            """Handle conversation metadata"""
            if metadata.get("conversation_end"):
                logger.info(f"Conversation ended for session {session_id}")
                
        # Start the conversation
        await self.client.start_conversation(
            session_id=session_id,
            on_transcript=on_transcript,
            on_audio=on_audio,
            on_metadata=on_metadata
        )
        
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get conversation summary"""
        session = self.sessions.get(session_id, {})
        return {
            "transcript": session.get("transcript", []),
            "cart": session.get("cart", {"items": []}),
            "duration": (datetime.utcnow() - session.get("started_at", datetime.utcnow())).total_seconds()
        }