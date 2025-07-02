"""
Simplified Google Cloud Speech-to-Text streaming implementation
Direct approach without complex threading
"""
import asyncio
import json
from typing import AsyncGenerator, Dict, Any
from google.cloud import speech
import structlog
from datetime import datetime

logger = structlog.get_logger()

class SimpleGoogleSTT:
    """Simplified Google STT handler"""
    
    def __init__(self):
        self.client = speech.SpeechClient()
        
        # Basic config for real-time streaming
        self.config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
            enable_automatic_punctuation=True,
        )
        
        self.streaming_config = speech.StreamingRecognitionConfig(
            config=self.config,
            interim_results=True,
        )
    
    async def process_stream(self, websocket) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process WebSocket audio stream directly
        """
        try:
            # Create a synchronous generator for the API
            def request_generator():
                # Send audio chunks as they arrive (config passed separately)
                while True:
                    try:
                        # This is a blocking call in a thread
                        audio_data = asyncio.run_coroutine_threadsafe(
                            websocket.receive_bytes(),
                            asyncio.get_event_loop()
                        ).result(timeout=0.1)
                        
                        yield speech.StreamingRecognizeRequest(
                            audio_content=audio_data
                        )
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.error(f"Error receiving audio: {e}")
                        break
            
            # Process responses - Google API expects config and requests
            responses = self.client.streaming_recognize(
                self.streaming_config,
                request_generator()
            )
            
            # Convert responses to async generator
            for response in responses:
                if not response.results:
                    continue
                
                for result in response.results:
                    if result.alternatives:
                        alternative = result.alternatives[0]
                        yield {
                            "transcript": alternative.transcript,
                            "is_final": result.is_final,
                            "confidence": getattr(alternative, 'confidence', 0.0),
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                        
        except Exception as e:
            logger.error(f"STT streaming error: {e}")
            yield {
                "error": "streaming_failed",
                "message": str(e)
            }