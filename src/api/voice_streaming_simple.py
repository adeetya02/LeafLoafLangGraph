"""
Simple WebSocket streaming with Deepgram - exactly following documentation
"""
import asyncio
import json
import os
import certifi
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
router = APIRouter(prefix="/api/v1/voice-simple")

DEEPGRAM_API_KEY = "36a821d351939023aabad9beeaa68b391caa124a"

@router.websocket("/stream")
async def streaming_endpoint(websocket: WebSocket):
    """Simple WebSocket endpoint for voice streaming"""
    await websocket.accept()
    logger.info("Client connected for simple voice streaming")
    
    # Create Deepgram client
    config = DeepgramClientOptions(
        options={"keepalive": "true"}
    )
    deepgram = DeepgramClient(DEEPGRAM_API_KEY, config)
    dg_connection = deepgram.listen.asyncwebsocket.v("1")
    
    # Variables to track state
    full_transcript = ""
    is_processing = False
    
    async def process_search(query: str):
        """Process search through LeafLoaf"""
        nonlocal is_processing
        if is_processing:
            return
            
        is_processing = True
        try:
            logger.info(f"🔍 Searching for: {query}")
            
            # Notify client
            await websocket.send_json({
                "type": "search_start",
                "query": query
            })
            
            # Create search state
            initial_state = {
                "query": query,
                "user_id": "voice_user",
                "request_id": generate_request_id(),
                "limit": 10,
                "session_id": "voice_session"
            }
            
            # Execute search
            result = await asyncio.to_thread(
                search_graph.invoke,
                initial_state
            )
            
            # Extract products
            products = []
            if result.get("products"):
                products = [
                    {
                        "name": p.get("name", "Unknown"),
                        "price": float(p.get("price", 0)),
                        "unit": p.get("unit", ""),
                        "category": p.get("category", "")
                    }
                    for p in result["products"][:10]
                ]
            
            # Send results
            await websocket.send_json({
                "type": "search_results",
                "query": query,
                "products": products,
                "count": len(products)
            })
            
            logger.info(f"✅ Found {len(products)} products")
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            await websocket.send_json({
                "type": "error",
                "message": "Search failed"
            })
        finally:
            is_processing = False
    
    # Define event handlers
    async def on_open(self, open, **kwargs):
        logger.info("✅ Deepgram connected")
        await websocket.send_json({
            "type": "system",
            "message": "Connected to Deepgram. Start speaking!"
        })
    
    async def on_transcript(self, result, **kwargs):
        nonlocal full_transcript
        
        sentence = result.channel.alternatives[0].transcript
        
        if len(sentence) == 0:
            return
            
        # Get metadata
        is_final = result.is_final
        speech_final = result.speech_final
        
        # Send to client
        await websocket.send_json({
            "type": "transcript",
            "text": sentence,
            "is_final": is_final,
            "speech_final": speech_final
        })
        
        # Track the full transcript
        if is_final:
            full_transcript = sentence
            logger.info(f"📝 Final: {sentence}")
    
    async def on_utterance_end(self, utterance_end, **kwargs):
        nonlocal full_transcript
        
        logger.info("🎯 Utterance ended")
        
        # Process if we have text
        if full_transcript.strip():
            # Send final transcript
            await websocket.send_json({
                "type": "final_transcript", 
                "text": full_transcript
            })
            
            # Trigger search
            asyncio.create_task(process_search(full_transcript))
            
            # Clear for next utterance
            full_transcript = ""
    
    async def on_error(self, error, **kwargs):
        logger.error(f"Deepgram error: {error}")
        await websocket.send_json({
            "type": "error",
            "message": f"Transcription error: {error}"
        })
    
    # Register handlers
    dg_connection.on(LiveTranscriptionEvents.Open, on_open)
    dg_connection.on(LiveTranscriptionEvents.Transcript, on_transcript)
    dg_connection.on(LiveTranscriptionEvents.UtteranceEnd, on_utterance_end)
    dg_connection.on(LiveTranscriptionEvents.Error, on_error)
    
    # Configure options
    options = LiveOptions(
        model="nova-2",
        language="en-US",
        smart_format=True,
        encoding="linear16",
        sample_rate=16000,
        channels=1,
        interim_results=True,
        utterance_end_ms=1000,
        vad_events=True,
        endpointing=300
    )
    
    try:
        # Start Deepgram connection
        if await dg_connection.start(options):
            logger.info("Deepgram started successfully")
            
            # Process messages from client
            while True:
                message = await websocket.receive()
                
                if message["type"] == "websocket.receive":
                    if "bytes" in message:
                        # Forward audio to Deepgram
                        await dg_connection.send(message["bytes"])
                    elif "text" in message:
                        # Handle control messages
                        data = json.loads(message["text"])
                        if data.get("type") == "stop":
                            break
                            
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await dg_connection.finish()
        logger.info("Cleaned up voice streaming session")

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "voice-streaming-simple"
    }