"""
Production-ready live streaming voice with Deepgram
Based on official Deepgram streaming documentation
"""
import asyncio
import json
import uuid
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)
import structlog

from src.core.graph import search_graph
from src.utils.id_generator import generate_request_id

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice-live")

DEEPGRAM_API_KEY = "36a821d351939023aabad9beeaa68b391caa124a"

class LiveStreamHandler:
    """Handles live streaming voice with Deepgram"""
    
    def __init__(self, client_ws: WebSocket):
        self.client_ws = client_ws
        self.deepgram_client = DeepgramClient(DEEPGRAM_API_KEY)
        self.dg_connection = None
        self.current_transcript = ""
        self.last_processed = ""
        self.user_id = f"voice_user_{str(uuid.uuid4())[:8]}"
        self.is_processing = False
        
    async def connect_deepgram(self):
        """Connect to Deepgram WebSocket"""
        try:
            # Create a websocket connection to Deepgram
            self.dg_connection = self.deepgram_client.listen.asyncwebsocket.v("1")
            
            # Configure event handlers
            self.dg_connection.on(LiveTranscriptionEvents.Open, self.on_open)
            self.dg_connection.on(LiveTranscriptionEvents.Transcript, self.on_transcript)
            self.dg_connection.on(LiveTranscriptionEvents.Metadata, self.on_metadata)
            self.dg_connection.on(LiveTranscriptionEvents.Error, self.on_error)
            self.dg_connection.on(LiveTranscriptionEvents.Close, self.on_close)
            
            # Configure options
            options = LiveOptions(
                model="nova-2",
                language="en-US",
                punctuate=True,
                smart_format=True,
                interim_results=True,
                utterance_end_ms=1000,
                vad_events=True,
                endpointing=300  # More aggressive endpointing for conversation
            )
            
            # Start the connection
            if await self.dg_connection.start(options):
                logger.info("Connected to Deepgram")
                return True
            else:
                logger.error("Failed to connect to Deepgram")
                return False
                
        except Exception as e:
            logger.error(f"Deepgram connection error: {e}")
            return False
    
    async def on_open(self, *args, **kwargs):
        """Called when Deepgram connection opens"""
        logger.info("Deepgram connection opened")
        await self.client_ws.send_json({
            "type": "deepgram_ready",
            "message": "Connected to Deepgram - start speaking!"
        })
    
    async def on_transcript(self, *args, **kwargs):
        """Handle transcript events from Deepgram"""
        result = kwargs.get("result", {})
        
        # Extract transcript data
        channel = result.get("channel", {})
        alternatives = channel.get("alternatives", [])
        
        if not alternatives:
            return
            
        transcript = alternatives[0].get("transcript", "")
        confidence = alternatives[0].get("confidence", 0.0)
        is_final = result.get("is_final", False)
        speech_final = result.get("speech_final", False)
        
        if transcript:
            # Send transcript to client
            await self.client_ws.send_json({
                "type": "transcript",
                "text": transcript,
                "confidence": confidence,
                "is_final": is_final,
                "speech_final": speech_final
            })
            
            # Build complete transcript
            if is_final:
                self.current_transcript += transcript + " "
                
                # Show interim complete transcript
                await self.client_ws.send_json({
                    "type": "transcript_so_far",
                    "text": self.current_transcript.strip()
                })
            
            # Process when speech ends
            if speech_final and self.current_transcript.strip():
                query = self.current_transcript.strip()
                
                # Avoid duplicate processing
                if query != self.last_processed and not self.is_processing:
                    self.last_processed = query
                    self.is_processing = True
                    
                    # Process in background to not block audio streaming
                    asyncio.create_task(self.search_products(query))
                
                self.current_transcript = ""
    
    async def on_metadata(self, *args, **kwargs):
        """Handle metadata events"""
        metadata = kwargs.get("metadata", {})
        logger.debug(f"Deepgram metadata: {metadata}")
    
    async def on_error(self, *args, **kwargs):
        """Handle error events"""
        error = kwargs.get("error", {})
        logger.error(f"Deepgram error: {error}")
        await self.client_ws.send_json({
            "type": "error",
            "message": f"Transcription error: {error}"
        })
    
    async def on_close(self, *args, **kwargs):
        """Handle connection close"""
        logger.info("Deepgram connection closed")
        await self.client_ws.send_json({
            "type": "deepgram_closed",
            "message": "Transcription connection closed"
        })
    
    async def search_products(self, query: str):
        """Search for products based on transcript"""
        try:
            # Notify client
            await self.client_ws.send_json({
                "type": "searching",
                "query": query
            })
            
            # Prepare search state
            from src.models.state import SearchState
            
            initial_state = SearchState(
                query=query,
                user_id=self.user_id,
                request_id=generate_request_id(),
                limit=8
            )
            
            # Execute search
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
                        "category": p.get("category", "")
                    }
                    for p in result["products"][:8]
                ]
            
            # Send results
            await self.client_ws.send_json({
                "type": "results",
                "query": query,
                "products": products,
                "count": len(products)
            })
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            await self.client_ws.send_json({
                "type": "error",
                "message": "Failed to search for products"
            })
        finally:
            self.is_processing = False
    
    async def send_audio(self, audio_data: bytes):
        """Send audio data to Deepgram"""
        if self.dg_connection:
            await self.dg_connection.send(audio_data)
    
    async def close(self):
        """Clean up connections"""
        if self.dg_connection:
            await self.dg_connection.finish()


@router.websocket("/stream")
async def live_streaming_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live streaming voice"""
    await websocket.accept()
    logger.info("Client connected for live streaming")
    
    handler = LiveStreamHandler(websocket)
    
    try:
        # Connect to Deepgram
        connected = await handler.connect_deepgram()
        if not connected:
            await websocket.send_json({
                "type": "error",
                "message": "Failed to connect to Deepgram"
            })
            return
        
        # Handle incoming messages
        while True:
            message = await websocket.receive()
            
            if message["type"] == "websocket.receive":
                if "bytes" in message:
                    # Audio data - forward to Deepgram
                    await handler.send_audio(message["bytes"])
                elif "text" in message:
                    # Control messages
                    data = json.loads(message["text"])
                    if data.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                    elif data.get("type") == "stop":
                        break
                        
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await handler.close()
        logger.info("Cleaned up live streaming session")


@router.get("/status")
async def streaming_status():
    """Check live streaming status"""
    return {
        "status": "ready",
        "deepgram_api_key": bool(DEEPGRAM_API_KEY),
        "endpoint": "/api/v1/voice-live/stream",
        "features": {
            "model": "nova-2",
            "interim_results": True,
            "smart_format": True,
            "endpointing": True,
            "vad_events": True
        }
    }