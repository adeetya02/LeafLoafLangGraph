"""
Deepgram Streaming Client
Simple STT streaming for real-time transcription
"""
import os
import asyncio
import json
from typing import Optional, Callable, Dict, Any
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)
import structlog

logger = structlog.get_logger()

class DeepgramStreamingClient:
    """Simple Deepgram streaming client for STT only"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DEEPGRAM_API_KEY")
        self.client = DeepgramClient(
            self.api_key,
            DeepgramClientOptions(options={"keepalive": "true"})
        )
        self.connection = None
        self.is_connected = False
        
    async def connect(
        self,
        on_transcript: Callable,
        on_error: Optional[Callable] = None,
        model: str = "nova-2",
        language: str = "en-US"
    ) -> bool:
        """Connect to Deepgram streaming API"""
        try:
            # Create websocket connection
            self.connection = self.client.listen.asyncwebsocket.v("1")
            
            # Register event handlers
            @self.connection.on(LiveTranscriptionEvents.Open)
            async def on_open(self, open, **kwargs):
                logger.info("Deepgram connection opened")
                self.is_connected = True
            
            @self.connection.on(LiveTranscriptionEvents.Transcript)
            async def on_message(self, result, **kwargs):
                transcript = result.channel.alternatives[0].transcript
                is_final = result.is_final
                
                if transcript:
                    await on_transcript({
                        "transcript": transcript,
                        "is_final": is_final,
                        "confidence": result.channel.alternatives[0].confidence,
                        "timestamp": result.start
                    })
            
            @self.connection.on(LiveTranscriptionEvents.Error)
            async def on_deepgram_error(self, error, **kwargs):
                logger.error(f"Deepgram error: {error}")
                if on_error:
                    await on_error(str(error))
            
            # Configure options
            options = LiveOptions(
                model=model,
                language=language,
                smart_format=True,
                interim_results=True,
                utterance_end_ms=1000,
                vad_events=True,
                endpointing=300
            )
            
            # Start connection
            await self.connection.start(options)
            return True
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    async def send_audio(self, audio_data: bytes) -> bool:
        """Send audio data to Deepgram"""
        if self.connection and self.is_connected:
            try:
                await self.connection.send(audio_data)
                return True
            except Exception as e:
                logger.error(f"Failed to send audio: {e}")
                return False
        return False
    
    async def disconnect(self):
        """Disconnect from Deepgram"""
        if self.connection:
            await self.connection.finish()
            self.is_connected = False
            logger.info("Deepgram connection closed")