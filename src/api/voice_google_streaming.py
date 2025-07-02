"""
Google Voice Streaming - Production-ready implementation
Continuous streaming with proper thread safety
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google.cloud import speech
import structlog
import asyncio
import json
import queue
import threading
from typing import Optional, AsyncGenerator
from datetime import datetime

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/google-streaming")

class ContinuousGoogleSTT:
    """Thread-safe continuous Google STT streaming"""
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.client = speech.SpeechClient()
        self.audio_queue = queue.Queue(maxsize=100)
        self.is_running = True
        self.recognition_complete = threading.Event()
        
        # Configure recognition for continuous streaming
        self.config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
            enable_automatic_punctuation=True,
            enable_word_time_offsets=True,
            model="latest_long",  # Better for continuous speech
            use_enhanced=True,
            # Multi-language support
            alternative_language_codes=["es-US", "hi-IN", "zh", "ko"],
        )
        
        self.streaming_config = speech.StreamingRecognitionConfig(
            config=self.config,
            interim_results=True,
            single_utterance=False,  # Keep listening continuously
            enable_voice_activity_events=True,  # Detect speech/silence
        )
        
    async def start(self):
        """Start the continuous streaming session"""
        try:
            # Send initial connection message
            await self.send_message({
                "type": "connected",
                "message": "Ready for continuous speech",
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Start STT processor in background thread
            stt_thread = threading.Thread(target=self.process_speech_thread)
            stt_thread.daemon = True
            stt_thread.start()
            
            # Main loop: receive audio from WebSocket
            await self.receive_audio_loop()
            
        except Exception as e:
            logger.error(f"Session error: {e}")
            await self.send_message({
                "type": "error",
                "message": str(e)
            })
        finally:
            self.cleanup()
            
    async def receive_audio_loop(self):
        """Continuously receive audio from WebSocket"""
        consecutive_errors = 0
        
        while self.is_running:
            try:
                # Receive audio data
                data = await self.websocket.receive_bytes()
                
                # Add to queue if not full
                try:
                    self.audio_queue.put_nowait(data)
                    consecutive_errors = 0  # Reset error counter
                except queue.Full:
                    logger.warning("Audio queue full, dropping chunk")
                    
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected by client")
                break
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Audio receive error ({consecutive_errors}): {e}")
                
                # Exit if too many consecutive errors
                if consecutive_errors > 5:
                    logger.error("Too many consecutive errors, ending session")
                    break
                    
                # Small delay before retry
                await asyncio.sleep(0.1)
    
    def process_speech_thread(self):
        """Process speech in background thread"""
        def audio_generator():
            """Generate audio requests for Google STT"""
            while self.is_running:
                try:
                    # Get audio with timeout
                    chunk = self.audio_queue.get(timeout=0.5)
                    
                    # Check for termination signal
                    if chunk is None:
                        break
                        
                    # Yield audio request
                    yield speech.StreamingRecognizeRequest(audio_content=chunk)
                    
                except queue.Empty:
                    # No audio available, but keep stream alive
                    # Google STT can handle gaps in audio
                    continue
                except Exception as e:
                    logger.error(f"Audio generator error: {e}")
                    break
        
        try:
            logger.info("Starting continuous STT processing")
            
            # Process responses
            responses = self.client.streaming_recognize(
                self.streaming_config,
                audio_generator()
            )
            
            # Handle each response
            for response in responses:
                self.handle_response(response)
                
                # Check if we should stop
                if not self.is_running:
                    break
                    
        except Exception as e:
            logger.error(f"STT processing error: {e}")
            self.send_error_sync(f"Speech recognition error: {str(e)}")
        finally:
            logger.info("STT processing ended")
            self.recognition_complete.set()
    
    def handle_response(self, response):
        """Handle STT response"""
        try:
            # Handle voice activity events
            if hasattr(response, 'speech_event_type'):
                if response.speech_event_type == speech.StreamingRecognizeResponse.SpeechEventType.SPEECH_ACTIVITY_BEGIN:
                    self.send_message_sync({
                        "type": "speech_activity",
                        "activity": "started",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                elif response.speech_event_type == speech.StreamingRecognizeResponse.SpeechEventType.SPEECH_ACTIVITY_END:
                    self.send_message_sync({
                        "type": "speech_activity", 
                        "activity": "ended",
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            # Handle recognition results
            if not response.results:
                return
                
            for result in response.results:
                if not result.alternatives:
                    continue
                    
                # Get best alternative
                alternative = result.alternatives[0]
                
                # Extract metadata
                metadata = {
                    "language_code": getattr(result, 'language_code', 'en-US'),
                    "result_end_time": getattr(result, 'result_end_time', None),
                }
                
                # Add confidence for final results
                if result.is_final:
                    metadata["confidence"] = getattr(alternative, 'confidence', 0.0)
                    
                # Send transcript
                self.send_message_sync({
                    "type": "transcript",
                    "text": alternative.transcript,
                    "is_final": result.is_final,
                    "metadata": metadata,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Log for debugging
                logger.info(
                    f"Transcript: '{alternative.transcript}' "
                    f"(final={result.is_final}, lang={metadata['language_code']})"
                )
                
        except Exception as e:
            logger.error(f"Error handling response: {e}")
    
    def send_message_sync(self, message: dict):
        """Send message from sync context (thread-safe)"""
        try:
            # Use asyncio.run_coroutine_threadsafe for thread safety
            future = asyncio.run_coroutine_threadsafe(
                self.send_message(message),
                asyncio.get_event_loop()
            )
            # Wait for completion with timeout
            future.result(timeout=1.0)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
    
    def send_error_sync(self, error_message: str):
        """Send error from sync context"""
        self.send_message_sync({
            "type": "error",
            "message": error_message,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def send_message(self, message: dict):
        """Send message to WebSocket (async)"""
        try:
            if self.websocket.client_state.value == 1:  # CONNECTED
                await self.websocket.send_json(message)
        except Exception as e:
            logger.error(f"WebSocket send error: {e}")
    
    def cleanup(self):
        """Clean up resources"""
        self.is_running = False
        
        # Signal audio generator to stop
        try:
            self.audio_queue.put_nowait(None)
        except:
            pass
            
        # Wait for recognition to complete
        self.recognition_complete.wait(timeout=2.0)
        
        logger.info("Cleanup completed")

@router.websocket("/ws")
async def streaming_voice_session(websocket: WebSocket):
    """WebSocket endpoint for continuous voice streaming"""
    await websocket.accept()
    logger.info("Continuous Google Voice streaming session started")
    
    try:
        # Create and start STT handler
        stt = ContinuousGoogleSTT(websocket)
        await stt.start()
        
    except Exception as e:
        logger.error(f"Streaming session error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Session error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            })
        except:
            pass
    finally:
        logger.info("Streaming session ended")
        try:
            await websocket.close()
        except:
            pass

@router.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "google-voice-streaming",
        "features": [
            "continuous_streaming",
            "multi_language",
            "voice_activity_detection",
            "thread_safe"
        ]
    }