"""
Real-time conversational voice API using WebSockets
Continuous streaming for natural conversation flow
"""
import asyncio
import json
import uuid
import time
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog

from src.voice.deepgram_sdk_client import DeepgramSDKClient
from src.core.graph import search_graph
from src.utils.id_generator import generate_request_id
from src.config.settings import settings
from src.config.constants import SEARCH_DEFAULT_LIMIT
from src.config.voice_config import (
    get_stt_config, 
    get_tts_config, 
    get_conversation_config,
    get_acknowledgment_phrase
)
from src.tracing.voice_tracer import (
    trace_voice_request,
    trace_supervisor_analysis,
    trace_search_parameters,
    trace_agent_processing,
    trace_voice_influence,
    trace_final_results
)

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice-streaming")

# Store active sessions
active_sessions: Dict[str, Dict[str, Any]] = {}

class ConversationalSession:
    """Manages a conversational shopping session"""
    
    def __init__(self, session_id: str, user_id: str = "anonymous"):
        self.session_id = session_id
        self.user_id = user_id
        self.start_time = time.time()
        # Get Deepgram API key from environment or settings
        import os
        deepgram_key = (
            settings.deepgram_api_key or 
            os.getenv("DEEPGRAM_API_KEY")
        )
        if not deepgram_key:
            raise ValueError("DEEPGRAM_API_KEY not found in environment or settings")
        self.deepgram_client = DeepgramSDKClient(deepgram_key)
        self.conversation_history = []
        self.current_context = {}
        self.pending_response = ""
        self.is_assistant_speaking = False
        
    async def process_transcript(self, transcript: str) -> Dict[str, Any]:
        """Process user speech and generate response"""
        
        # Don't process if assistant is speaking
        if self.is_assistant_speaking:
            return None
            
        # Start voice tracing
        trace_id = trace_voice_request(
            session_id=self.session_id,
            user_id=self.user_id,
            query=transcript,
            voice_metadata={
                "source": "websocket",
                "conversation_length": len(self.conversation_history),
                "has_context": bool(self.current_context)
            }
        )
        
        # Add to conversation
        self.conversation_history.append({
            "role": "user",
            "content": transcript,
            "timestamp": datetime.utcnow().isoformat(),
            "trace_id": trace_id
        })
        
        # Process through LangGraph to get intent and response
        return await self.process_query(transcript, trace_id)
    
    async def process_query(self, query: str, trace_id: str) -> Dict[str, Any]:
        """Process query through LangGraph with proper routing"""
        
        # Create search state
        initial_state = {
            "messages": [{
                "role": "human",
                "content": query,
                "tool_calls": None,
                "tool_call_id": None
            }],
            "query": query,
            "request_id": generate_request_id(),
            "timestamp": datetime.utcnow(),
            "alpha_value": 0.5,
            "search_strategy": "hybrid",
            "next_action": None,
            "reasoning": [],
            "routing_decision": None,
            "should_search": True,
            "search_params": {
                "limit": 10,
                "source": "voice"
            },
            "search_results": [],
            "search_metadata": {},
            "session_id": self.session_id,
            "user_id": self.user_id,
            "source": "voice",
            "final_response": {},
            "error": None,
            "trace_id": trace_id,
            "voice_metadata": {
                "source": "websocket",
                "conversation_length": len(self.conversation_history),
                "has_context": bool(self.current_context)
            }
        }
        
        try:
            # Execute through LangGraph
            start_time = time.time()
            final_state = await search_graph.ainvoke(initial_state)
            
            # Check if this is general chat
            if final_state.get("is_general_chat") or final_state.get("routing_decision") == "general_chat":
                # Get the response from the response compiler
                final_response = final_state.get("final_response", {})
                response_text = final_response.get("response", "I'm here to help with your grocery shopping!")
                
                # Log processing time
                processing_time_ms = (time.time() - start_time) * 1000
                trace_agent_processing(
                    trace_id,
                    "general_chat",
                    processing_time_ms,
                    {
                        "intent": final_state.get("intent", "general_chat"),
                        "query": query,
                        "confidence": final_state.get("confidence", 0.8)
                    }
                )
                
                # Log final results
                trace_final_results(
                    trace_id,
                    {"products": [], "metadata": {"chat_response": True, "intent": final_state.get("intent")}},
                    processing_time_ms
                )
                
                return {
                    "type": "response",
                    "text": response_text,
                    "is_general_chat": True,
                    "intent": final_state.get("intent"),
                    "trace_id": trace_id
                }
            
            # Otherwise, handle as product search
            products = final_state.get("search_results", [])
            
            # Log processing time
            search_time_ms = (time.time() - start_time) * 1000
            trace_agent_processing(
                trace_id,
                "search_graph",
                search_time_ms,
                {
                    "products_found": len(products),
                    "query": query
                }
            )
            
            if products:
                # Build conversational response
                response_text = self._build_product_response(query, products)
                
                # Log final results
                trace_final_results(
                    trace_id,
                    {"products": products, "metadata": final_state.get("search_metadata", {})},
                    search_time_ms
                )
                
                return {
                    "type": "response",
                    "text": response_text,
                    "products": products[:5],
                    "total_found": len(products),
                    "trace_id": trace_id
                }
            else:
                # Log no results
                trace_final_results(
                    trace_id,
                    {"products": [], "metadata": {"no_results": True}},
                    search_time_ms
                )
                
                return {
                    "type": "response",
                    "text": f"I couldn't find any {query}. Would you like me to search for something else?",
                    "products": [],
                    "trace_id": trace_id
                }
                
        except Exception as e:
            logger.error(f"Query processing error: {e}")
            return {
                "type": "response",
                "text": "I'm having trouble understanding right now. Could you try again?",
                "error": str(e),
                "trace_id": trace_id
            }
    
    def _generate_chat_response(self, query: str, state: Dict[str, Any]) -> str:
        """Generate a natural chat response based on intent"""
        query_lower = query.lower()
        
        # Greetings
        if any(word in query_lower for word in ["hello", "hi", "hey", "good morning", "good afternoon"]):
            responses = [
                "Hello! Welcome to LeafLoaf. What can I help you find today?",
                "Hi there! I'm here to help with your grocery shopping. What are you looking for?",
                "Good to hear from you! What groceries can I help you with today?",
                "Hello! Ready to help you shop. What's on your list today?"
            ]
            import random
            return random.choice(responses)
        
        # How are you
        elif any(phrase in query_lower for phrase in ["how are you", "how's it going", "what's up"]):
            return "I'm doing great, thank you for asking! I'm here to help you find the best groceries. What can I search for you?"
        
        # Thanks
        elif any(word in query_lower for word in ["thank", "thanks", "appreciate"]):
            return "You're very welcome! Is there anything else you'd like to shop for?"
        
        # Goodbye
        elif any(word in query_lower for word in ["bye", "goodbye", "see you", "later"]):
            return "Goodbye! Thanks for shopping with LeafLoaf. Have a great day!"
        
        # Default friendly response
        else:
            return "I'm here to help you with grocery shopping. What would you like me to search for?"
    
    async def search_products(self, query: str) -> Dict[str, Any]:
        """Search for products using LangGraph"""
        
        # Create search state
        initial_state = {
            "messages": [{
                "role": "human",
                "content": query,
                "tool_calls": None,
                "tool_call_id": None
            }],
            "query": query,
            "request_id": generate_request_id(),
            "timestamp": datetime.utcnow(),
            "alpha_value": 0.5,
            "search_strategy": "hybrid",
            "next_action": None,
            "reasoning": [],
            "routing_decision": None,
            "should_search": True,
            "search_params": {
                "limit": 10,
                "source": "voice"
            },
            "search_results": [],
            "search_metadata": {},
            "session_id": self.session_id,
            "user_id": self.user_id,
            "source": "voice",
            "final_response": {},
            "error": None,
            "trace_id": trace_id
        }
        
        try:
            # Log search parameters for tracing
            trace_search_parameters(trace_id, {
                "query": query,
                "alpha": 0.5,
                "limit": 10,
                "source": "voice",
                "voice_influenced": True
            })
            
            # Execute search
            start_time = time.time()
            final_state = await search_graph.ainvoke(initial_state)
            products = final_state.get("search_results", [])
            
            # Log processing time
            search_time_ms = (time.time() - start_time) * 1000
            trace_agent_processing(
                trace_id,
                "search_graph",
                search_time_ms,
                {
                    "products_found": len(products),
                    "query": query
                }
            )
            
            if products:
                # Build conversational response
                response_text = self._build_product_response(query, products)
                
                # Log final results
                trace_final_results(
                    trace_id,
                    {"products": products, "metadata": final_state.get("search_metadata", {})},
                    search_time_ms
                )
                
                return {
                    "type": "response",
                    "text": response_text,
                    "products": products[:5],
                    "total_found": len(products),
                    "trace_id": trace_id
                }
            else:
                # Log no results
                trace_final_results(
                    trace_id,
                    {"products": [], "metadata": {"no_results": True}},
                    search_time_ms
                )
                
                return {
                    "type": "response",
                    "text": f"I couldn't find any {query}. Would you like me to search for something else?",
                    "products": [],
                    "trace_id": trace_id
                }
                
        except Exception as e:
            logger.error(f"Search error: {e}")
            return {
                "type": "response",
                "text": "I'm having trouble searching right now. Could you try again?",
                "error": str(e)
            }
    
    def _build_product_response(self, query: str, products: list) -> str:
        """Build natural conversational response"""
        
        # Check if all organic
        all_organic = all(p.get('is_organic', False) for p in products)
        
        if 'milk' in query.lower() and all_organic:
            response = f"I found {len(products)} milk options. They're all organic varieties. "
        else:
            response = f"I found {len(products)} options for {query}. "
        
        # Describe top products conversationally
        top_products = products[:3]
        
        if len(top_products) == 1:
            p = top_products[0]
            response += f"We have {p['name']} from {p.get('supplier', 'our store')} for ${p['price']:.2f}."
        
        elif len(top_products) == 2:
            response += f"The top choices are {top_products[0]['name']} for ${top_products[0]['price']:.2f} "
            response += f"and {top_products[1]['name']} for ${top_products[1]['price']:.2f}."
        
        elif len(top_products) >= 3:
            response += f"The top picks are: "
            response += f"{top_products[0]['name']} at ${top_products[0]['price']:.2f}, "
            response += f"{top_products[1]['name']} at ${top_products[1]['price']:.2f}, "
            response += f"and {top_products[2]['name']} at ${top_products[2]['price']:.2f}."
        
        if len(products) > 3:
            response += f" I have {len(products) - 3} more options if you'd like to hear them."
        
        return response

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time voice conversation"""
    
    await websocket.accept()
    logger.info(
        "🌐 WebSocket connected",
        session_id=session_id,
        endpoint="voice_streaming",
        timestamp=datetime.now().isoformat()
    )
    
    # Create session
    session = ConversationalSession(session_id)
    active_sessions[session_id] = session
    
    # Create Deepgram WebSocket connection
    deepgram_ws = None
    
    try:
        # Connect to Deepgram streaming
        deepgram_ws = await session.deepgram_client.create_stream_connection()
        
        # Send initial status
        await websocket.send_json({
            "type": "status",
            "message": "Connected! Start speaking...",
            "level": "success"
        })
        
        # Handle messages concurrently
        async def receive_audio():
            """Receive audio from client and forward to Deepgram"""
            while True:
                try:
                    # Receive audio chunk
                    data = await websocket.receive_bytes()
                    
                    # Log audio reception (only occasionally to avoid spam)
                    if len(active_sessions[session_id].conversation_history) % 100 == 0:
                        logger.debug(
                            "🎵 Audio streaming",
                            session_id=session_id,
                            chunk_size=len(data),
                            total_conversations=len(active_sessions[session_id].conversation_history)
                        )
                    
                    # Forward to Deepgram
                    if deepgram_ws and hasattr(deepgram_ws, 'closed') and not deepgram_ws.closed:
                        await deepgram_ws.send(data)
                        
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.error(f"Audio receive error: {e}")
                    break
        
        async def process_deepgram():
            """Process Deepgram responses"""
            while True:
                try:
                    if not deepgram_ws or (hasattr(deepgram_ws, 'closed') and deepgram_ws.closed):
                        break
                        
                    # Receive from Deepgram
                    message = await deepgram_ws.recv()
                    response = json.loads(message)
                    
                    # Handle transcript
                    if response.get("type") == "Results":
                        channel = response.get("channel", {})
                        alternatives = channel.get("alternatives", [])
                        
                        if alternatives:
                            transcript = alternatives[0].get("transcript", "").strip()
                            is_final = response.get("is_final", False)
                            
                            if transcript:
                                # Send transcript to client
                                await websocket.send_json({
                                    "type": "transcript",
                                    "text": transcript,
                                    "is_final": is_final
                                })
                                
                                # Process final transcripts
                                if is_final and len(transcript.split()) > 1:
                                    # Process the query
                                    result = await session.process_transcript(transcript)
                                    
                                    if result:
                                        # Send response
                                        await websocket.send_json(result)
                                        
                                        # Generate TTS
                                        if result.get("text"):
                                            session.is_assistant_speaking = True
                                            
                                            try:
                                                audio_data = await session.deepgram_client.synthesize_speech(
                                                    result["text"]
                                                )
                                                
                                                # Send audio in chunks
                                                chunk_size = 4096
                                                for i in range(0, len(audio_data), chunk_size):
                                                    chunk = audio_data[i:i + chunk_size]
                                                    await websocket.send_bytes(chunk)
                                                    await asyncio.sleep(0.01)  # Small delay
                                                
                                                logger.info(
                                                    "🔊 TTS audio sent",
                                                    session_id=session.session_id,
                                                    text_length=len(result["text"]),
                                                    audio_size=len(audio_data)
                                                )
                                                    
                                            finally:
                                                session.is_assistant_speaking = False
                                
                except Exception as e:
                    logger.error(f"Deepgram processing error: {e}")
                    break
        
        # Run both tasks concurrently
        await asyncio.gather(
            receive_audio(),
            process_deepgram()
        )
        
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": "Connection error occurred"
        })
        
    finally:
        # Cleanup
        if deepgram_ws and hasattr(deepgram_ws, 'closed') and not deepgram_ws.closed:
            await deepgram_ws.close()
            
        if session_id in active_sessions:
            del active_sessions[session_id]
            
        logger.info(
            "👋 WebSocket disconnected",
            session_id=session_id,
            total_conversations=len(session.conversation_history) if session else 0,
            duration_seconds=int(time.time() - session.start_time) if hasattr(session, 'start_time') else 0
        )

async def generate_streaming_tts(websocket: WebSocket, session: ConversationalSession, text: str, conv_config: Dict[str, Any]):
    """Generate TTS audio with word-level streaming for more natural conversation"""
    try:
        # Split text into chunks for streaming
        words = text.split()
        chunk_size = conv_config.get("response_chunk_size", 10)
        
        session.is_assistant_speaking = True
        
        for i in range(0, len(words), chunk_size):
            chunk_words = words[i:i + chunk_size]
            chunk_text = " ".join(chunk_words)
            
            # Add punctuation if missing at chunk boundary
            if i + chunk_size < len(words) and not chunk_text[-1] in '.!?,;':
                chunk_text += ","
            
            try:
                # Generate audio for this chunk
                audio_data = await session.deepgram_client.synthesize_speech(chunk_text)
                
                # Send audio in smaller pieces for smooth playback
                audio_chunk_size = 4096
                for j in range(0, len(audio_data), audio_chunk_size):
                    audio_chunk = audio_data[j:j + audio_chunk_size]
                    await websocket.send_bytes(audio_chunk)
                    await asyncio.sleep(0.01)  # Small delay for smooth streaming
                
                # Send word boundary marker
                await websocket.send_json({
                    "type": "word_boundary",
                    "word_index": i,
                    "words": chunk_words
                })
                
            except Exception as e:
                logger.error(f"TTS chunk generation error: {e}")
                
    except Exception as e:
        logger.error(f"Streaming TTS error: {e}")
    finally:
        session.is_assistant_speaking = False
        
        # Send end of speech marker
        await websocket.send_json({
            "type": "speech_end"
        })

@router.get("/health")
async def streaming_health():
    """Health check for streaming endpoints"""
    return {
        "status": "healthy",
        "active_sessions": len(active_sessions),
        "streaming_enabled": True,
        "endpoints": {
            "websocket": "WS /api/v1/voice-streaming/ws/{session_id}",
            "conversational": "WS /api/v1/voice/websocket/conversational"
        }
    }

@router.get("/config")
async def get_voice_configuration():
    """Get current voice configuration"""
    from src.config.voice_config import get_voice_config
    return get_voice_config()

@router.post("/config")
async def update_voice_configuration(updates: Dict[str, Any]):
    """Update voice configuration parameters"""
    from src.config.voice_config import update_config
    
    results = {}
    for section, params in updates.items():
        if isinstance(params, dict):
            for key, value in params.items():
                try:
                    update_config(section, key, value)
                    results[f"{section}.{key}"] = "updated"
                except Exception as e:
                    results[f"{section}.{key}"] = f"error: {str(e)}"
    
    return {"status": "updated", "results": results}


@router.websocket("/websocket/conversational")
async def conversational_websocket(websocket: WebSocket):
    """TRUE conversational AI endpoint - continuous listening, no push-to-talk"""
    
    await websocket.accept()
    session_id = str(uuid.uuid4())
    logger.info(f"Conversational WebSocket connected: {session_id}")
    
    # Create session
    session = ConversationalSession(session_id)
    active_sessions[session_id] = session
    
    # Create Deepgram WebSocket connection with optimized settings
    deepgram_ws = None
    
    try:
        # Define transcript handler
        async def handle_transcript(data):
            """Handle transcript data from Deepgram"""
            if data.get("event") == "speech_started":
                logger.debug("Speech started")
                return
            elif data.get("event") == "utterance_end":
                logger.debug("Utterance ended")
                return
                
            transcript = data.get("transcript", "")
            is_final = data.get("is_final", False)
            speech_final = data.get("speech_final", False)
            
            if transcript:
                # Send interim transcript
                await websocket.send_json({
                    "type": "interim_transcript",
                    "text": transcript,
                    "is_final": is_final
                })
                
                logger.info(
                    "🎤 Transcript received",
                    session_id=session_id,
                    transcript=transcript,
                    is_final=is_final,
                    speech_final=speech_final
                )
                
                # Process complete utterances
                conv_config = get_conversation_config()
                if speech_final or (is_final and conv_config["streaming_response"]):
                    # Process the query
                    response = await session.process_transcript(transcript)
                    
                    if response:
                        await websocket.send_json(response)
                        
                        # Generate TTS if configured
                        if response.get("text") and conv_config["streaming_response"]:
                            await generate_streaming_tts(
                                websocket,
                                session,
                                response["text"],
                                conv_config
                            )
        
        # Define error handler
        async def handle_error(error):
            """Handle Deepgram errors"""
            logger.error(f"Deepgram error: {error}")
            await websocket.send_json({
                "type": "error",
                "message": f"Speech service error: {error}"
            })
        
        # Start Deepgram live transcription with SDK
        stt_config = get_stt_config()
        success = await session.deepgram_client.start_live_transcription(
            on_transcript=handle_transcript,
            on_error=handle_error,
            options=stt_config
        )
        
        if not success:
            raise Exception("Failed to start Deepgram transcription")
            
        # Send initial status
        await websocket.send_json({
            "type": "deepgram_connected",
            "message": "Ready to listen..."
        })
        
        # Keep the connection alive with periodic silence
        last_audio_time = asyncio.get_event_loop().time()
        
        async def keep_alive():
            """Send periodic silence to keep Deepgram connection alive"""
            while True:
                try:
                    await asyncio.sleep(5)  # Check every 5 seconds
                    current_time = asyncio.get_event_loop().time()
                    if current_time - last_audio_time > 5:  # No audio for 5 seconds
                        if deepgram_ws and not deepgram_ws.closed:
                            # Send 100ms of silence
                            silence = b'\x00' * 1600  # 100ms at 16kHz
                            await deepgram_ws.send(silence)
                            logger.debug("Sent keep-alive silence")
                except Exception as e:
                    logger.error(f"Keep-alive error: {e}")
                    break
        
        keep_alive_task = asyncio.create_task(keep_alive())
        
        # Process audio and responses concurrently
        async def receive_audio():
            """Receive audio from client and forward to Deepgram"""
            while True:
                try:
                    message = await websocket.receive()
                    
                    if message["type"] == "websocket.receive":
                        if "bytes" in message:
                            # Audio data received
                            audio_data = message["bytes"]
                            
                            # Validate audio data
                            if not audio_data or len(audio_data) == 0:
                                logger.warning("Received empty audio data")
                                continue
                                
                            # Log audio details on first chunk and periodically
                            if not hasattr(session, '_audio_logged') or len(session.conversation_history) % 10 == 0:
                                # Check audio format (first few bytes can indicate format)
                                header_info = ""
                                if len(audio_data) >= 4:
                                    header_info = f", header: {audio_data[:4].hex()}"
                                logger.info(f"Audio format check: {len(audio_data)} bytes{header_info}")
                                
                                # Log sample values to understand format
                                if len(audio_data) >= 10:
                                    samples = list(audio_data[:10])
                                    logger.info(f"First 10 bytes: {samples}")
                                
                                session._audio_logged = True
                            
                            logger.debug(f"Received audio data: {len(audio_data)} bytes")
                            
                            if deepgram_ws and not deepgram_ws.closed:
                                try:
                                    # Send raw audio bytes directly
                                    await deepgram_ws.send(audio_data)
                                    logger.debug(f"Forwarded {len(audio_data)} bytes to Deepgram")
                                    
                                    # Update last audio time
                                    nonlocal last_audio_time
                                    last_audio_time = asyncio.get_event_loop().time()
                                except websockets.exceptions.ConnectionClosed as e:
                                    logger.error(f"Deepgram connection closed: {e}")
                                    # Try to reconnect
                                    try:
                                        deepgram_ws = await session.deepgram_client.create_stream_connection()
                                        logger.info("Reconnected to Deepgram")
                                    except Exception as re:
                                        logger.error(f"Failed to reconnect: {re}")
                                        break
                                except Exception as e:
                                    logger.error(f"Failed to forward audio to Deepgram: {e}")
                        elif "text" in message:
                            # Control messages
                            data = json.loads(message["text"])
                            if data.get("type") == "ping":
                                await websocket.send_json({"type": "pong"})
                                
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.error(f"Audio receive error: {e}")
                    break
        
        async def process_deepgram():
            """Process Deepgram transcriptions and generate responses"""
            transcript_buffer = ""
            
            while True:
                try:
                    if not deepgram_ws or deepgram_ws.closed:
                        logger.warning("Deepgram WebSocket is closed")
                        break
                        
                    # Receive from Deepgram with timeout
                    try:
                        msg = await asyncio.wait_for(deepgram_ws.recv(), timeout=30.0)
                    except asyncio.TimeoutError:
                        logger.warning("Deepgram receive timeout - sending keep-alive")
                        # Send keep-alive
                        if deepgram_ws and not deepgram_ws.closed:
                            await deepgram_ws.send(b'\x00' * 160)  # 10ms silence
                        continue
                    
                    if isinstance(msg, str):
                        data = json.loads(msg)
                        
                        if data.get("type") == "Results":
                            channel = data.get("channel", {})
                            alternatives = channel.get("alternatives", [])
                            
                            if alternatives:
                                transcript = alternatives[0].get("transcript", "")
                                is_final = data.get("is_final", False)
                                speech_final = data.get("speech_final", False)
                                
                                if transcript:
                                    # Send interim transcript
                                    await websocket.send_json({
                                        "type": "interim_transcript",
                                        "text": transcript,
                                        "is_final": is_final
                                    })
                                    
                                    logger.info(
                                        "🎤 Transcript received",
                                        session_id=session_id,
                                        transcript=transcript,
                                        is_final=is_final,
                                        length=len(transcript)
                                    )
                                    
                                    if is_final:
                                        transcript_buffer += transcript + " "
                                    
                                    # Get conversation config
                                    conv_config = get_conversation_config()
                                    
                                    # Process based on configuration
                                    should_process = False
                                    
                                    if conv_config["streaming_response"] and is_final and len(transcript_buffer.strip().split()) >= 3:
                                        # Process on final transcripts with enough words for faster response
                                        should_process = True
                                    elif speech_final:
                                        # Always process on speech final
                                        should_process = True
                                        
                                    if should_process and transcript_buffer.strip():
                                        logger.info(
                                            "💬 Processing utterance",
                                            session_id=session_id,
                                            text=transcript_buffer.strip(),
                                            is_final=is_final,
                                            speech_final=speech_final
                                        )
                                        
                                        # Send quick acknowledgment if configured
                                        if conv_config["use_acknowledgments"] and not session.is_assistant_speaking:
                                            ack_phrase = get_acknowledgment_phrase()
                                            if ack_phrase:
                                                await websocket.send_json({
                                                    "type": "acknowledgment",
                                                    "text": ack_phrase
                                                })
                                        
                                        # Process the query
                                        response = await session.process_transcript(
                                            transcript_buffer.strip()
                                        )
                                        
                                        if response:
                                            await websocket.send_json(response)
                                            
                                            # Generate TTS with streaming if configured
                                            if response.get("text") and conv_config["streaming_response"]:
                                                await generate_streaming_tts(
                                                    websocket,
                                                    session,
                                                    response["text"],
                                                    conv_config
                                                )
                                            
                                            logger.info(
                                                "✅ Response sent",
                                                session_id=session_id,
                                                streaming=conv_config["streaming_response"],
                                                trace_id=response.get("trace_id")
                                            )
                                        
                                        if speech_final:
                                            transcript_buffer = ""
                        
                        elif data.get("type") == "Metadata":
                            # Connection metadata
                            logger.debug(f"Deepgram metadata: {data}")
                            
                except Exception as e:
                    logger.error(f"Deepgram processing error: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Transcription error occurred"
                    })
                    break
        
        # Run both tasks concurrently
        await asyncio.gather(
            receive_audio(),
            process_deepgram()
        )
        
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({
            "type": "error", 
            "message": f"Connection error: {str(e)}"
        })
        
    finally:
        # Cleanup
        if 'keep_alive_task' in locals() and keep_alive_task:
            keep_alive_task.cancel()
            
        if deepgram_ws and not deepgram_ws.closed:
            try:
                await deepgram_ws.close()
                logger.info("Deepgram WebSocket closed")
            except Exception as e:
                logger.error(f"Error closing Deepgram WebSocket: {e}")
        
        if session_id in active_sessions:
            del active_sessions[session_id]
            
        logger.info(f"Conversational WebSocket disconnected: {session_id}")