"""
Test endpoint for simplified Google Voice
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from google.cloud import speech

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/google-test")

# Thread pool for blocking operations
executor = ThreadPoolExecutor(max_workers=2)

@router.websocket("/ws")
async def test_google_voice(websocket: WebSocket):
    """Simple test of Google STT streaming"""
    await websocket.accept()
    logger.info("Test WebSocket connected")
    
    try:
        # Initialize Google STT
        client = speech.SpeechClient()
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
            enable_automatic_punctuation=True,
        )
        streaming_config = speech.StreamingRecognitionConfig(
            config=config,
            interim_results=True,
        )
        
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "message": "Google STT Test Connected"
        })
        
        # Simple approach: collect audio chunks and process
        audio_chunks = []
        chunk_count = 0
        
        # Collect initial audio (1 second worth)
        logger.info("Collecting initial audio...")
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < 1.0:
            try:
                data = await asyncio.wait_for(websocket.receive_bytes(), timeout=0.1)
                audio_chunks.append(data)
                chunk_count += 1
                logger.debug(f"Collected chunk {chunk_count}: {len(data)} bytes")
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error collecting audio: {e}")
                break
        
        if not audio_chunks:
            await websocket.send_json({
                "type": "error",
                "message": "No audio received"
            })
            return
        
        logger.info(f"Collected {len(audio_chunks)} chunks, starting STT")
        
        # Create request generator (config passed separately to streaming_recognize)
        def request_generator():
            # Send collected audio
            for chunk in audio_chunks:
                yield speech.StreamingRecognizeRequest(
                    audio_content=chunk
                )
            
            # Continue with live audio
            while True:
                try:
                    # Get next chunk with timeout
                    future = asyncio.run_coroutine_threadsafe(
                        websocket.receive_bytes(),
                        asyncio.get_event_loop()
                    )
                    data = future.result(timeout=0.1)
                    yield speech.StreamingRecognizeRequest(
                        audio_content=data
                    )
                except Exception as e:
                    logger.debug(f"No more audio: {e}")
                    break
        
        # Process in thread to avoid blocking
        def process_stt():
            try:
                # Google API expects config and requests as positional args
                responses = client.streaming_recognize(
                    streaming_config,
                    request_generator()
                )
                
                for response in responses:
                    if response.results:
                        for result in response.results:
                            if result.alternatives:
                                return {
                                    "transcript": result.alternatives[0].transcript,
                                    "is_final": result.is_final,
                                    "confidence": getattr(result.alternatives[0], 'confidence', 0.0)
                                }
            except Exception as e:
                logger.error(f"STT error: {e}")
                return {"error": str(e)}
        
        # Run STT in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(executor, process_stt)
        
        # Send result
        await websocket.send_json({
            "type": "transcript",
            **result
        })
        
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"Test error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })

@router.get("/health")
async def test_health():
    """Health check"""
    return {"status": "ok", "test": "google-voice-simple"}