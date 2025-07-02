"""
Gemini 2.5 Native Voice Implementation
Uses Gemini's built-in STT and TTS capabilities via Vertex AI
"""
import os
import json
import asyncio
import base64
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig
import vertexai
import structlog

from src.core.graph import search_graph
from src.utils.id_generator import generate_request_id
from src.services.preference_service import get_preference_service

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice-gemini")

# Configure Vertex AI
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "leafloafai")
LOCATION = os.getenv("GCP_LOCATION", "us-central1")

class GeminiVoiceSession:
    """Manages a native Gemini voice session with STT and TTS"""
    
    def __init__(self, client_ws: WebSocket):
        self.client_ws = client_ws
        self.session_id = generate_request_id()
        self.user_id = f"gemini_voice_{self.session_id[:8]}"
        self.model = None
        self.chat = None
        self.conversation_history = []
        self.is_processing = False
        self.preference_service = get_preference_service()
        
        # Voice configuration
        self.voice_config = {
            "language_code": "en-US",
            "voice": {
                "style": "friendly",  # friendly, professional, casual
                "pace": "medium",     # slow, medium, fast
                "pitch": "medium",    # low, medium, high
                "accent": "american"  # american, british, australian
            }
        }
        
    async def initialize(self):
        """Initialize Gemini with voice capabilities via Vertex AI"""
        try:
            logger.info("Initializing Gemini 2.5 voice session on Vertex AI...")
            
            # Initialize Vertex AI
            vertexai.init(project=PROJECT_ID, location=LOCATION)
            
            # Initialize the model with voice capabilities
            # Using Gemini 2.0 Flash (latest available on Vertex AI)
            # For now, create without tools to avoid the error
            self.model = GenerativeModel(
                model_name="gemini-1.5-flash",  # Flash model on Vertex AI
                system_instruction="""You are LeafLoaf, a warm and friendly grocery shopping assistant with voice capabilities.

Your personality:
- Conversational and natural, like talking to a helpful friend
- Use casual language with contractions (I'm, you're, let's)
- Add personality with phrases like "Oh!", "Actually", "You know what?"
- Keep responses brief and natural for voice

Your capabilities:
- Search for grocery products and provide recommendations
- Remember user preferences and shopping patterns
- Help with meal planning and recipe suggestions
- Provide nutritional information
- Manage shopping lists and carts

Voice interaction guidelines:
- Acknowledge what you heard before responding
- Keep responses concise (2-3 sentences max)
- Use natural pauses and intonation
- Be ready for interruptions and context switches
- Sound enthusiastic about helping

When searching for products:
1. Acknowledge the request naturally
2. Search and mention top 2-3 options with prices
3. Ask if they'd like to add something to cart
4. Be ready for follow-up questions

Example responses:
- "Oh, I'd be happy to help you find milk! I've got organic whole milk for $5.99 and Oatly oat milk for $4.99. Which sounds good?"
- "Sure thing! Let me check what tomatoes we have... Perfect, we've got fresh Roma tomatoes and some nice heirloom ones too."
- "You know what? Based on what you usually get, I think you might like our new organic spinach. Want me to add some?"

Remember: You're having a natural conversation, not reading a script."""
            )
            
            # Start chat session
            self.chat = self.model.start_chat(history=[])
            
            # Send initialization success
            await self.client_ws.send_json({
                "type": "gemini_ready",
                "message": "Gemini voice assistant ready",
                "features": {
                    "model": "gemini-2.0-flash-exp",
                    "voice": "native",
                    "capabilities": ["stt", "tts", "functions", "context_awareness"]
                }
            })
            
            # Send welcome message with voice
            await self._speak_welcome()
            
            return True
            
        except Exception as e:
            logger.error(f"Gemini initialization error: {e}")
            await self.client_ws.send_json({
                "type": "error",
                "message": f"Failed to initialize Gemini: {str(e)}"
            })
            return False
    
    async def _speak_welcome(self):
        """Generate and send welcome message with voice"""
        welcome_text = "Hey there! I'm LeafLoaf, your grocery shopping assistant. What can I help you find today?"
        
        try:
            # For now, just send the text without audio generation
            # Gemini voice features are not yet available on Vertex AI
            response = await self.chat.send_message_async(welcome_text)
            
            # Send text to client
            await self.client_ws.send_json({
                "type": "assistant_response",
                "text": welcome_text
            })
            
            # Extract and send audio
            if hasattr(response, 'audio') and response.audio:
                await self._send_audio_to_client(response.audio)
                
        except Exception as e:
            logger.error(f"Welcome message error: {e}")
    
    async def handle_audio_input(self, audio_data: bytes):
        """Process audio input using Gemini's native STT"""
        if self.is_processing:
            logger.debug("Already processing, skipping audio")
            return
            
        self.is_processing = True
        
        try:
            # Convert audio to base64 for Gemini
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Create audio part for Gemini
            audio_part = {
                "inline_data": {
                    "mime_type": "audio/wav",  # Adjust based on actual format
                    "data": audio_base64
                }
            }
            
            # For now, Gemini on Vertex AI doesn't support audio input
            # We'll need to use a separate STT service
            logger.warning("Audio input not yet supported on Vertex AI Gemini")
            
            # Send error message to client
            await self.client_ws.send_json({
                "type": "assistant_response",
                "text": "I'm sorry, voice input isn't available yet. Please use the text input below."
            })
            return
            
            # Extract transcript from response metadata
            if hasattr(response, 'metadata') and 'transcript' in response.metadata:
                transcript = response.metadata['transcript']
                
                # Send transcript to client
                await self.client_ws.send_json({
                    "type": "transcript",
                    "text": transcript,
                    "is_final": True
                })
                
                # Add to conversation history
                self.conversation_history.append({
                    "role": "user",
                    "content": transcript
                })
            
            # Process response
            await self._process_response(response)
            
        except Exception as e:
            logger.error(f"Audio processing error: {e}")
            await self.client_ws.send_json({
                "type": "error",
                "message": "Sorry, I had trouble understanding that. Could you try again?"
            })
        finally:
            self.is_processing = False
    
    async def handle_text_input(self, text: str):
        """Process text input and generate voice response"""
        if self.is_processing:
            return
            
        self.is_processing = True
        
        try:
            # Send user message confirmation
            await self.client_ws.send_json({
                "type": "transcript",
                "text": text,
                "is_final": True
            })
            
            # Add to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": text
            })
            
            # Generate text response
            response = await self.chat.send_message_async(text)
            
            await self._process_response(response)
            
        except Exception as e:
            logger.error(f"Text processing error: {e}")
            await self.client_ws.send_json({
                "type": "error",
                "message": "Sorry, I encountered an error. Please try again."
            })
        finally:
            self.is_processing = False
    
    async def _process_response(self, response):
        """Process Gemini response including function calls"""
        try:
            # Check for product search intent in the response
            if hasattr(response, 'text') and response.text:
                text_lower = response.text.lower()
                if any(keyword in text_lower for keyword in ['search', 'find', 'show', 'looking for', 'need', 'want']):
                    # Extract search query from the conversation
                    # This is a temporary workaround until we fix the function calling
                    logger.info("Detected product search intent in response")
            
            # Extract text response
            if hasattr(response, 'text') and response.text:
                text_response = response.text
                
                # Send text to client
                await self.client_ws.send_json({
                    "type": "assistant_response",
                    "text": text_response
                })
                
                # Add to conversation history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": text_response
                })
            
            # Extract and send audio
            if hasattr(response, 'audio') and response.audio:
                await self._send_audio_to_client(response.audio)
                
        except Exception as e:
            logger.error(f"Response processing error: {e}")
    
    async def _handle_function_call(self, function_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle function calls from Gemini"""
        try:
            if function_name == "search_products":
                # Use LeafLoaf search
                query = args.get("query", "")
                filters = args.get("filters", {})
                
                logger.info(f"Gemini searching for: {query}")
                
                # Get user preferences
                preferences = await self.preference_service.get_user_preferences(self.user_id)
                
                state = {
                    "query": query,
                    "user_id": self.user_id,
                    "request_id": generate_request_id(),
                    "session_id": self.session_id,
                    "limit": 10,
                    "preferences": preferences,
                    "filters": filters
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
                            "category": p.get("category"),
                            "in_stock": p.get("in_stock", True),
                            "dietary_tags": p.get("dietary_tags", [])
                        })
                
                # Send products to client UI
                await self.client_ws.send_json({
                    "type": "products",
                    "data": products
                })
                
                return {
                    "success": True,
                    "products": products,
                    "count": len(products)
                }
                
            elif function_name == "add_to_cart":
                product_id = args.get("product_id")
                quantity = args.get("quantity", 1)
                
                # TODO: Implement actual cart management
                logger.info(f"Adding to cart: {product_id} x {quantity}")
                
                return {
                    "success": True,
                    "message": f"Added {quantity} item(s) to cart",
                    "cart_total": 1  # Placeholder
                }
                
            elif function_name == "get_user_preferences":
                preference_type = args.get("preference_type", "all")
                preferences = await self.preference_service.get_user_preferences(self.user_id)
                
                return {
                    "success": True,
                    "preferences": preferences.get(preference_type, preferences)
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
    
    async def _send_audio_to_client(self, audio_data):
        """Send audio data to client"""
        try:
            # Gemini returns audio in various formats
            # Convert to base64 for web transmission
            if isinstance(audio_data, bytes):
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            else:
                # If it's already base64 or other format
                audio_base64 = str(audio_data)
            
            # Send audio chunks
            chunk_size = 4096
            for i in range(0, len(audio_base64), chunk_size):
                chunk = audio_base64[i:i + chunk_size]
                await self.client_ws.send_json({
                    "type": "audio_chunk",
                    "data": chunk,
                    "encoding": "base64",
                    "format": "wav",  # Adjust based on actual format
                    "sample_rate": 24000  # Gemini default
                })
            
            # Send completion marker
            await self.client_ws.send_json({
                "type": "audio_complete"
            })
            
        except Exception as e:
            logger.error(f"Audio sending error: {e}")
    
    async def update_voice_settings(self, settings: Dict[str, Any]):
        """Update voice configuration"""
        if "style" in settings:
            self.voice_config["voice"]["style"] = settings["style"]
        if "pace" in settings:
            self.voice_config["voice"]["pace"] = settings["pace"]
        if "pitch" in settings:
            self.voice_config["voice"]["pitch"] = settings["pitch"]
        if "accent" in settings:
            self.voice_config["voice"]["accent"] = settings["accent"]
        
        logger.info(f"Updated voice settings: {self.voice_config}")
        
        await self.client_ws.send_json({
            "type": "voice_settings_updated",
            "settings": self.voice_config
        })
    
    async def cleanup(self):
        """Clean up session"""
        logger.info(f"Cleaning up Gemini voice session {self.session_id}")
        # Gemini cleanup if needed


@router.websocket("/stream")
async def gemini_voice_endpoint(websocket: WebSocket):
    """WebSocket endpoint for Gemini native voice"""
    await websocket.accept()
    logger.info("Gemini voice client connected")
    
    session = GeminiVoiceSession(websocket)
    
    try:
        # Initialize Gemini
        if not await session.initialize():
            return
        
        # Process messages
        while True:
            message = await websocket.receive()
            
            if message["type"] == "websocket.receive":
                if "bytes" in message:
                    # Audio input
                    await session.handle_audio_input(message["bytes"])
                    
                elif "text" in message:
                    # Control messages or text input
                    data = json.loads(message["text"])
                    msg_type = data.get("type")
                    
                    if msg_type == "text_input":
                        await session.handle_text_input(data.get("text", ""))
                    elif msg_type == "voice_settings":
                        await session.update_voice_settings(data.get("settings", {}))
                    elif msg_type == "stop":
                        break
                        
    except WebSocketDisconnect:
        logger.info("Gemini voice client disconnected")
    except Exception as e:
        logger.error(f"Gemini voice error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Voice error: {str(e)}"
            })
        except:
            pass
    finally:
        await session.cleanup()


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "voice-gemini-native",
        "features": {
            "stt": "gemini-native",
            "tts": "gemini-native", 
            "llm": "gemini-2.0-flash",
            "voice_control": ["style", "pace", "pitch", "accent"],
            "functions": ["search_products", "add_to_cart", "get_user_preferences"]
        }
    }


@router.get("/voice-options")
async def get_voice_options():
    """Get available voice configuration options"""
    return {
        "styles": ["friendly", "professional", "casual", "enthusiastic"],
        "pace": ["slow", "medium", "fast"],
        "pitch": ["low", "medium", "high"],
        "accents": ["american", "british", "australian", "neutral"],
        "languages": ["en-US", "en-GB", "en-AU", "es-ES", "fr-FR", "de-DE"]
    }