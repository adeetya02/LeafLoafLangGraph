"""
Unified Google Voice WebSocket Endpoint
Integrates STT, TTS, and Voice-Native Supervisor
"""
import asyncio
import json
import base64
from typing import Optional, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import structlog
from datetime import datetime

from src.agents.supervisor_voice_native import VoiceNativeSupervisor
try:
    from src.voice.google_voice_handler import GoogleVoiceHandler
    GOOGLE_AVAILABLE = True
except Exception as e:
    logger.warning(f"Google Voice not available: {e}, using mock mode")
    from src.voice.mock_voice_handler import MockVoiceHandler as GoogleVoiceHandler
    GOOGLE_AVAILABLE = False
from src.core.graph import search_graph
from src.utils.id_generator import generate_request_id
from src.models.state import SearchState

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice/google")

class VoiceConversationManager:
    """Manages voice conversations through WebSocket"""
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.voice_handler = GoogleVoiceHandler()
        self.supervisor = VoiceNativeSupervisor()
        self.session_id = generate_request_id()
        self.is_active = True
        self.audio_queue = asyncio.Queue()
        self.state = None
        
    async def handle_conversation(self):
        """Main conversation loop"""
        try:
            # Send initial greeting
            await self.send_message({
                "type": "session_started",
                "session_id": self.session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Voice conversation started. How can I help you today?"
            })
            
            # Start concurrent tasks
            tasks = [
                asyncio.create_task(self.receive_audio()),
                asyncio.create_task(self.process_audio()),
                asyncio.create_task(self.heartbeat())
            ]
            
            # Wait for any task to complete (or fail)
            done, pending = await asyncio.wait(
                tasks, 
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for session {self.session_id}")
        except Exception as e:
            logger.error(f"Voice conversation error: {e}")
            await self.send_error(str(e))
        finally:
            self.is_active = False
            await self.voice_handler.cleanup_session(self.session_id)
    
    async def receive_audio(self):
        """Receive audio chunks from WebSocket"""
        try:
            while self.is_active:
                message = await self.websocket.receive_json()
                
                if message.get("type") == "audio":
                    # Decode base64 audio
                    audio_data = base64.b64decode(message["audio"])
                    await self.audio_queue.put(audio_data)
                    
                elif message.get("type") == "text":
                    # Handle text input
                    await self.process_text_input(message["text"])
                    
                elif message.get("type") == "config":
                    # Update configuration
                    await self.update_config(message.get("config", {}))
                    
                elif message.get("type") == "end_stream":
                    # Signal end of audio stream
                    await self.audio_queue.put(None)
                    
        except WebSocketDisconnect:
            raise
        except Exception as e:
            logger.error(f"Audio receive error: {e}")
            raise
    
    async def process_audio(self):
        """Process audio through STT and supervisor"""
        try:
            async def audio_generator():
                """Generate audio chunks from queue"""
                while self.is_active:
                    chunk = await self.audio_queue.get()
                    if chunk is None:
                        break
                    yield chunk
            
            # Process voice stream through supervisor
            async for state in self.supervisor.process_voice_stream(
                audio_generator(),
                self.session_id,
                self.state
            ):
                # Update conversation state
                self.state = state
                
                # Send interim results
                await self.send_message({
                    "type": "transcript",
                    "text": state.get("query", ""),
                    "is_final": True,
                    "confidence": state.get("voice_confidence", 0.0),
                    "language": state.get("detected_language", "en-US")
                })
                
                # Process through full graph if routing decision made
                if state.get("routing_decision"):
                    await self.process_through_graph(state)
                    
        except Exception as e:
            logger.error(f"Audio processing error: {e}")
            raise
    
    async def process_through_graph(self, state: SearchState):
        """Process state through the full LangGraph"""
        try:
            # Send processing status
            await self.send_message({
                "type": "processing",
                "intent": state.get("intent"),
                "routing": state.get("routing_decision")
            })
            
            # Run through graph
            result = await search_graph.ainvoke(state)
            
            # Extract response
            response_text = self._extract_response_text(result)
            
            # Generate voice response
            voice_response = await self.voice_handler.generate_voice_response(
                text=response_text,
                session_id=self.session_id,
                response_type=result.get("intent", "answer"),
                voice_metadata=state.get("voice_metadata"),
                style_hint=state.get("voice_routing_hints", {}).get("response_style", {}).get("style")
            )
            
            # Send text response
            await self.send_message({
                "type": "response",
                "text": response_text,
                "metadata": {
                    "intent": result.get("intent"),
                    "confidence": result.get("confidence"),
                    "products_found": len(result.get("search_results", [])),
                    "execution_time": result.get("total_execution_time", 0)
                }
            })
            
            # Send audio response if available
            if voice_response.get("audio_data"):
                await self.send_message({
                    "type": "audio_response",
                    "audio": base64.b64encode(voice_response["audio_data"]).decode(),
                    "format": {
                        "encoding": "LINEAR16",
                        "sample_rate": 24000,
                        "channels": 1
                    }
                })
                
        except Exception as e:
            logger.error(f"Graph processing error: {e}")
            await self.send_error(f"Failed to process request: {str(e)}")
    
    async def process_text_input(self, text: str):
        """Process text input through supervisor"""
        try:
            # Create state from text
            state = self._create_state_from_text(text)
            
            # Process through supervisor
            state = await self.supervisor.execute(state)
            
            # Process through graph
            if state.get("routing_decision"):
                await self.process_through_graph(state)
                
        except Exception as e:
            logger.error(f"Text processing error: {e}")
            await self.send_error(str(e))
    
    def _create_state_from_text(self, text: str) -> SearchState:
        """Create SearchState from text input"""
        return SearchState(
            messages=[],
            query=text,
            request_id=generate_request_id(),
            timestamp=datetime.utcnow(),
            alpha_value=0.5,
            search_strategy="hybrid",
            intent=None,
            next_action=None,
            confidence=0.0,
            routing_decision=None,
            should_search=False,
            search_params={},
            reasoning=[],
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
            session_id=self.session_id
        )
    
    def _extract_response_text(self, result: Dict[str, Any]) -> str:
        """Extract response text from graph result"""
        # Check final_response first
        if result.get("final_response", {}).get("message"):
            return result["final_response"]["message"]
            
        # Check for search results
        if result.get("search_results"):
            products = result["search_results"][:5]  # Top 5
            if products:
                response = f"I found {len(result['search_results'])} products. Here are the top options:\n"
                for i, product in enumerate(products, 1):
                    response += f"{i}. {product.get('name', 'Unknown')} - ${product.get('price', 0):.2f}\n"
                return response
                
        # Fallback
        return "I'm sorry, I couldn't process that request. Could you please try again?"
    
    async def update_config(self, config: Dict[str, Any]):
        """Update voice configuration"""
        if "language" in config:
            self.voice_handler.stt_handler.update_language(config["language"])
            self.voice_handler.tts_handler.set_default_voice(
                config["language"],
                config.get("voice_type", "default")
            )
            
    async def send_message(self, message: Dict[str, Any]):
        """Send message to client"""
        try:
            await self.websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            
    async def send_error(self, error: str):
        """Send error message to client"""
        await self.send_message({
            "type": "error",
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    async def heartbeat(self):
        """Send periodic heartbeat to keep connection alive"""
        try:
            while self.is_active:
                await asyncio.sleep(30)
                await self.send_message({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat()
                })
        except Exception:
            pass

@router.websocket("/ws")
async def voice_websocket(
    websocket: WebSocket,
    language: Optional[str] = Query(default="en-US")
):
    """
    WebSocket endpoint for voice conversations
    
    Protocol:
    - Client sends: {"type": "audio", "audio": "base64_encoded_audio"}
    - Client sends: {"type": "text", "text": "user message"}
    - Client sends: {"type": "config", "config": {"language": "es-US"}}
    - Client sends: {"type": "end_stream"} to end audio stream
    
    - Server sends: {"type": "transcript", "text": "...", "is_final": true}
    - Server sends: {"type": "response", "text": "...", "metadata": {...}}
    - Server sends: {"type": "audio_response", "audio": "base64_encoded"}
    - Server sends: {"type": "error", "error": "..."}
    - Server sends: {"type": "heartbeat", "timestamp": "..."}
    """
    await websocket.accept()
    
    manager = VoiceConversationManager(websocket)
    
    # Set initial language if provided
    if language != "en-US":
        await manager.update_config({"language": language})
    
    await manager.handle_conversation()

@router.get("/languages")
async def get_supported_languages():
    """Get list of supported languages"""
    return {
        "languages": [
            {"code": "en-US", "name": "English (US)"},
            {"code": "en-IN", "name": "English (India)"},
            {"code": "es-US", "name": "Spanish (US)"},
            {"code": "es-MX", "name": "Spanish (Mexico)"},
            {"code": "hi-IN", "name": "Hindi"},
            {"code": "zh-CN", "name": "Chinese (Mandarin)"},
            {"code": "ko-KR", "name": "Korean"},
            {"code": "ja-JP", "name": "Japanese"},
            {"code": "vi-VN", "name": "Vietnamese"},
            {"code": "ar-SA", "name": "Arabic"},
            {"code": "pt-BR", "name": "Portuguese (Brazil)"},
            {"code": "bn-IN", "name": "Bengali"},
            {"code": "ta-IN", "name": "Tamil"},
            {"code": "fr-FR", "name": "French"},
            {"code": "de-DE", "name": "German"},
            {"code": "it-IT", "name": "Italian"},
            {"code": "ru-RU", "name": "Russian"},
            {"code": "th-TH", "name": "Thai"},
        ]
    }

@router.get("/voices")
async def get_available_voices(language: str = Query(default="en-US")):
    """Get available voices for a language"""
    handler = GoogleVoiceHandler()
    voices = await handler.tts_handler.list_voices(language)
    return {"voices": voices}