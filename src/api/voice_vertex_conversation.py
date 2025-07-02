"""
Vertex AI Conversation - Next-gen conversational AI
Uses Vertex AI Agent Builder for advanced dialogue management
"""
import asyncio
import json
import base64
import uuid
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog
from google.cloud import discoveryengine_v1 as discoveryengine
from google.cloud import speech_v1
from google.cloud import texttospeech_v1
from vertexai.language_models import ChatModel
import vertexai
import os

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice/vertex-conversation")

# Configuration
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "leafloafai")
LOCATION = os.getenv("GCP_LOCATION", "us-central1")
DATA_STORE_ID = os.getenv("VERTEX_DATASTORE_ID", "")  # For product catalog

class VertexConversation:
    """Advanced conversation using Vertex AI Agent Builder"""
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.session_id = str(uuid.uuid4())
        self.language_code = "en-US"
        
        # Initialize Vertex AI
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        
        # Initialize clients
        self.stt_client = speech_v1.SpeechClient()
        self.tts_client = texttospeech_v1.TextToSpeechClient()
        
        # Initialize conversation model
        self.chat_model = ChatModel.from_pretrained("chat-bison@002")
        self.chat = self.chat_model.start_chat(
            context="""You are LeafLoaf, an expert grocery shopping assistant.
            
Your capabilities:
- Search for products with detailed information
- Provide personalized recommendations
- Manage shopping cart and orders
- Answer questions about nutrition, recipes, and cooking
- Remember user preferences and shopping patterns

Guidelines:
- Be concise and conversational
- Focus on helping users find the best products
- Suggest alternatives when items aren't available
- Consider dietary restrictions and preferences
- Provide price-conscious recommendations

Current session: {session_id}
Language: {language}""".format(
                session_id=self.session_id,
                language=self.language_code
            )
        )
        
        # Product search client (if using Vertex AI Search)
        if DATA_STORE_ID:
            self.search_client = discoveryengine.SearchServiceClient()
            self.search_path = self.search_client.serving_config_path(
                project=PROJECT_ID,
                location="global",
                data_store=DATA_STORE_ID,
                serving_config="default_config"
            )
        else:
            self.search_client = None
            
        # Conversation context
        self.context = {
            "cart_items": [],
            "preferences": {},
            "search_history": []
        }
        
    async def handle_connection(self):
        """Main WebSocket handler"""
        await self.websocket.accept()
        logger.info(f"Vertex AI conversation started: {self.session_id}")
        
        await self.websocket.send_json({
            "type": "connected",
            "session_id": self.session_id,
            "message": "Welcome to LeafLoaf! I'm your AI shopping assistant."
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
        elif msg_type == "context":
            # Update context (user preferences, location, etc.)
            self.context.update(data.get("context", {}))
        elif msg_type == "language":
            self.language_code = data.get("code", "en-US")
            
    async def process_audio(self, audio_data: bytes):
        """Process audio through STT → Vertex AI → TTS"""
        try:
            # 1. Speech-to-Text with streaming
            config = speech_v1.RecognitionConfig(
                encoding=speech_v1.RecognitionConfig.AudioEncoding.WEBM_OPUS,
                sample_rate_hertz=48000,
                language_code=self.language_code,
                enable_automatic_punctuation=True,
                model="latest_long",
                use_enhanced=True,
                # Enable speaker diarization for multi-speaker scenarios
                enable_speaker_diarization=True,
                diarization_speaker_count=2
            )
            
            audio = speech_v1.RecognitionAudio(content=audio_data)
            response = self.stt_client.recognize(config=config, audio=audio)
            
            if not response.results:
                return
                
            result = response.results[0]
            transcript = result.alternatives[0].transcript
            confidence = result.alternatives[0].confidence
            
            # Extract voice characteristics
            voice_metadata = {
                "confidence": confidence,
                "language": self.language_code,
                "stability": result.stability if hasattr(result, 'stability') else 1.0
            }
            
            await self.websocket.send_json({
                "type": "transcript",
                "text": transcript,
                "metadata": voice_metadata
            })
            
            # 2. Process with Vertex AI
            await self.process_with_ai(transcript, voice_metadata)
            
        except Exception as e:
            logger.error(f"Audio processing error: {e}")
            await self.websocket.send_json({
                "type": "error",
                "message": "Audio processing error"
            })
            
    async def process_text(self, text: str, voice_metadata: dict = None):
        """Process text through Vertex AI"""
        await self.process_with_ai(text, voice_metadata or {})
        
    async def process_with_ai(self, text: str, metadata: dict):
        """Process user input with Vertex AI"""
        try:
            # Add to context
            self.context["last_input"] = text
            
            # Detect intent using the chat model
            intent_prompt = f"""Analyze this user input and determine the intent:
User said: "{text}"

Possible intents:
- search_product: User wants to find specific products
- add_to_cart: User wants to add items to cart
- view_cart: User wants to see their cart
- checkout: User wants to complete order
- ask_nutrition: User asks about nutrition/dietary info
- ask_recipe: User asks for recipe suggestions
- general_chat: General conversation
- preference_update: User mentions dietary preferences

Return ONLY the intent name."""

            intent_response = await self.chat.send_message_async(intent_prompt)
            intent = intent_response.text.strip().lower()
            
            # Process based on intent
            if intent == "search_product":
                await self.handle_product_search(text)
            elif intent == "add_to_cart":
                await self.handle_add_to_cart(text)
            elif intent == "view_cart":
                await self.handle_view_cart()
            elif intent == "ask_nutrition":
                await self.handle_nutrition_query(text)
            elif intent == "ask_recipe":
                await self.handle_recipe_query(text)
            elif intent == "preference_update":
                await self.handle_preference_update(text)
            else:
                # General conversation
                response = await self.chat.send_message_async(text)
                await self.send_response(response.text)
                
        except Exception as e:
            logger.error(f"AI processing error: {e}")
            await self.send_response("I'm having trouble understanding. Could you rephrase that?")
            
    async def handle_product_search(self, query: str):
        """Enhanced product search with Vertex AI"""
        try:
            # Extract search parameters using AI
            extract_prompt = f"""Extract product search parameters from: "{query}"
Return as JSON with fields: product, category, brand, dietary_restrictions, price_range"""

            extraction = await self.chat.send_message_async(extract_prompt)
            
            try:
                search_params = json.loads(extraction.text)
            except:
                search_params = {"product": query}
            
            # Use Vertex AI Search if available
            if self.search_client and DATA_STORE_ID:
                products = await self.vertex_ai_search(search_params)
            else:
                # Fallback to existing search
                products = await self.langgraph_search(query)
            
            if products:
                # Generate natural response
                response_prompt = f"""Create a natural response for finding these products:
Query: {query}
Found: {len(products)} products
Top 3: {json.dumps(products[:3], indent=2)}

Make it conversational and helpful. Mention top options with prices."""

                response = await self.chat.send_message_async(response_prompt)
                await self.send_response(response.text, products=products)
            else:
                await self.send_response(f"I couldn't find any {query}. Would you like me to search for alternatives?")
                
        except Exception as e:
            logger.error(f"Search error: {e}")
            await self.send_response("I had trouble searching. Could you try again?")
            
    async def vertex_ai_search(self, params: dict) -> List[dict]:
        """Search using Vertex AI Search"""
        try:
            request = discoveryengine.SearchRequest(
                serving_config=self.search_path,
                query=params.get("product", ""),
                filter=self._build_search_filter(params),
                page_size=10
            )
            
            response = self.search_client.search(request)
            
            products = []
            for result in response.results:
                doc = result.document
                products.append({
                    "id": doc.id,
                    "name": doc.struct_data.get("name"),
                    "price": doc.struct_data.get("price"),
                    "category": doc.struct_data.get("category"),
                    "description": doc.struct_data.get("description"),
                    "in_stock": doc.struct_data.get("in_stock", True)
                })
                
            return products
            
        except Exception as e:
            logger.error(f"Vertex AI Search error: {e}")
            return []
            
    async def langgraph_search(self, query: str) -> List[dict]:
        """Fallback to existing LangGraph search"""
        from src.core.graph import search_graph
        from src.utils.id_generator import generate_request_id
        
        initial_state = {
            "query": query,
            "user_id": f"vertex_{self.session_id}",
            "request_id": generate_request_id(),
            "limit": 10,
            "source": "vertex_ai"
        }
        
        result = await search_graph.ainvoke(initial_state)
        return result.get("search_results", [])
        
    async def handle_add_to_cart(self, text: str):
        """Add items to cart with AI understanding"""
        # Extract item and quantity
        extract_prompt = f"""Extract from: "{text}"
What product and quantity to add to cart?
Return as: {{"product": "...", "quantity": 1}}"""

        extraction = await self.chat.send_message_async(extract_prompt)
        
        try:
            item_info = json.loads(extraction.text)
            self.context["cart_items"].append(item_info)
            
            response = f"Added {item_info['quantity']} {item_info['product']} to your cart. You now have {len(self.context['cart_items'])} items."
            await self.send_response(response)
        except:
            await self.send_response("I couldn't understand what to add. Could you specify the product and quantity?")
            
    async def handle_view_cart(self):
        """Show cart contents"""
        if not self.context["cart_items"]:
            await self.send_response("Your cart is empty. What would you like to shop for today?")
        else:
            cart_summary = "Your cart contains:\n"
            for item in self.context["cart_items"]:
                cart_summary += f"- {item['quantity']} {item['product']}\n"
            
            await self.send_response(cart_summary)
            
    async def handle_nutrition_query(self, query: str):
        """Answer nutrition questions"""
        response = await self.chat.send_message_async(
            f"Answer this nutrition question as a helpful grocery assistant: {query}"
        )
        await self.send_response(response.text)
        
    async def handle_recipe_query(self, query: str):
        """Suggest recipes and ingredients"""
        response = await self.chat.send_message_async(
            f"Suggest a recipe and list ingredients for: {query}. Format as a shopping list."
        )
        await self.send_response(response.text)
        
    async def handle_preference_update(self, text: str):
        """Update user preferences"""
        extract_prompt = f"""Extract dietary preferences from: "{text}"
Examples: vegan, gluten-free, nut allergy, low sodium, organic only"""

        preferences = await self.chat.send_message_async(extract_prompt)
        self.context["preferences"]["dietary"] = preferences.text
        
        await self.send_response(f"I've noted your preferences: {preferences.text}. I'll keep these in mind for future recommendations.")
        
    async def send_response(self, text: str, products: list = None):
        """Send response with TTS"""
        # Send text response
        await self.websocket.send_json({
            "type": "response",
            "text": text,
            "products": products or [],
            "context": {
                "cart_count": len(self.context["cart_items"]),
                "has_preferences": bool(self.context["preferences"])
            }
        })
        
        # Generate neural TTS
        synthesis_input = texttospeech_v1.SynthesisInput(text=text)
        
        # Use WaveNet or Neural2 voices for better quality
        voice = texttospeech_v1.VoiceSelectionParams(
            language_code=self.language_code,
            name=f"{self.language_code}-Neural2-F",  # High quality neural voice
            ssml_gender=texttospeech_v1.SsmlVoiceGender.FEMALE
        )
        
        audio_config = texttospeech_v1.AudioConfig(
            audio_encoding=texttospeech_v1.AudioEncoding.MP3,
            speaking_rate=1.0,
            pitch=0.0,
            volume_gain_db=0.0,
            effects_profile_id=["telephony-class-application"]  # Optimized for conversation
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
        
    def _build_search_filter(self, params: dict) -> str:
        """Build search filter for Vertex AI Search"""
        filters = []
        
        if params.get("category"):
            filters.append(f'category: "{params["category"]}"')
            
        if params.get("brand"):
            filters.append(f'brand: "{params["brand"]}"')
            
        if params.get("dietary_restrictions"):
            for restriction in params["dietary_restrictions"].split(","):
                filters.append(f'dietary_tags: "{restriction.strip()}"')
                
        if params.get("price_range"):
            # Parse price range like "under 10" or "5-15"
            pass
            
        return " AND ".join(filters) if filters else ""

@router.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for Vertex AI conversation"""
    conversation = VertexConversation(websocket)
    await conversation.handle_connection()

@router.get("/health")
async def health_check():
    """Check service health"""
    return {
        "status": "healthy",
        "service": "vertex-ai-conversation",
        "features": {
            "stt": "Google Cloud Speech-to-Text v1",
            "tts": "Google Cloud Text-to-Speech v1 (Neural2)",
            "ai": "Vertex AI Chat (Bison)",
            "search": "Vertex AI Search" if DATA_STORE_ID else "LangGraph",
            "languages": ["en-US", "es-US", "fr-FR", "de-DE", "ja-JP", "ko-KR", "zh-CN"]
        },
        "config": {
            "project_id": PROJECT_ID,
            "location": LOCATION,
            "datastore_configured": bool(DATA_STORE_ID)
        }
    }