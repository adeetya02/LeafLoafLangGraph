"""
Deepgram Streaming Client with Dynamic Intent Support
Simple STT streaming with dynamic intent learning
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
from src.voice.deepgram.base_client_with_intents import BaseDeepgramClientWithIntents
import structlog

logger = structlog.get_logger()


class DeepgramStreamingClientWithIntents(BaseDeepgramClientWithIntents):
    """Deepgram streaming client with dynamic intent support"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
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
        language: str = "en-US",
        enable_intents: bool = True
    ) -> bool:
        """Connect to Deepgram streaming API with dynamic intent support"""
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
                
                # Extract intent if available (when using extended intent mode)
                intent_info = None
                if hasattr(result, 'alternatives') and result.alternatives:
                    alt = result.alternatives[0]
                    if hasattr(alt, 'intent'):
                        intent_info = {
                            "intent": alt.intent,
                            "confidence": alt.intent_confidence if hasattr(alt, 'intent_confidence') else None
                        }
                
                if transcript:
                    await on_transcript({
                        "transcript": transcript,
                        "is_final": is_final,
                        "confidence": result.channel.alternatives[0].confidence,
                        "timestamp": result.start,
                        "intent_info": intent_info  # Include Deepgram's intent if detected
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
            
            # Add dynamic intents if enabled
            if enable_intents:
                # Enable extended intent mode
                options.intents = "extended"
                
                # Add custom intents from learner
                if self._current_custom_intents:
                    # Custom intents are passed as a list in the 'custom_intents' parameter
                    options.custom_intents = self._current_custom_intents
                    logger.info(f"Added {len(self._current_custom_intents)} custom intents")
                
                # Start intent learning if not already started
                await self.start_intent_learning()
            
            # Start connection
            success = await self.connection.start(options)
            
            if success:
                logger.info(f"Deepgram streaming connected (model: {model}, intents: {enable_intents})")
                return True
            else:
                logger.error("Failed to start Deepgram connection")
                return False
            
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
    
    async def update_custom_intents(self) -> bool:
        """Update custom intents on the fly (if supported by Deepgram)"""
        if not self.connection or not self.is_connected:
            return False
            
        try:
            # Send configuration update message
            update_msg = {
                "type": "Configure",
                "config": {
                    "custom_intents": self._current_custom_intents
                }
            }
            
            await self.connection.send(json.dumps(update_msg))
            logger.info(f"Updated custom intents dynamically: {len(self._current_custom_intents)} patterns")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update custom intents: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from Deepgram"""
        # Stop intent learning
        await self.stop_intent_learning()
        
        # Close connection
        if self.connection:
            await self.connection.finish()
            self.is_connected = False
            logger.info("Deepgram connection closed")