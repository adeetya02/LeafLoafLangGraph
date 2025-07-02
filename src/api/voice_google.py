"""
Google Cloud Voice Integration
Combines Speech-to-Text and Text-to-Speech with LangGraph
"""
import asyncio
import json
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog

from src.api.voice_google_stt import GoogleSTTHandler
from src.api.voice_google_tts import GoogleTTSHandler
from src.core.graph import search_graph
from src.utils.id_generator import generate_request_id
from src.config.settings import settings

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/google-voice")

class GoogleVoiceSession:
    """Manages a Google Voice conversation session"""
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.session_id = str(uuid.uuid4())
        self.user_id = f"voice_user_{self.session_id[:8]}"
        
        # Initialize STT and TTS handlers
        self.stt = GoogleSTTHandler()
        self.tts = GoogleTTSHandler()
        
        # Conversation state
        self.is_assistant_speaking = False
        self.conversation_history = []
        self.current_language = "en-US"
        self.user_interrupted = False
        self.last_voice_features = {}  # Store user's voice characteristics
        
        # Audio buffer for streaming
        self.audio_buffer = asyncio.Queue()
        
        # Synchronization event to ensure audio is flowing
        self.audio_started = asyncio.Event()
        
    async def handle_connection(self):
        """Main connection handler"""
        await self.websocket.accept()
        logger.info(f"🎤🎤🎤 GOOGLE VOICE SESSION STARTED: {self.session_id} 🎤🎤🎤")
        
        try:
            # Send welcome message
            await self.send_message({
                "type": "session_started",
                "session_id": self.session_id,
                "message": "Connected to Google Voice Assistant"
            })
            
            # Skip welcome audio - let conversation start naturally
            # The system will respond appropriately when user speaks
            
            # Start parallel tasks
            logger.info("Starting parallel tasks: audio reception and STT processing")
            results = await asyncio.gather(
                self.handle_incoming_audio(),
                self.process_speech_recognition(),
                return_exceptions=True
            )
            
            # Check for exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Task {i} failed with exception: {result}")
                    raise result
            
        except WebSocketDisconnect:
            logger.info(f"Voice session ended: {self.session_id}")
        except Exception as e:
            logger.error(f"Voice session error: {e}")
            await self.send_error(str(e))
        finally:
            await self.cleanup()
    
    async def handle_incoming_audio(self):
        """Receive audio chunks from client"""
        try:
            chunk_count = 0
            total_bytes = 0
            while True:
                # Try to receive binary audio data
                try:
                    data = await self.websocket.receive_bytes()
                    chunk_count += 1
                    total_bytes += len(data)
                except Exception:
                    # Maybe it's a JSON message
                    try:
                        text = await self.websocket.receive_text()
                        json_data = json.loads(text)
                        if json_data.get("type") == "language_change":
                            new_lang = json_data.get("language", "en-US")
                            self.current_language = new_lang
                            self.stt.update_language(new_lang)
                            self.tts.set_default_voice(new_lang)
                            logger.info(f"Language changed to: {new_lang}")
                        continue
                    except Exception as e:
                        logger.warning(f"Error handling message: {e}")
                        continue
                
                logger.debug(f"Received audio chunk {chunk_count}: {len(data)} bytes (total: {total_bytes})")
                
                # Add to buffer for STT processing
                await self.audio_buffer.put(data)
                
                # Signal that audio has started flowing
                if chunk_count == 1:
                    self.audio_started.set()
                    logger.info("Audio flow started - signaling STT to begin")
                
                # Log every 50th chunk to monitor flow
                if chunk_count % 50 == 0:
                    logger.info(f"Audio flow: received {chunk_count} chunks, {total_bytes} bytes, buffer size: {self.audio_buffer.qsize()}")
                
                # Check if user is interrupting
                if self.is_assistant_speaking:
                    self.user_interrupted = True
                    
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected after {chunk_count} chunks, {total_bytes} bytes")
        except Exception as e:
            logger.error(f"Audio receive error: {e}")
    
    async def process_speech_recognition(self):
        """Process audio through STT and handle responses"""
        logger.info(f"=== STT Process Started for session {self.session_id} ===")
        
        # Wait for audio to start flowing before beginning STT
        logger.info("Waiting for audio flow to begin...")
        await self.audio_started.wait()
        logger.info("Audio flow confirmed - starting STT processing")
        
        try:
            # Create audio generator from buffer  
            async def audio_generator():
                chunk_count = 0
                while True:
                    # Get audio chunk without timeout - wait indefinitely
                    audio_chunk = await self.audio_buffer.get()
                    if audio_chunk is None:  # Sentinel value to stop
                        logger.info(f"Audio generator stopping after {chunk_count} chunks")
                        break
                    chunk_count += 1
                    if chunk_count % 10 == 1:
                        logger.info(f"Audio generator yielding chunk {chunk_count}: {len(audio_chunk)} bytes")
                    yield audio_chunk
            
            # Process through STT
            logger.info("Starting STT stream recognition...")
            result_count = 0
            async for result in self.stt.stream_recognize(audio_generator()):
                result_count += 1
                logger.info(f"STT result #{result_count}: {result}")
                
                if "error" in result:
                    logger.error(f"STT error: {result['message']}")
                    await self.send_error(result["message"])
                    continue
                
                # Send transcript to client with voice features
                await self.send_message({
                    "type": "transcript",
                    "text": result["transcript"],
                    "is_final": result["is_final"],
                    "confidence": result["confidence"],
                    "language": result.get("language_code", "en-US"),
                    "voice_features": result.get("voice_features", {})
                })
                
                # Process final results
                if result["is_final"] and result["transcript"].strip():
                    # Store voice features for TTS adaptation
                    self.last_voice_features = result.get("voice_features", {})
                    await self.process_user_input(result)
                    
        except Exception as e:
            logger.error(f"STT processing error: {e}")
    
    async def process_user_input(self, stt_result: Dict[str, Any]):
        """Process user input through LangGraph"""
        transcript = stt_result["transcript"]
        confidence = stt_result.get("confidence", 1.0)
        
        # Extract language and voice features
        detected_language = stt_result.get("language_code", "en-US")
        voice_features = stt_result.get("voice_features", {})
        
        # Update TTS language if different from current
        if detected_language != self.current_language:
            self.current_language = detected_language
            self.stt.update_language(detected_language)
            self.tts.set_default_voice(detected_language)
            logger.info(f"Switched to language: {detected_language}")
        
        # Log conversation with full context
        self.conversation_history.append({
            "role": "user",
            "content": transcript,
            "timestamp": datetime.utcnow().isoformat(),
            "confidence": confidence,
            "language": detected_language,
            "voice_features": voice_features
        })
        
        # Let the LLM handle all intents including greetings - no hardcoding
        
        try:
            # Create state for LangGraph
            state = {
                "messages": [{
                    "role": "human",
                    "content": transcript
                }],
                "query": transcript,
                "request_id": generate_request_id(),
                "timestamp": datetime.utcnow(),
                "session_id": self.session_id,
                "user_id": self.user_id,
                "source": "google_voice",
                
                # Voice-specific metadata with full features
                "voice_metadata": {
                    "confidence": confidence,
                    "language": detected_language,
                    "voice_features": voice_features,
                    "speaking_rate": stt_result.get("speaking_rate"),
                    "words": stt_result.get("words", [])
                },
                
                # Standard search state fields
                "search_params": {},
                "current_order": {"items": []},
                "alpha_value": 0.5,
                "search_strategy": "hybrid",
                "routing_decision": None,
                "search_results": [],
                "agent_status": {},
                "should_search": True,
                
                # Voice synthesis requirements for AI-driven decisions
                "voice_synthesis_needed": True,
                "conversation_history": self.conversation_history
            }
            
            # Process through LangGraph
            result = await search_graph.ainvoke(state)
            
            # Extract response
            response_text = self._extract_response_text(result)
            
            # Log assistant response
            self.conversation_history.append({
                "role": "assistant",
                "content": response_text,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Send text response
            await self.send_message({
                "type": "assistant_response",
                "text": response_text
            })
            
            # Send voice parameters to client for display
            voice_params = result.get("voice_synthesis_params", {})
            if voice_params:
                await self.send_message({
                    "type": "voice_params",
                    "params": voice_params
                })
            
            # Synthesize and send audio response with AI-driven parameters
            await self.synthesize_and_send_response(response_text, voice_params)
            
            # Send search results if available
            if result.get("search_results"):
                await self.send_message({
                    "type": "search_results",
                    "products": result["search_results"][:10]
                })
                
        except Exception as e:
            logger.error(f"Processing error: {e}")
            error_message = "I'm sorry, I had trouble processing that. Could you please try again?"
            # Use empathetic voice for error messages
            error_voice_params = {"voice_type": "empathetic", "emotion": "empathetic"}
            await self.synthesize_and_send_response(error_message, error_voice_params)
    
    async def synthesize_and_send_response(self, text: str, voice_params: Optional[Dict[str, Any]] = None):
        """Synthesize text and send audio to client using AI-driven parameters"""
        try:
            self.is_assistant_speaking = True
            
            # Use AI-driven voice parameters from supervisor/LLM
            # Fallback to defaults if not provided
            if voice_params is None:
                voice_params = {}
            
            voice_type = voice_params.get("voice_type", "default")
            emotion = voice_params.get("emotion", "neutral")
            cultural_adapted_text = voice_params.get("adapted_text", text)
            
            # Create conversational SSML
            ssml_text = self.tts.create_conversational_ssml(
                cultural_adapted_text,
                style=emotion if emotion != "neutral" else "normal",
                language_code=self.current_language
            )
            
            # Synthesize audio with SSML and AI-driven parameters
            audio_content = await self.tts.synthesize(
                ssml_text,
                language_code=self.current_language,
                voice_type=voice_type,
                speaking_rate=voice_params.get("speaking_rate", 1.0),
                pitch=voice_params.get("pitch_adjustment", 0.0),
                use_ssml=True  # Use the SSML we created
            )
            
            # Send audio in chunks for streaming
            chunk_size = 4096  # 4KB chunks
            for i in range(0, len(audio_content), chunk_size):
                # Check for interruption
                if self.user_interrupted:
                    logger.info("User interrupted, stopping playback")
                    self.user_interrupted = False
                    break
                    
                chunk = audio_content[i:i + chunk_size]
                await self.websocket.send_bytes(chunk)
                await asyncio.sleep(0.01)  # Small delay for smooth playback
                
        except Exception as e:
            logger.error(f"TTS error: {e}")
        finally:
            self.is_assistant_speaking = False
            
            # Send end of speech marker
            await self.send_message({
                "type": "assistant_speech_end"
            })
    
    def _extract_response_text(self, result: Dict[str, Any]) -> str:
        """Extract response text from LangGraph result"""
        # Try different possible response locations
        if "final_response" in result and result["final_response"]:
            return result["final_response"].get("message", "")
            
        if "messages" in result and result["messages"]:
            for msg in reversed(result["messages"]):
                if msg.get("role") == "assistant":
                    return msg.get("content", "")
                    
        # Fallback: summarize search results
        if result.get("search_results"):
            count = len(result["search_results"])
            return f"I found {count} products matching your search."
            
        return "I processed your request. How else can I help you?"
    
    async def send_message(self, message: Dict[str, Any]):
        """Send JSON message to client"""
        try:
            await self.websocket.send_json(message)
        except Exception as e:
            logger.error(f"Send message error: {e}")
    
    async def send_error(self, error: str):
        """Send error message to client"""
        await self.send_message({
            "type": "error",
            "message": error
        })
    
    async def cleanup(self):
        """Clean up session resources"""
        logger.info(f"Cleaning up voice session: {self.session_id}")
        # Add any cleanup needed


@router.websocket("/connect")
async def voice_websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for Google Voice conversations"""
    session = GoogleVoiceSession(websocket)
    await session.handle_connection()


@router.get("/health")
async def voice_health():
    """Health check for Google Voice integration"""
    return {
        "status": "healthy",
        "service": "google_voice",
        "features": [
            "speech-to-text",
            "text-to-speech", 
            "multi-language",
            "streaming-recognition",
            "langgraph-integration"
        ],
        "languages": [
            "en-US", "en-IN", "es-US", 
            "hi-IN", "zh-CN", "ko-KR"
        ]
    }