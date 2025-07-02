"""
Fixed Google Voice implementation - immediate streaming
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google.cloud import speech
import structlog
import asyncio
import json
from typing import Optional
import queue
import threading

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/google-fixed")

class GoogleVoiceHandler:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.client = speech.SpeechClient()
        self.audio_queue = queue.Queue()
        self.is_running = True
        
        # Configure recognition
        self.config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
            enable_automatic_punctuation=True,
            model="latest_short",
            use_enhanced=True,
        )
        
        self.streaming_config = speech.StreamingRecognitionConfig(
            config=self.config,
            interim_results=True,
            single_utterance=False,  # Keep listening
        )
        
    async def start(self):
        """Start the voice session"""
        await self.websocket.send_json({
            "type": "connected",
            "message": "Ready for speech"
        })
        
        # Start audio receiver task
        audio_task = asyncio.create_task(self.receive_audio())
        
        # Start STT in thread (blocking operation)
        stt_thread = threading.Thread(target=self.process_speech)
        stt_thread.daemon = True
        stt_thread.start()
        
        # Wait for audio task to complete
        await audio_task
        
        # Cleanup
        self.is_running = False
        self.audio_queue.put(None)  # Signal end
        stt_thread.join(timeout=1.0)
        
    async def receive_audio(self):
        """Receive audio from WebSocket and queue it"""
        try:
            while self.is_running:
                try:
                    data = await self.websocket.receive_bytes()
                    self.audio_queue.put(data)
                    logger.debug(f"Queued audio: {len(data)} bytes")
                except WebSocketDisconnect:
                    logger.info("WebSocket disconnected")
                    break
                except Exception as e:
                    logger.error(f"Audio receive error: {e}")
                    break
        finally:
            self.is_running = False
            
    def process_speech(self):
        """Process speech in thread"""
        def request_generator():
            """Generate requests for Google STT"""
            while self.is_running:
                try:
                    # Get audio with timeout
                    chunk = self.audio_queue.get(timeout=0.1)
                    if chunk is None:
                        break
                    yield speech.StreamingRecognizeRequest(audio_content=chunk)
                except queue.Empty:
                    # No audio available, but keep trying
                    continue
                except Exception as e:
                    logger.error(f"Request generator error: {e}")
                    break
        
        try:
            logger.info("Starting Google STT streaming")
            responses = self.client.streaming_recognize(
                self.streaming_config,
                request_generator()
            )
            
            for response in responses:
                if not response.results:
                    continue
                    
                for result in response.results:
                    if result.alternatives:
                        asyncio.run_coroutine_threadsafe(
                            self.send_transcript(
                                result.alternatives[0].transcript,
                                result.is_final
                            ),
                            asyncio.get_event_loop()
                        )
                        
        except Exception as e:
            logger.error(f"STT error: {e}")
            asyncio.run_coroutine_threadsafe(
                self.websocket.send_json({
                    "type": "error",
                    "message": str(e)
                }),
                asyncio.get_event_loop()
            )
            
    async def send_transcript(self, text: str, is_final: bool):
        """Send transcript to client"""
        await self.websocket.send_json({
            "type": "transcript",
            "text": text,
            "is_final": is_final
        })
        logger.info(f"Transcript: {text} (final={is_final})")

@router.websocket("/ws")
async def voice_session(websocket: WebSocket):
    """WebSocket endpoint for voice conversation"""
    await websocket.accept()
    logger.info("Fixed Google Voice WebSocket connected")
    
    try:
        handler = GoogleVoiceHandler(websocket)
        await handler.start()
    except Exception as e:
        logger.error(f"Voice session error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    finally:
        logger.info("Voice session ended")

@router.get("/health")
async def health():
    """Health check"""
    return {"status": "ok", "version": "fixed"}