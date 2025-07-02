"""
Google Dialogflow CX + Vertex AI Conversation Implementation
Modern conversational AI with built-in NLU and dialogue management
"""
import asyncio
import json
import base64
import uuid
from typing import Optional, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog
from google.cloud import dialogflow_v2 as dialogflow
from google.cloud import speech_v1
from google.cloud import texttospeech_v1
import os

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice/dialogflow")

# Configuration
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "leafloafai")
LOCATION = os.getenv("GCP_LOCATION", "us-central1")
AGENT_ID = os.getenv("DIALOGFLOW_AGENT_ID", "")  # You'll need to create this

class DialogflowConversation:
    """Manages conversation using Dialogflow CX"""
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.session_id = str(uuid.uuid4())
        self.language_code = "en-US"
        
        # Initialize clients
        self.session_client = dialogflow.SessionsClient()
        self.stt_client = speech_v1.SpeechClient()
        self.tts_client = texttospeech_v1.TextToSpeechClient()
        
        # Session path (Dialogflow v2 doesn't use location/agent params)
        self.session_path = self.session_client.session_path(
            project=PROJECT_ID,
            session=self.session_id
        )
        
        # Audio configuration
        self.audio_config = speech_v1.RecognitionConfig(
            encoding=speech_v1.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            sample_rate_hertz=48000,
            language_code=self.language_code,
            enable_automatic_punctuation=True,
            model="latest_long"
        )
        
    async def handle_connection(self):
        """Main WebSocket handler"""
        await self.websocket.accept()
        logger.info(f"Dialogflow session started: {self.session_id}")
        
        await self.websocket.send_json({
            "type": "connected",
            "session_id": self.session_id,
            "message": "Connected to LeafLoaf AI Assistant"
        })
        
        try:
            while True:
                message = await self.websocket.receive()
                
                if message["type"] == "websocket.receive":
                    if "bytes" in message:
                        await self.process_audio(message["bytes"])
                    elif "text" in message:
                        data = json.loads(message["text"])
                        await self.handle_message(data)
                        
        except WebSocketDisconnect:
            logger.info(f"Session ended: {self.session_id}")
        except Exception as e:
            logger.error(f"Session error: {e}")
            
    async def handle_message(self, data: dict):
        """Handle control messages"""
        msg_type = data.get("type")
        
        if msg_type == "text":
            await self.process_text(data.get("text", ""))
        elif msg_type == "language":
            self.language_code = data.get("code", "en-US")
            await self.websocket.send_json({
                "type": "language_changed",
                "language": self.language_code
            })
            
    async def process_audio(self, audio_data: bytes):
        """Process audio through STT → Dialogflow → TTS"""
        try:
            # 1. Speech-to-Text
            audio = speech_v1.RecognitionAudio(content=audio_data)
            response = self.stt_client.recognize(
                config=self.audio_config, 
                audio=audio
            )
            
            if not response.results:
                return
                
            transcript = response.results[0].alternatives[0].transcript
            confidence = response.results[0].alternatives[0].confidence
            
            await self.websocket.send_json({
                "type": "transcript",
                "text": transcript,
                "confidence": confidence
            })
            
            # 2. Process with Dialogflow
            await self.process_text(transcript)
            
        except Exception as e:
            logger.error(f"Audio processing error: {e}")
            await self.websocket.send_json({
                "type": "error",
                "message": "Audio processing error"
            })
            
    async def process_text(self, text: str):
        """Process text through Dialogflow CX"""
        try:
            # Create text input
            text_input = dialogflow.TextInput(text=text)
            query_input = dialogflow.QueryInput(
                text=text_input,
                language_code=self.language_code
            )
            
            # Detect intent
            request = dialogflow.DetectIntentRequest(
                session=self.session_path,
                query_input=query_input
            )
            
            response = self.session_client.detect_intent(request=request)
            query_result = response.query_result
            
            # Extract intent and parameters
            intent_name = query_result.intent.display_name if query_result.intent else "unknown"
            parameters = dict(query_result.parameters) if query_result.parameters else {}
            
            # Send intent info
            await self.websocket.send_json({
                "type": "intent",
                "name": intent_name,
                "parameters": parameters,
                "confidence": query_result.intent_detection_confidence
            })
            
            # Process based on intent
            if intent_name == "product.search":
                await self.handle_product_search(parameters)
            elif intent_name == "order.add":
                await self.handle_add_to_cart(parameters)
            elif intent_name == "order.view":
                await self.handle_view_cart()
            else:
                # Send Dialogflow response
                response_text = query_result.response_messages[0].text.text[0]
                await self.send_response(response_text)
                
        except Exception as e:
            logger.error(f"Dialogflow error: {e}")
            await self.send_response("I'm having trouble understanding. Could you try again?")
            
    async def handle_product_search(self, parameters: dict):
        """Handle product search intent"""
        product = parameters.get("product", "")
        category = parameters.get("category", "")
        
        # Here you would integrate with your existing search
        # For now, we'll use a simple response
        search_query = product or category
        
        if search_query:
            # Import your existing search functionality
            from src.core.graph import search_graph
            from src.utils.id_generator import generate_request_id
            
            initial_state = {
                "query": search_query,
                "user_id": f"dialogflow_{self.session_id}",
                "request_id": generate_request_id(),
                "limit": 5,
                "source": "dialogflow"
            }
            
            # Execute search
            result = await search_graph.ainvoke(initial_state)
            
            if result.get("search_results"):
                products = result["search_results"][:3]
                response = f"I found {len(result['search_results'])} options for {search_query}. "
                response += "Top picks: " + ", ".join([
                    f"{p['name']} at ${p['price']:.2f}" 
                    for p in products
                ])
                await self.send_response(response, products=products)
            else:
                await self.send_response(f"I couldn't find any {search_query}. Try something else?")
        else:
            await self.send_response("What product are you looking for?")
            
    async def handle_add_to_cart(self, parameters: dict):
        """Handle add to cart intent"""
        product = parameters.get("product", "")
        quantity = parameters.get("quantity", 1)
        
        response = f"I'll add {quantity} {product} to your cart."
        await self.send_response(response)
        
    async def handle_view_cart(self):
        """Handle view cart intent"""
        # This would integrate with your order agent
        response = "Your cart is currently empty. What would you like to add?"
        await self.send_response(response)
        
    async def send_response(self, text: str, products: list = None):
        """Send response with optional TTS"""
        # Send text response
        await self.websocket.send_json({
            "type": "response",
            "text": text,
            "products": products or []
        })
        
        # Generate TTS
        synthesis_input = texttospeech_v1.SynthesisInput(text=text)
        voice = texttospeech_v1.VoiceSelectionParams(
            language_code=self.language_code,
            ssml_gender=texttospeech_v1.SsmlVoiceGender.NEUTRAL
        )
        audio_config = texttospeech_v1.AudioConfig(
            audio_encoding=texttospeech_v1.AudioEncoding.MP3
        )
        
        response = self.tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        # Send audio
        await self.websocket.send_json({
            "type": "audio",
            "data": base64.b64encode(response.audio_content).decode(),
            "format": "mp3"
        })

@router.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for Dialogflow conversation"""
    conversation = DialogflowConversation(websocket)
    await conversation.handle_connection()

@router.get("/setup")
async def setup_info():
    """Get setup information for Dialogflow"""
    return {
        "instructions": {
            "1": "Create a Dialogflow CX agent in Google Cloud Console",
            "2": "Set up intents: product.search, order.add, order.view, etc.",
            "3": "Add entities: @product, @category, @quantity",
            "4": "Set DIALOGFLOW_AGENT_ID environment variable",
            "5": "Enable required APIs: Dialogflow, Speech-to-Text, Text-to-Speech"
        },
        "current_config": {
            "project_id": PROJECT_ID,
            "location": LOCATION,
            "agent_configured": bool(AGENT_ID)
        },
        "example_intents": [
            {
                "name": "product.search",
                "training_phrases": [
                    "I need [milk]@product",
                    "Show me [organic]@category products",
                    "Find [bananas]@product"
                ],
                "parameters": ["product", "category"]
            },
            {
                "name": "order.add",
                "training_phrases": [
                    "Add [2]@quantity [apples]@product to cart",
                    "Put [milk]@product in my basket"
                ],
                "parameters": ["product", "quantity"]
            }
        ]
    }