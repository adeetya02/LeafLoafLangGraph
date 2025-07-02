"""
Full conversational AI with Deepgram STT and TTS
Complete implementation following Deepgram documentation
"""
import asyncio
import json
import os
import ssl
import certifi
import base64
import struct
import time
from typing import Optional, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
    SpeakWSOptions,
    SpeakWebSocketEvents,
)
import structlog

# Fix SSL for macOS
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

# Create SSL context with proper certificates
ssl_context = ssl.create_default_context(cafile=certifi.where())

from src.core.graph import search_graph
from src.utils.id_generator import generate_request_id
from src.integrations.gemma_optimized_client import GemmaOptimizedClient
from src.services.transcript_processor import get_transcript_processor
from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel, GenerationConfig
import vertexai

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice-conv")

# Get API key from environment
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "36a821d351939023aabad9beeaa68b391caa124a")

class ConversationalAssistant:
    """Full conversational AI with proper STT and TTS implementation"""
    
    def __init__(self, client_ws: WebSocket, session_id: str = None, user_id: str = None):
        self.client_ws = client_ws
        self.session_id = session_id or generate_request_id()
        self.user_id = user_id or "voice_user"
        
        # Deepgram client for both STT and TTS
        config = DeepgramClientOptions(
            options={
                "keepalive": "true"
            }
        )
        self.deepgram = DeepgramClient(DEEPGRAM_API_KEY, config)
        
        # Connections
        self.tts_connection = None
        self.stt_connection = None
        
        # LLM for generating responses - Use Gemini from Vertex AI
        self.llm = self._initialize_gemini_llm()
        
        # Transcript processor for async sentiment analysis
        self.transcript_processor = get_transcript_processor(DEEPGRAM_API_KEY)
        
        # Conversation state
        self.conversation_history = []
        self.is_processing = False
        self.current_transcript = ""
        self.audio_queue = asyncio.Queue()
        
        # Audio buffer for smooth playback
        self.audio_buffer = bytearray()
        
        # Store the event loop for sync handlers
        self.loop = None
    
    def _initialize_gemini_llm(self):
        """Initialize Gemini from Vertex AI as the conversational LLM"""
        try:
            # Initialize Vertex AI
            project_id = os.getenv("GCP_PROJECT_ID", "leafloafai")
            location = os.getenv("GCP_LOCATION", "us-central1")
            vertexai.init(project=project_id, location=location)
            
            # Define function declarations for Gemini
            search_products_func = {
                "name": "search_products",
                "description": "Search for grocery products in the store",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query for products (e.g., 'organic milk', 'fresh tomatoes')"
                        }
                    },
                    "required": ["query"]
                }
            }
            
            show_categories_func = {
                "name": "show_categories",
                "description": "Show available product categories with examples",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Optional specific category to show",
                            "enum": ["all", "dairy", "produce", "meat", "pantry", "frozen", "beverages", "snacks"]
                        }
                    }
                }
            }
            
            # Create Gemini model with function declarations
            from vertexai.generative_models import Tool, FunctionDeclaration
            
            tools = [
                Tool(
                    function_declarations=[
                        FunctionDeclaration(
                            name=search_products_func["name"],
                            description=search_products_func["description"],
                            parameters=search_products_func["parameters"]
                        ),
                        FunctionDeclaration(
                            name=show_categories_func["name"],
                            description=show_categories_func["description"],
                            parameters=show_categories_func["parameters"]
                        )
                    ]
                )
            ]
            
            model = GenerativeModel(
                model_name="gemini-2.0-flash",  # Gemini 2.0 Flash model
                generation_config=GenerationConfig(
                    temperature=0.7,
                    top_p=0.9,
                    max_output_tokens=500,
                ),
                tools=tools
            )
            
            logger.info("Initialized Gemini 2.0 Flash from Vertex AI with function calling")
            return model
            
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini, falling back to Gemma: {e}")
            # Fallback to existing Gemma
            return GemmaOptimizedClient()
        
    async def initialize(self):
        """Initialize both STT and TTS connections"""
        try:
            logger.info("Starting voice assistant initialization...")
            
            # Store the current event loop
            self.loop = asyncio.get_event_loop()
            
            # Initialize STT first
            logger.info("Initializing STT...")
            success = await self._initialize_stt()
            if not success:
                logger.error("STT initialization failed")
                return False
            logger.info("STT initialized successfully")
                
            # Initialize TTS
            logger.info("Initializing TTS...")
            success = await self._initialize_tts()
            if not success:
                logger.error("TTS initialization failed")
                return False
            logger.info("TTS initialized successfully")
                
            # Send welcome audio
            logger.info("Sending welcome message...")
            await self._speak_welcome()
            
            logger.info("Voice assistant initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"Initialization error: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def _initialize_stt(self) -> bool:
        """Initialize STT connection with Deepgram"""
        try:
            # Create STT WebSocket connection (use websocket, not asyncwebsocket)
            self.stt_connection = self.deepgram.listen.websocket.v("1")
            
            # Register event handlers with correct method names
            self.stt_connection.on(LiveTranscriptionEvents.Open, self._on_stt_open)
            self.stt_connection.on(LiveTranscriptionEvents.Transcript, self._on_transcript)
            self.stt_connection.on(LiveTranscriptionEvents.UtteranceEnd, self._on_utterance_end)
            self.stt_connection.on(LiveTranscriptionEvents.SpeechStarted, self._on_speech_started)
            self.stt_connection.on(LiveTranscriptionEvents.Error, self._on_stt_error)
            self.stt_connection.on(LiveTranscriptionEvents.Close, self._on_stt_close)
            
            # Configure STT options
            stt_options = LiveOptions(
                model="nova-2",
                language="en-US",
                smart_format=True,
                encoding="linear16",
                channels=1,
                sample_rate=16000,
                interim_results=True,
                utterance_end_ms="1000",
                vad_events=True,
                endpointing=300
            )
            
            # Start STT connection
            logger.info("Starting STT connection...")
            logger.info(f"STT options: {stt_options}")
            connection_result = self.stt_connection.start(stt_options)
            if connection_result:
                logger.info("STT connection established successfully")
                return True
            else:
                logger.error("Failed to start STT connection - check if Deepgram API key is valid")
                return False
                
        except Exception as e:
            logger.error(f"STT initialization error: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def _initialize_tts(self) -> bool:
        """Initialize TTS WebSocket connection"""
        try:
            # Create TTS WebSocket connection
            self.tts_connection = self.deepgram.speak.websocket.v("1")
            
            # Register event handlers
            self.tts_connection.on(SpeakWebSocketEvents.Open, self._on_tts_open)
            self.tts_connection.on(SpeakWebSocketEvents.AudioData, self._on_tts_audio)
            self.tts_connection.on(SpeakWebSocketEvents.Metadata, self._on_tts_metadata)
            self.tts_connection.on(SpeakWebSocketEvents.Flushed, self._on_tts_flushed)
            self.tts_connection.on(SpeakWebSocketEvents.Error, self._on_tts_error)
            self.tts_connection.on(SpeakWebSocketEvents.Close, self._on_tts_close)
            
            # Configure TTS options with conversational voice
            tts_options = SpeakWSOptions(
                model="aura-helios-en",  # Most natural/conversational voice
                encoding="linear16",
                sample_rate=16000
            )
            
            # Start TTS connection
            logger.info("Starting TTS connection...")
            connection_result = self.tts_connection.start(tts_options)
            if connection_result:
                logger.info("TTS connection established successfully")
                return True
            else:
                logger.error("Failed to start TTS connection")
                return False
                
        except Exception as e:
            logger.error(f"TTS initialization error: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def _on_tts_open(self, *args, **kwargs):
        """TTS connection opened"""
        logger.info("TTS WebSocket opened")
        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self.client_ws.send_json({
                    "type": "tts_ready",
                    "message": "Voice synthesis ready"
                }),
                self.loop
            )
    
    def _on_tts_audio(self, *args, **kwargs):
        """Handle audio data from TTS"""
        # The audio data is in kwargs['data']
        audio_data = kwargs.get('data')
            
        if audio_data and isinstance(audio_data, bytes):
            logger.info(f"TTS Audio received: {len(audio_data)} bytes")
            # Send audio chunk to client as base64
            # Linear16 is raw PCM data, we need to add WAV header for browser playback
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    self.client_ws.send_json({
                        "type": "audio_chunk",
                        "data": audio_base64,
                        "encoding": "linear16",
                        "sample_rate": 16000
                    }),
                    self.loop
                )
        else:
            logger.warning(f"TTS audio handler called but unexpected data type: {type(audio_data)}")
    
    def _on_tts_metadata(self, *args, **kwargs):
        """Handle TTS metadata"""
        metadata = kwargs.get("metadata")
        logger.debug(f"TTS Metadata: {metadata}")
        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self.client_ws.send_json({
                    "type": "tts_metadata",
                    "data": metadata
                }),
                self.loop
            )
    
    def _on_tts_flushed(self, *args, **kwargs):
        """TTS audio generation complete"""
        logger.info("TTS audio generation complete")
        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self.client_ws.send_json({
                    "type": "audio_complete"
                }),
                self.loop
            )
    
    def _on_tts_error(self, *args, **kwargs):
        """TTS error occurred"""
        error = kwargs.get("error", "Unknown error")
        logger.error(f"TTS error: {error}")
        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self.client_ws.send_json({
                    "type": "tts_error",
                    "error": str(error)
                }),
                self.loop
            )
    
    def _on_tts_close(self, *args, **kwargs):
        """TTS connection closed"""
        logger.info("TTS WebSocket closed")
    
    def _on_stt_open(self, *args, **kwargs):
        """STT connection opened"""
        logger.info("STT WebSocket opened")
        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self.client_ws.send_json({
                    "type": "stt_ready",
                    "message": "Voice recognition ready"
                }),
                self.loop
            )
    
    def _on_speech_started(self, *args, **kwargs):
        """User started speaking"""
        logger.debug("Speech started")
        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self.client_ws.send_json({
                    "type": "user_speaking",
                    "status": "started"
                }),
                self.loop
            )
    
    def _on_transcript(self, *args, **kwargs):
        """Handle transcript from STT with Audio Intelligence"""
        logger.info("=== TRANSCRIPT EVENT CALLED ===")
        logger.info(f"Args: {args}")
        logger.info(f"Kwargs keys: {list(kwargs.keys())}")
        
        result = kwargs.get("result")
        if not result:
            logger.debug("No result in transcript event")
            return
            
        # The result is a LiveResultResponse object, not a dict
        logger.debug(f"Transcript result type: {type(result)}")
        
        # Extract transcript from LiveResultResponse object
        if hasattr(result, 'channel'):
            channel = result.channel
            alternatives = channel.alternatives if hasattr(channel, 'alternatives') else []
        else:
            logger.debug("No channel in result")
            return
        
        if not alternatives:
            logger.debug("No alternatives in transcript result")
            return
            
        # Extract from first alternative
        alternative = alternatives[0]
        transcript = alternative.transcript if hasattr(alternative, 'transcript') else ""
        confidence = alternative.confidence if hasattr(alternative, 'confidence') else 0.0
        
        # Get metadata from result object
        is_final = result.is_final if hasattr(result, 'is_final') else False
        speech_final = result.speech_final if hasattr(result, 'speech_final') else False
        
        logger.debug(f"Transcript: '{transcript}', is_final: {is_final}, speech_final: {speech_final}")
        
        # Note: Audio Intelligence features are not available in WebSocket mode
        # They require using the batch API instead
        
        if transcript:
            # Build response
            response_data = {
                "type": "transcript",
                "text": transcript,
                "confidence": confidence,
                "is_final": is_final,
                "speech_final": speech_final
            }
            
            # Send transcript with intelligence to client
            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    self.client_ws.send_json(response_data),
                    self.loop
                )
            
            # Store final transcript
            if is_final:
                self.current_transcript = transcript
                logger.info(f"User said: {transcript}")
    
    def _on_utterance_end(self, *args, **kwargs):
        """User finished speaking - process and respond"""
        logger.info(f"Utterance ended. Current transcript: '{self.current_transcript}'")
        
        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self.client_ws.send_json({
                    "type": "user_speaking",
                    "status": "ended"
                }),
                self.loop
            )
        
        if self.current_transcript and not self.is_processing:
            logger.info(f"Processing user input: '{self.current_transcript}'")
            asyncio.run_coroutine_threadsafe(
                self._process_user_input(self.current_transcript),
                self.loop
            )
            self.current_transcript = ""
        else:
            logger.warning(f"Not processing - transcript empty or already processing. transcript='{self.current_transcript}', is_processing={self.is_processing}")
    
    def _on_stt_error(self, *args, **kwargs):
        """STT error occurred"""
        error = kwargs.get("error", "Unknown error")
        logger.error(f"STT error: {error}")
        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self.client_ws.send_json({
                    "type": "stt_error",
                    "error": str(error)
                }),
                self.loop
            )
    
    def _on_stt_close(self, *args, **kwargs):
        """STT connection closed"""
        logger.info("STT WebSocket closed")
    
    async def _process_user_input(self, user_input: str):
        """Process user input and generate response"""
        self.is_processing = True
        process_start = time.time()
        
        try:
            # Check if WebSocket is still connected
            if not hasattr(self.client_ws, 'client_state') or str(self.client_ws.client_state) != 'WebSocketState.CONNECTED':
                logger.warning("WebSocket disconnected, stopping processing")
                return
            # Timing point 1: Start
            logger.info(f"[TRACE] Process start for: '{user_input}'")
            
            # Add to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": user_input
            })
            
            # Send processing status
            await self.client_ws.send_json({
                "type": "processing",
                "status": "started"
            })
            
            # Timing point 2: Pre-Gemini
            pre_gemini = time.time()
            logger.info(f"[TRACE] Pre-Gemini setup: {(pre_gemini - process_start)*1000:.0f}ms")
            
            # Use Gemini with function calling to determine action
            response_text = ""
            products = []
            
            # Check if we're using Gemini or Gemma
            if hasattr(self.llm, 'generate_content'):
                # Gemini from Vertex AI - use function calling
                try:
                    logger.info(f"Processing with Gemini function calling: '{user_input}'")
                    
                    # Timing point 3: Gemini call start
                    gemini_start = time.time()
                    
                    # Send message with function calling enabled - use streaming
                    response = await asyncio.to_thread(
                        self.llm.generate_content,
                        user_input,
                        generation_config=GenerationConfig(
                            temperature=0.7,
                            top_p=0.9,
                            max_output_tokens=500,
                        ),
                        stream=False  # Keep non-streaming for function calls
                    )
                    
                    # Timing point 4: Gemini response received
                    gemini_end = time.time()
                    logger.info(f"[TRACE] Gemini call took: {(gemini_end - gemini_start)*1000:.0f}ms")
                    
                    logger.info(f"Gemini response type: {type(response)}")
                    logger.info(f"Response candidates: {len(response.candidates) if hasattr(response, 'candidates') else 'no candidates'}")
                    
                    # Check if Gemini made function calls
                    function_calls_found = False
                    if hasattr(response, 'candidates') and response.candidates:
                        candidate = response.candidates[0]
                        logger.info(f"Candidate content: {candidate.content if hasattr(candidate, 'content') else 'no content'}")
                        
                        # Check for function calls in the candidate's content parts
                        if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                            for part in candidate.content.parts:
                                logger.info(f"Part type: {type(part)}, Part: {part}")
                                if hasattr(part, 'function_call'):
                                    func_call = part.function_call
                                    function_calls_found = True
                                    logger.info(f"Function call found: {func_call.name} with args: {func_call.args}")
                                    
                                    if func_call.name == "search_products":
                                        query = func_call.args.get("query", user_input)
                                        logger.info(f"Searching products for: {query}")
                                        
                                        # Timing point 5: Search start
                                        search_start = time.time()
                                        products = await self._search_products(query)
                                        search_end = time.time()
                                        logger.info(f"[TRACE] Product search took: {(search_end - search_start)*1000:.0f}ms, found {len(products)} products")
                                        
                                        # Timing point 6: Response generation
                                        response_start = time.time()
                                        response_text = await self._generate_product_response(user_input, products)
                                        response_end = time.time()
                                        logger.info(f"[TRACE] Response generation took: {(response_end - response_start)*1000:.0f}ms")
                                        
                                        # Send products to client
                                        if products:
                                            await self.client_ws.send_json({
                                                "type": "products",
                                                "data": products[:5]
                                            })
                                            
                                    elif func_call.name == "show_categories":
                                        category = func_call.args.get("category", "all")
                                        logger.info(f"Showing categories: {category}")
                                        
                                        if category == "all":
                                            # Show samples from multiple categories
                                            categories = ["dairy", "produce", "meat", "pantry"]
                                            all_products = []
                                            
                                            for cat in categories[:3]:
                                                cat_products = await self._search_products(cat)
                                                if cat_products:
                                                    all_products.extend(cat_products[:2])
                                            
                                            products = all_products
                                        else:
                                            # Show specific category
                                            products = await self._search_products(category)
                                        
                                        response_text = await self._generate_category_response(products)
                                        
                                        # Send products to client
                                        if products:
                                            await self.client_ws.send_json({
                                                "type": "products",
                                                "data": products[:6]
                                            })
                    
                    if not function_calls_found:
                        # No function calls, check for regular text response
                        logger.info("No function calls found, using text response")
                        if hasattr(response, 'text') and response.text:
                            response_text = response.text.strip()
                        else:
                            # Fallback to generating response
                            response_text = await self._generate_conversational_response(user_input)
                        
                except Exception as e:
                    logger.error(f"Gemini function calling error: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    
                    # Fallback to intent detection
                    logger.info("Falling back to intent detection")
                    if await self._is_product_search(user_input):
                        products = await self._search_products(user_input)
                        logger.info(f"Search completed with {len(products)} products")
                        # Generate response based on products found
                        response_text = await self._generate_product_response(user_input, products)
                        if products:
                            try:
                                await self.client_ws.send_json({
                                    "type": "products",
                                    "data": products[:5]
                                })
                            except Exception as e:
                                logger.error(f"Error sending products: {e}")
                    else:
                        response_text = await self._generate_conversational_response(user_input)
            else:
                # Gemma fallback - use intent detection
                if await self._is_product_search(user_input):
                    products = await self._search_products(user_input)
                    response_text = await self._generate_product_response(user_input, products)
                    if products:
                        await self.client_ws.send_json({
                            "type": "products",
                            "data": products[:5]
                        })
                else:
                    response_text = await self._generate_conversational_response(user_input)
            
            # Add response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": response_text
            })
            
            # Capture transcript for async processing
            await self.transcript_processor.capture_transcript(
                user_id=self.user_id,
                session_id=self.session_id,
                transcript=user_input,
                response=response_text,
                metadata={
                    "is_product_search": len(products) > 0,
                    "product_count": len(products),
                    "conversation_length": len(self.conversation_history)
                }
            )
            
            # Send response text to client
            try:
                await self.client_ws.send_json({
                    "type": "assistant_response",
                    "text": response_text
                })
            except Exception as e:
                logger.error(f"Error sending response to client: {e}")
                return
            
            # Stream the response for all cases with word-level streaming
            await self._speak_word_streaming(response_text)
            
        except Exception as e:
            logger.error(f"Error processing input: {e}")
            error_response = "I'm sorry, I had trouble processing that. Could you please try again?"
            await self.client_ws.send_json({
                "type": "assistant_response",
                "text": error_response
            })
            await self._speak_streaming(error_response)
            
        finally:
            self.is_processing = False
            try:
                await self.client_ws.send_json({
                    "type": "processing",
                    "status": "completed"
                })
            except Exception as e:
                logger.error(f"Error sending processing complete: {e}")
    
    async def _is_product_search(self, user_input: str) -> bool:
        """Use LLM to determine if user input is asking about products"""
        prompt = f"""You are analyzing a customer's request in a grocery shopping conversation.

Customer said: "{user_input}"

Determine if this is a request to search for specific products or just a general conversation.

Return ONLY one word:
- "SEARCH" if they want to find/buy specific products
- "CHAT" if it's a greeting, general question, or conversation

Examples:
"I need milk" -> SEARCH
"Show me organic apples" -> SEARCH
"What options do I have?" -> CHAT
"Hello" -> CHAT
"How are you?" -> CHAT
"What can you help me with?" -> CHAT

Response:"""

        try:
            if hasattr(self.llm, 'generate_content'):
                # Gemini from Vertex AI
                response = await asyncio.to_thread(
                    self.llm.generate_content, prompt
                )
                intent = response.text.strip().upper()
            else:
                # Gemma fallback
                response = await self.llm.generate_text(prompt)
                intent = response.strip().upper()
                
            logger.info(f"LLM Intent detection: '{user_input}' -> {intent}")
            return intent == "SEARCH"
            
        except Exception as e:
            logger.error(f"Intent detection error: {e}")
            # Fallback to simple keyword detection
            search_keywords = ['find', 'need', 'want', 'looking for', 'buy', 'show']
            return any(keyword in user_input.lower() for keyword in search_keywords)
    
    async def _generate_category_response(self, products: list) -> str:
        """Generate conversational response about categories"""
        if not products:
            return (
                "I can help you find all sorts of groceries! We have fresh produce like fruits and vegetables, "
                "dairy products, meats and seafood, pantry staples, frozen foods, beverages, and snacks. "
                "What are you looking for today?"
            )
        
        # Group products by category
        categories = {}
        for p in products:
            cat = p.get('category', 'Other')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(p)
        
        prompt = f"""You are LeafLoaf, a friendly grocery assistant showing available categories.

Available categories with examples:
{chr(10).join([f"- {cat}: {', '.join([p['name'] for p in prods[:2]])}" for cat, prods in categories.items()])}

Generate a natural response that:
- Mentions the main categories we have
- Gives 1-2 specific examples from what's available
- Asks what they're interested in
- Sounds conversational, not like a list

Keep it to 2-3 sentences."""

        try:
            if hasattr(self.llm, 'generate_content'):
                response = await asyncio.to_thread(
                    self.llm.generate_content, prompt
                )
                return response.text.strip()
            else:
                response = await self.llm.generate_text(prompt)
                return response.strip()
        except Exception as e:
            logger.error(f"Category response generation error: {e}")
            # Fallback response
            return (
                f"I've got great options in {', '.join(list(categories.keys())[:3])}! "
                "What type of groceries are you looking for today?"
            )
    
    async def _search_products(self, query: str) -> list:
        """Search for products using LeafLoaf search with full multi-agent system"""
        try:
            logger.info(f"Searching for products: {query}")
            
            # Use the full search graph with supervisor routing
            from src.core.graph import search_graph
            
            # Import required for proper state creation
            from datetime import datetime
            from src.models.state import SearchStrategy
            
            # Create search state matching the chat API exactly
            request_id = generate_request_id()
            search_state = {
                # Messages for React pattern
                "messages": [{
                    "role": "human",
                    "content": query,
                    "tool_calls": None,
                    "tool_call_id": None
                }],
                
                # Request context
                "query": query,
                "request_id": request_id,
                "timestamp": datetime.utcnow(),
                
                # Search config
                "alpha_value": 0.5,  # Default for voice
                "search_strategy": SearchStrategy.HYBRID,
                
                # Agent state
                "next_action": None,
                "reasoning": [],
                "routing_decision": "product_search",  # Pre-determined by function calling
                "should_search": True,
                "search_params": {
                    "graphiti_mode": None,
                    "show_all": False,
                    "limit": 20,  # Use configured default limit
                    "source": "voice"
                },
                "search_results": [],
                "search_metadata": {},
                "pending_tool_calls": [],
                "completed_tool_calls": [],
                
                # User context
                "session_id": self.session_id,
                "enhanced_query": None,
                "current_order": {"items": []},
                "order_metadata": {},
                "user_context": {
                    "user_id": self.user_id,
                    "filters": {},
                    "preferences": {}
                },
                "preferences": [],
                "filters": {},
                
                # Graphiti personalization
                "user_id": self.user_id,
                "graphiti_mode": None,
                "show_all": False,
                "source": "voice",
                
                # Execution tracking
                "agent_status": {},
                "agent_timings": {},
                "total_execution_time": 0,
                
                # Tracing
                "trace_id": request_id,
                "span_ids": {},
                
                # Control flow
                "should_continue": True,
                "final_response": {},
                "error": None,
                
                # Intent fields
                "intent": "product_search",
                "confidence": 0.9
            }
            
            # Execute search using the full LangGraph system
            result = await search_graph.ainvoke(search_state)
            
            # Extract products from the result - look in final_response like the chat API
            products = []
            if result and isinstance(result, dict):
                # Log the result structure for debugging
                logger.info(f"Search result keys: {list(result.keys())}")
                
                # Get the final response from the state
                final_response = result.get("final_response", {})
                logger.info(f"Final response keys: {list(final_response.keys())}")
                logger.info(f"Final response success: {final_response.get('success')}")
                
                # Check multiple possible locations for products
                product_list = (
                    final_response.get("products", []) or
                    result.get("enhanced_products", []) or 
                    result.get("products", []) or
                    result.get("search_results", [])
                )
                
                logger.info(f"Product list found: {len(product_list)} items")
                
                for p in product_list[:10]:
                    products.append({
                        "name": p.get("product_name", p.get("name", "Unknown")),
                        "price": float(p.get("price", 0)),
                        "unit": p.get("unit", ""),
                        "category": p.get("category", ""),
                        "in_stock": p.get("in_stock", True),
                        # Include personalization data if available
                        "user_preference_score": p.get("user_preference_score", 0),
                        "frequently_bought": p.get("frequently_bought", False),
                        "last_purchased": p.get("last_purchased", None)
                    })
            
            logger.info(f"Found {len(products)} products from search")
            return products
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    async def _generate_product_response_streaming(self, query: str, products: list):
        """Generate and stream product search response with ultra-low latency"""
        if not products:
            response = f"I couldn't find any products matching '{query}'. Would you like me to search for something else?"
            await self._speak_word_streaming(response)
            return response
        
        # Use the new streaming method that combines Gemini streaming + word-level TTS
        response = await self._generate_and_stream_response(
            user_input=query,
            is_search=True,
            products=products
        )
        
        return response
    
    async def _generate_product_response(self, query: str, products: list) -> str:
        """Generate conversational response about products"""
        if not products:
            return (
                f"I couldn't find any products matching '{query}'. "
                "Could you try describing what you're looking for differently? "
                "I can help you find fresh produce, dairy, meats, and pantry items."
            )
        
        # Format product list for LLM
        product_list = []
        for i, p in enumerate(products[:5], 1):
            price_str = f"${p['price']:.2f}"
            stock_str = "in stock" if p.get('in_stock', True) else "out of stock"
            product_list.append(
                f"{i}. {p['name']} - {price_str} {p['unit']} ({stock_str})"
            )
        
        prompt = f"""You are LeafLoaf, a warm and friendly grocery shopping assistant having a natural voice conversation.

Customer asked: "{query}"

Available products:
{chr(10).join(product_list)}

Recent conversation:
{self._format_recent_history(3)}

Generate a natural, conversational response that sounds like a helpful friend, not a robot:
- Use casual language ("I've got", "looks like", "how about")
- Add personality with phrases like "Oh!", "Actually,", "You know what?"
- Mention only top 2-3 products conversationally
- Keep it brief and natural - like you're chatting with a friend

Example style: "Oh, I've got some great options for you! There's Organic Valley milk for $5.99, and Horizon's also really good at $6.49. Want me to grab one of those for you?"

IMPORTANT: Sound human, warm, and conversational - NOT formal or robotic."""

        try:
            # Check if we're using Gemini or Gemma
            if hasattr(self.llm, 'generate_content'):
                # Gemini from Vertex AI
                response = await asyncio.to_thread(
                    self.llm.generate_content, prompt
                )
                return response.text.strip()
            else:
                # Gemma fallback
                response = await self.llm.generate_text(prompt)
                return response.strip()
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            # Fallback response
            return (
                f"I found {len(products)} options for {query}. "
                f"The top choice is {products[0]['name']} at ${products[0]['price']:.2f} {products[0]['unit']}. "
                "Would you like me to add it to your cart?"
            )
    
    async def _generate_conversational_response(self, user_input: str) -> str:
        """Generate general conversational response"""
        prompt = f"""You are LeafLoaf, a warm and friendly grocery shopping assistant having a natural voice chat.

Recent conversation:
{self._format_recent_history(5)}

Customer just said: "{user_input}"

Your role: You help people shop for groceries at LeafLoaf. You can search for any products they need including:
- Fresh produce (fruits, vegetables)
- Dairy products (milk, cheese, yogurt)
- Meats and seafood
- Pantry staples (pasta, rice, canned goods)
- Frozen foods
- Beverages
- Snacks and treats
- Organic and specialty items

Generate a natural, conversational response:
- If they ask about options/categories, tell them what kinds of products you can help find
- If they greet you, greet them warmly and ask how you can help
- If they ask general questions, answer helpfully and guide them
- Keep responses brief (2-3 sentences max)
- Sound like a helpful friend, not a robot

IMPORTANT: Be natural and conversational. Use phrases like "Oh!", "Sure thing!", "You bet!\""""

        try:
            # Check if we're using Gemini or Gemma
            if hasattr(self.llm, 'generate_content'):
                # Gemini from Vertex AI
                response = await asyncio.to_thread(
                    self.llm.generate_content, prompt
                )
                return response.text.strip()
            else:
                # Gemma fallback
                response = await self.llm.generate_text(prompt)
                return response.strip()
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            # Fallback response
            return (
                "I'm here to help with your grocery shopping! "
                "You can ask me about any products, prices, or what's in stock."
            )
    
    async def _generate_and_stream_response(self, user_input: str, is_search: bool = False, products: list = None):
        """Generate and stream response with Gemini streaming + word-level TTS"""
        try:
            # Prepare the prompt based on type
            if is_search and products:
                # Format product list
                product_list = []
                for i, p in enumerate(products[:5], 1):
                    price_str = f"${p['price']:.2f}"
                    stock_str = "in stock" if p.get('in_stock', True) else "out of stock"
                    product_list.append(f"{i}. {p['name']} - {price_str} {p['unit']} ({stock_str})")
                
                prompt = f"""You are LeafLoaf, a friendly grocery assistant. Keep response under 50 words.
Customer asked: "{user_input}"
Products found:
{chr(10).join(product_list)}
Recent: {self._format_recent_history(2)}
Mention top 2-3 products conversationally. Be warm and natural."""
            else:
                prompt = f"""You are LeafLoaf, a friendly grocery assistant. Keep response under 40 words.
Recent: {self._format_recent_history(3)}
Customer: "{user_input}"
Be warm, helpful, natural. Guide them to search for products."""
            
            # Check if Gemini supports streaming
            if hasattr(self.llm, 'generate_content'):
                # Try streaming generation
                try:
                    logger.info("[TRACE] Starting Gemini streaming generation")
                    
                    # Create generation config for streaming
                    generation_config = GenerationConfig(
                        temperature=0.7,
                        max_output_tokens=150,
                        candidate_count=1
                    )
                    
                    # Start streaming generation
                    response_stream = self.llm.generate_content(
                        prompt,
                        generation_config=generation_config,
                        stream=True
                    )
                    
                    # Stream tokens to TTS as they arrive
                    buffer = []
                    full_response = []
                    
                    for chunk in response_stream:
                        if chunk.text:
                            text_chunk = chunk.text
                            full_response.append(text_chunk)
                            
                            # Add to buffer
                            words = text_chunk.split()
                            buffer.extend(words)
                            
                            # Send to TTS when we have enough words
                            if len(buffer) >= 3:
                                phrase = ' '.join(buffer)
                                logger.info(f"[TRACE] Streaming phrase: '{phrase}'")
                                self.tts_connection.send_text(phrase + " ")
                                buffer = []
                                await asyncio.sleep(0.01)  # Tiny delay
                    
                    # Send remaining buffer
                    if buffer:
                        phrase = ' '.join(buffer)
                        logger.info(f"[TRACE] Final phrase: '{phrase}'")
                        self.tts_connection.send_text(phrase)
                    
                    # Flush TTS
                    self.tts_connection.flush()
                    
                    return ''.join(full_response).strip()
                    
                except Exception as e:
                    logger.warning(f"Streaming failed, falling back to regular generation: {e}")
                    # Fall back to non-streaming
                    response = await asyncio.to_thread(
                        self.llm.generate_content, prompt
                    )
                    response_text = response.text.strip()
                    await self._speak_word_streaming(response_text)
                    return response_text
            else:
                # Non-streaming fallback
                response = await self.llm.generate_text(prompt)
                response_text = response.strip()
                await self._speak_word_streaming(response_text)
                return response_text
                
        except Exception as e:
            logger.error(f"Generate and stream error: {e}")
            fallback = "I'm having a bit of trouble. Could you try that again?"
            await self._speak_word_streaming(fallback)
            return fallback
    
    def _format_recent_history(self, num_exchanges: int) -> str:
        """Format recent conversation history"""
        if not self.conversation_history:
            return "No previous conversation"
        
        # Get last N exchanges (2 messages per exchange)
        recent = self.conversation_history[-(num_exchanges * 2):]
        
        formatted = []
        for msg in recent:
            role = "Customer" if msg["role"] == "user" else "LeafLoaf"
            formatted.append(f"{role}: {msg['content']}")
        
        return "\n".join(formatted)
    
    async def _speak(self, text: str):
        """Send text to TTS WebSocket for speech synthesis"""
        try:
            if not self.tts_connection:
                logger.error("TTS connection not established")
                return
            
            # Timing: TTS start
            tts_start = time.time()
            
            # Send text to TTS WebSocket
            logger.info(f"Sending text to TTS: {text[:50]}...")
            self.tts_connection.send_text(text)  # Sync method
            logger.info("Text sent to TTS")
            
            # Flush to ensure all audio is generated
            logger.info("Flushing TTS...")
            self.tts_connection.flush()  # Sync method
            logger.info("TTS flushed")
            
            # Wait for audio to complete
            logger.info("Waiting for TTS audio to complete...")
            await asyncio.sleep(0.1)  # Small delay for processing
            
            tts_end = time.time()
            logger.info(f"[TRACE] TTS _speak took: {(tts_end - tts_start)*1000:.0f}ms")
            logger.info("TTS audio complete")
            
        except Exception as e:
            logger.error(f"TTS speak error: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    async def _speak_streaming(self, text: str):
        """Send text to TTS in chunks for faster perceived response"""
        try:
            if not self.tts_connection:
                logger.error("TTS connection not established")
                return
            
            # Split text into sentences for natural chunking
            import re
            sentences = re.split(r'(?<=[.!?])\s+', text)
            
            tts_start = time.time()
            logger.info(f"[TRACE] Starting streaming TTS with {len(sentences)} chunks")
            
            for i, sentence in enumerate(sentences):
                if sentence.strip():
                    # Send each sentence immediately
                    logger.info(f"[TRACE] Sending chunk {i+1}/{len(sentences)}: {sentence[:30]}...")
                    self.tts_connection.send_text(sentence)
                    
                    # Small delay between chunks for natural flow
                    if i < len(sentences) - 1:
                        await asyncio.sleep(0.05)
            
            # Flush at the end to ensure all audio is generated
            self.tts_connection.flush()
            
            tts_end = time.time()
            logger.info(f"[TRACE] Streaming TTS completed in: {(tts_end - tts_start)*1000:.0f}ms")
            
        except Exception as e:
            logger.error(f"Streaming TTS error: {type(e).__name__}: {e}")
            # Fallback to regular speak
            await self._speak(text)
    
    async def _speak_word_streaming(self, text: str):
        """Send text to TTS word-by-word for ultra-low latency"""
        try:
            if not self.tts_connection:
                logger.error("TTS connection not established")
                return
            
            import re
            tts_start = time.time()
            
            # Strategy: Send small natural phrases (3-5 words) for instant speech
            # This balances between latency and naturalness
            words = text.split()
            buffer = []
            
            logger.info(f"[TRACE] Starting word-level streaming with {len(words)} words")
            
            for i, word in enumerate(words):
                buffer.append(word)
                
                # Send chunk when we hit natural boundaries or size limit
                should_send = False
                
                # Check for natural phrase boundaries
                if word.endswith((',', ';', ':')) or word.endswith(('!', '?', '.')):
                    should_send = True
                # Or if we have 3-5 words (optimal for natural speech)
                elif len(buffer) >= 4:
                    should_send = True
                # Or if it's the last word
                elif i == len(words) - 1:
                    should_send = True
                
                if should_send and buffer:
                    chunk = ' '.join(buffer)
                    logger.info(f"[TRACE] Sending phrase chunk: '{chunk}'")
                    self.tts_connection.send_text(chunk + " ")  # Add space for natural flow
                    buffer = []
                    
                    # Tiny delay for natural pacing (20ms)
                    if i < len(words) - 1:
                        await asyncio.sleep(0.02)
            
            # Send any remaining words
            if buffer:
                chunk = ' '.join(buffer)
                logger.info(f"[TRACE] Sending final chunk: '{chunk}'")
                self.tts_connection.send_text(chunk)
            
            # Flush to ensure all audio is generated
            self.tts_connection.flush()
            
            tts_end = time.time()
            logger.info(f"[TRACE] Word-level streaming completed in: {(tts_end - tts_start)*1000:.0f}ms")
            
        except Exception as e:
            logger.error(f"Word streaming TTS error: {type(e).__name__}: {e}")
            # Fallback to sentence streaming
            await self._speak_streaming(text)
    
    async def _speak_welcome(self):
        """Speak welcome message"""
        welcome_text = (
            "Hey there! I'm LeafLoaf, and I'm here to help with your grocery shopping. "
            "What can I grab for you today?"
        )
        await self._speak_streaming(welcome_text)
        
        # Also send as text
        await self.client_ws.send_json({
            "type": "assistant_response",
            "text": welcome_text
        })
    
    async def handle_client_audio(self, audio_data: bytes):
        """Handle audio data from client"""
        if self.stt_connection:
            # Debug: Log audio data being sent
            logger.debug(f"Sending audio to STT: {len(audio_data)} bytes")
            # The send method is synchronous in the WebSocket SDK
            self.stt_connection.send(audio_data)
        else:
            logger.warning("STT connection not available for audio data")
    
    async def cleanup(self):
        """Clean up all connections"""
        logger.info("Cleaning up conversational assistant")
        
        # Close STT
        if self.stt_connection:
            try:
                self.stt_connection.finish()  # Synchronous method
            except:
                pass
        
        # Close TTS
        if self.tts_connection:
            try:
                self.tts_connection.finish()  # Synchronous method
            except:
                pass


@router.websocket("/stream")
async def conversational_endpoint(websocket: WebSocket):
    """WebSocket endpoint for full conversational AI"""
    await websocket.accept()
    logger.info("Client connected for conversational AI")
    
    assistant = ConversationalAssistant(websocket)
    
    try:
        # Initialize assistant
        logger.info("Initializing voice assistant for new connection...")
        init_result = await assistant.initialize()
        if not init_result:
            logger.error("Voice assistant initialization failed")
            await websocket.send_json({
                "type": "error",
                "message": "Failed to initialize voice assistant - check server logs"
            })
            return
        logger.info("Voice assistant initialized successfully")
        
        # Process messages from client
        while True:
            message = await websocket.receive()
            
            if message["type"] == "websocket.receive":
                if "bytes" in message:
                    # Audio data from client microphone
                    audio_bytes = message["bytes"]
                    logger.debug(f"Received audio from client: {len(audio_bytes)} bytes")
                    await assistant.handle_client_audio(audio_bytes)
                    
                elif "text" in message:
                    # Control messages or text input
                    data = json.loads(message["text"])
                    
                    if data.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                    elif data.get("type") == "stop":
                        break
                    elif data.get("type") == "text_input":
                        # Handle text input for testing function calling
                        text_input = data.get("text", "")
                        if text_input:
                            logger.info(f"Received text input for processing: '{text_input}'")
                            # Simulate transcript by directly processing the text
                            assistant.current_transcript = text_input
                            await assistant._process_user_input(text_input)
                        
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Connection error: {str(e)}"
            })
        except:
            pass
    finally:
        await assistant.cleanup()
        logger.info("Conversational AI session ended")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "voice-conversational-full",
        "features": {
            "stt": True,
            "tts": True,
            "llm": True,
            "search": True,
            "streaming": True,
            "transcript_analysis": True
        }
    }

@router.get("/insights/{user_id}")
async def get_user_insights(user_id: str):
    """Get voice conversation insights for a user"""
    processor = get_transcript_processor(DEEPGRAM_API_KEY)
    insights = await processor.get_user_insights(user_id)
    
    return {
        "user_id": user_id,
        "insights": insights,
        "status": "success"
    }