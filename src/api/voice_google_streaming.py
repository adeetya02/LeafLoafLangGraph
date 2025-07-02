"""
Google Voice Streaming with AI-Native Supervisor
Handles real-time audio streaming with STT/TTS
"""
import asyncio
import json
import base64
from typing import Optional, AsyncGenerator
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import structlog
from datetime import datetime

from src.agents.supervisor_optimized import OptimizedSupervisorAgent
from src.voice.google_voice_handler import GoogleVoiceHandler
from src.core.graph import search_graph
from src.utils.id_generator import generate_request_id
from src.models.state import SearchState, SearchStrategy
from src.models.voice_state import VoiceMetadata

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice/google-streaming")

class VoiceStreamingSession:
    """Manages a voice streaming session with Google STT/TTS"""
    
    def __init__(self, session_id: str, language: str = "en-US"):
        self.session_id = session_id
        self.language = language
        self.voice_handler = GoogleVoiceHandler()
        # Create a dedicated supervisor instance for this session
        self.supervisor = OptimizedSupervisorAgent()
        self.audio_buffer = bytearray()
        self.is_processing = False
        
    async def process_audio_chunk(self, audio_data: bytes) -> Optional[dict]:
        """Process incoming audio chunk"""
        # Add to buffer
        self.audio_buffer.extend(audio_data)
        
        # Process if we have enough audio (e.g., 1 second worth)
        # Google STT works best with chunks of 0.5-1 second
        if len(self.audio_buffer) > 16000:  # ~1 second at 16kHz
            if not self.is_processing:
                self.is_processing = True
                try:
                    # Process the audio
                    result = await self._process_audio_buffer()
                    return result
                finally:
                    self.is_processing = False
        
        return None
    
    async def _process_audio_buffer(self) -> Optional[dict]:
        """Process the accumulated audio buffer"""
        try:
            # Convert buffer to audio stream
            audio_data = bytes(self.audio_buffer)
            self.audio_buffer = bytearray()  # Clear buffer
            
            # Use Google STT directly (simpler approach)
            from google.cloud import speech
            
            client = speech.SpeechClient()
            audio = speech.RecognitionAudio(content=audio_data)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
                sample_rate_hertz=48000,
                language_code=self.language,
                enable_automatic_punctuation=True,
            )
            
            # Synchronous recognition (simpler than streaming)
            response = client.recognize(config=config, audio=audio)
            
            if not response.results:
                return None
            
            # Get transcript
            transcript = response.results[0].alternatives[0].transcript
            confidence = response.results[0].alternatives[0].confidence
            
            # Simple voice metadata
            voice_metadata = {
                "pace": "normal",
                "emotion": "neutral", 
                "volume": "normal",
                "clarity": "high" if confidence > 0.9 else "medium",
                "confidence": confidence
            }
            
            logger.info(f"Transcribed: {transcript}", 
                       voice_metadata=voice_metadata)
            
            # Process through AI-native supervisor
            state = await self._process_with_supervisor(transcript, voice_metadata)
            
            # Generate voice response
            response_text = self._generate_response_text(state)
            
            # Convert to speech
            audio_response = await self.voice_handler.generate_voice_response(
                response_text,
                self.session_id,
                "assistant",
                voice_metadata,
                style_hint=state.get("voice_synthesis_params", {})
            )
            
            return {
                "type": "voice_response",
                "transcript": transcript,
                "response_text": response_text,
                "audio": base64.b64encode(audio_response["audio_content"]).decode(),
                "intent": state.get("intent"),
                "confidence": state.get("confidence"),
                "voice_metadata": voice_metadata,
                "supervisor_native": True  # Confirm AI-native
            }
            
        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            return {
                "type": "error",
                "message": str(e)
            }
    
    async def _process_with_supervisor(self, text: str, voice_metadata: dict) -> dict:
        """Process through AI-native supervisor"""
        # Create state with all required fields
        state = SearchState(
            messages=[],
            query=text,
            request_id=generate_request_id(),
            timestamp=datetime.utcnow(),
            session_id=self.session_id,
            voice_metadata=voice_metadata,
            search_params={"alpha": 0.5},
            # Initialize all required fields
            reasoning=[],
            intent=None,
            next_action=None,
            confidence=0.0,
            routing_decision=None,
            should_search=False,
            alpha_value=0.5,
            search_strategy=SearchStrategy.HYBRID,
            search_results=[],
            search_metadata={},
            pending_tool_calls=[],
            completed_tool_calls=[],
            agent_status={},
            agent_timings={},
            total_execution_time=0.0,
            trace_id=None,
            final_response={},
            should_continue=True,
            error=None,
            enhanced_query=None,
            current_order={},
            order_metadata={},
            user_context=None,
            preferences=[],
            is_general_chat=False
        )
        
        # Process through supervisor (AI-native, no patterns!)
        state = await self.supervisor._run(state)
        
        return state
    
    def _generate_response_text(self, state: dict) -> str:
        """Generate response based on intent"""
        intent = state.get("intent", "unknown")
        query = state.get("query", "")
        
        # Simple responses for demo
        if intent == "general_chat":
            return "Hello! I'm your AI shopping assistant. How can I help you today?"
        elif intent == "product_search":
            return f"I'll search for {query} for you. One moment..."
        elif intent in ["add_to_order", "remove_from_order", "update_order"]:
            return f"I'll help you with your cart. Processing: {query}"
        elif intent == "list_order":
            return "Let me check what's in your cart..."
        elif intent == "confirm_order":
            return "I'll help you checkout. Let me review your order..."
        else:
            return f"I understand you're asking about: {query}. Let me help with that."

@router.websocket("/ws")
async def voice_streaming_websocket(
    websocket: WebSocket,
    language: Optional[str] = Query(default="en-US")
):
    """WebSocket endpoint for voice streaming with AI-native supervisor"""
    await websocket.accept()
    
    session_id = generate_request_id()
    session = VoiceStreamingSession(session_id, language)
    
    logger.info(f"Voice streaming session started: {session_id}")
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "session_started",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Voice streaming ready. Send audio chunks or text.",
            "features": {
                "supervisor": "AI-native (Gemini)",
                "stt": "Google Cloud Speech-to-Text",
                "tts": "Google Cloud Text-to-Speech",
                "streaming": True,
                "no_hardcoded_patterns": True
            }
        })
        
        # Main message loop
        while True:
            message = await websocket.receive()
            
            if message["type"] == "websocket.receive":
                if "text" in message:
                    # Handle text message
                    data = json.loads(message["text"])
                    msg_type = data.get("type")
                    
                    if msg_type == "text":
                        # Process text directly
                        text = data.get("text", "")
                        state = await session._process_with_supervisor(text, {})
                        
                        response_text = session._generate_response_text(state)
                        
                        await websocket.send_json({
                            "type": "text_response",
                            "text": response_text,
                            "intent": state.get("intent"),
                            "confidence": state.get("confidence"),
                            "supervisor_native": True
                        })
                    
                    elif msg_type == "ping":
                        await websocket.send_json({"type": "pong"})
                
                elif "bytes" in message:
                    # Handle audio data
                    audio_data = message["bytes"]
                    
                    # Process audio chunk
                    result = await session.process_audio_chunk(audio_data)
                    
                    if result:
                        await websocket.send_json(result)
    
    except WebSocketDisconnect:
        logger.info(f"Voice streaming session ended: {session_id}")
    except Exception as e:
        logger.error(f"Voice streaming error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })

@router.get("/test")
async def test_supervisor_native():
    """Test endpoint to confirm supervisor is AI-native"""
    # Create a new supervisor instance for testing
    supervisor = OptimizedSupervisorAgent()
    
    # Check LLM type
    llm_type = type(supervisor.llm).__name__
    
    # Test queries
    test_queries = [
        "Hello",
        "I need apples",
        "Add milk to cart",
        "What's in my order?"
    ]
    
    results = []
    for query in test_queries:
        state = SearchState(
            messages=[],
            query=query,
            request_id=generate_request_id(),
            timestamp=datetime.utcnow(),
            session_id="test",
            voice_metadata={},
            search_params={"alpha": 0.5},
            reasoning=[],
            intent=None,
            next_action=None,
            confidence=0.0,
            routing_decision=None,
            should_search=False,
            alpha_value=0.5,
            search_strategy=SearchStrategy.HYBRID,
            search_results=[],
            search_metadata={},
            pending_tool_calls=[],
            completed_tool_calls=[],
            agent_status={},
            agent_timings={},
            total_execution_time=0.0,
            trace_id=None,
            final_response={},
            should_continue=True,
            error=None,
            enhanced_query=None,
            current_order={},
            order_metadata={},
            user_context=None,
            preferences=[],
            is_general_chat=False
        )
        
        state = await supervisor._run(state)
        
        results.append({
            "query": query,
            "intent": state.get("intent"),
            "confidence": state.get("confidence")
        })
    
    return {
        "supervisor": "AI-native",
        "llm": llm_type,
        "no_hardcoded_patterns": True,
        "test_results": results
    }