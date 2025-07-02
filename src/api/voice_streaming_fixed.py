"""
Fixed WebSocket streaming with proper Deepgram SDK integration
Handles binary audio and triggers search immediately on transcripts
"""
import asyncio
import json
import uuid
import os
import certifi
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)
import structlog

# Fix SSL for macOS
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

from src.core.graph import search_graph
from src.utils.id_generator import generate_request_id
from src.models.state import SearchState

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice-fixed")

DEEPGRAM_API_KEY = "36a821d351939023aabad9beeaa68b391caa124a"

class StreamingVoiceHandler:
    """Handles streaming voice with proper Deepgram SDK integration"""
    
    def __init__(self, client_ws: WebSocket):
        self.client_ws = client_ws
        # Create Deepgram client with proper config
        config = DeepgramClientOptions(
            options={"keepalive": "true"}
        )
        self.deepgram = DeepgramClient(DEEPGRAM_API_KEY, config)
        self.dg_connection = None
        self.user_id = f"voice_user_{str(uuid.uuid4())[:8]}"
        self.session_id = str(uuid.uuid4())
        self.is_processing = False
        self.transcript_buffer = ""
        self.last_processed_transcript = ""
        self.current_sentence = ""  # Track current sentence being spoken
        
    async def initialize_deepgram(self):
        """Initialize Deepgram live connection"""
        try:
            # Create websocket connection using SDK (updated API)
            self.dg_connection = self.deepgram.listen.asyncwebsocket.v("1")
            
            # Register event handlers
            self.dg_connection.on(LiveTranscriptionEvents.Open, self.on_open)
            self.dg_connection.on(LiveTranscriptionEvents.Transcript, self.on_transcript)
            self.dg_connection.on(LiveTranscriptionEvents.Metadata, self.on_metadata)
            self.dg_connection.on(LiveTranscriptionEvents.UtteranceEnd, self.on_utterance_end)
            self.dg_connection.on(LiveTranscriptionEvents.Error, self.on_error)
            self.dg_connection.on(LiveTranscriptionEvents.Close, self.on_close)
            
            # Configure options for conversational AI
            options = LiveOptions(
                model="nova-2",
                language="en-US",
                punctuate=True,
                smart_format=True,
                interim_results=True,
                utterance_end_ms=1000,  # End utterance after 1 second of silence
                vad_events=True,
                endpointing=300,  # Aggressive endpointing for conversations
                encoding="linear16",  # PCM16
                sample_rate=16000,
                channels=1
            )
            
            # Start the connection
            success = await self.dg_connection.start(options)
            
            if success:
                logger.info("Deepgram connection established")
                await self.client_ws.send_json({
                    "type": "system",
                    "message": "Connected to Deepgram. Start speaking!"
                })
                return True
            else:
                logger.error("Failed to start Deepgram connection")
                return False
                
        except Exception as e:
            logger.error(f"Deepgram initialization error: {e}")
            return False
    
    async def on_open(self, *args, **kwargs):
        """Deepgram connection opened"""
        logger.info("Deepgram WebSocket opened")
    
    async def on_transcript(self, *args, **kwargs):
        """Handle transcript from Deepgram"""
        result = kwargs.get("result", {})
        logger.debug(f"Received transcript event: {result}")
        
        # Extract transcript details
        channel = result.get("channel", {})
        alternatives = channel.get("alternatives", [])
        
        if not alternatives:
            return
            
        alternative = alternatives[0]
        transcript = alternative.get("transcript", "")
        confidence = alternative.get("confidence", 0.0)
        
        # Get finalization flags
        is_final = result.get("is_final", False)
        speech_final = result.get("speech_final", False)
        
        if transcript:
            # Send transcript to client for display
            await self.client_ws.send_json({
                "type": "transcript",
                "text": transcript,
                "confidence": confidence,
                "is_final": is_final,
                "speech_final": speech_final
            })
            
            # Update current sentence
            self.current_sentence = transcript
            
            # When we get a final transcript, add it to the buffer
            if is_final and transcript.strip():
                self.transcript_buffer = transcript  # Replace buffer with latest final transcript
                logger.info(f"Final transcript: {transcript}")
    
    async def on_utterance_end(self, *args, **kwargs):
        """Handle utterance end event - trigger search"""
        logger.info("UtteranceEnd event received")
        
        # Process the complete utterance
        if self.transcript_buffer.strip() and not self.is_processing:
            complete_transcript = self.transcript_buffer.strip()
            
            # Avoid duplicate processing
            if complete_transcript != self.last_processed_transcript:
                self.last_processed_transcript = complete_transcript
                self.is_processing = True
                
                # Send final transcript
                await self.client_ws.send_json({
                    "type": "final_transcript",
                    "text": complete_transcript
                })
                
                # Trigger search immediately
                asyncio.create_task(self.process_search(complete_transcript))
            
            # Clear buffer for next utterance
            self.transcript_buffer = ""
    
    async def on_metadata(self, *args, **kwargs):
        """Handle metadata from Deepgram"""
        metadata = kwargs.get("metadata", {})
        logger.debug(f"Deepgram metadata: {metadata}")
    
    async def on_error(self, *args, **kwargs):
        """Handle Deepgram errors"""
        error = kwargs.get("error", "Unknown error")
        logger.error(f"Deepgram error: {error}")
        await self.client_ws.send_json({
            "type": "error",
            "message": f"Transcription error: {error}"
        })
    
    async def on_close(self, *args, **kwargs):
        """Deepgram connection closed"""
        logger.info("Deepgram WebSocket closed")
    
    async def process_search(self, query: str):
        """Process search through LeafLoaf supervisor"""
        try:
            # Notify client that search is starting
            await self.client_ws.send_json({
                "type": "search_start",
                "query": query
            })
            
            # Create search state
            initial_state = SearchState(
                query=query,
                user_id=self.user_id,
                request_id=generate_request_id(),
                limit=10,
                session_id=self.session_id
            )
            
            # Execute search through supervisor
            logger.info(f"Triggering search for: {query}")
            result = await asyncio.to_thread(
                search_graph.invoke,
                initial_state.model_dump()
            )
            
            # Extract products
            products = []
            if result.get("products"):
                products = [
                    {
                        "name": p.get("name") or p.get("product_name", "Unknown"),
                        "price": float(p.get("price") or p.get("unit_price", 0)),
                        "unit": p.get("unit", ""),
                        "category": p.get("category", ""),
                        "in_stock": p.get("in_stock", True)
                    }
                    for p in result["products"][:10]
                ]
            
            # Send results to client
            await self.client_ws.send_json({
                "type": "search_results",
                "query": query,
                "products": products,
                "count": len(products),
                "execution_time": result.get("metadata", {}).get("execution_time_ms", 0)
            })
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            await self.client_ws.send_json({
                "type": "error",
                "message": "Failed to search for products"
            })
        finally:
            self.is_processing = False
    
    async def handle_audio_data(self, audio_bytes: bytes):
        """Forward audio data to Deepgram"""
        if self.dg_connection:
            logger.debug(f"Forwarding {len(audio_bytes)} bytes of audio to Deepgram")
            await self.dg_connection.send(audio_bytes)
    
    async def cleanup(self):
        """Clean up connections"""
        if self.dg_connection:
            await self.dg_connection.finish()


@router.websocket("/stream")
async def streaming_voice_endpoint(websocket: WebSocket):
    """WebSocket endpoint for streaming voice with search"""
    await websocket.accept()
    logger.info("Client connected for voice streaming")
    
    handler = StreamingVoiceHandler(websocket)
    
    try:
        # Initialize Deepgram connection
        if not await handler.initialize_deepgram():
            await websocket.send_json({
                "type": "error",
                "message": "Failed to initialize voice transcription"
            })
            return
        
        # Process messages from client
        while True:
            message = await websocket.receive()
            
            if message["type"] == "websocket.receive":
                if "bytes" in message:
                    # Binary audio data - forward to Deepgram
                    await handler.handle_audio_data(message["bytes"])
                    
                elif "text" in message:
                    # Text message (control)
                    data = json.loads(message["text"])
                    
                    if data.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                    elif data.get("type") == "stop":
                        break
                        
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"Connection error: {str(e)}"
        })
    finally:
        await handler.cleanup()
        logger.info("Cleaned up voice streaming session")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "voice-streaming-fixed",
        "deepgram_configured": bool(DEEPGRAM_API_KEY),
        "features": {
            "streaming": True,
            "search_integration": True,
            "model": "nova-2"
        }
    }