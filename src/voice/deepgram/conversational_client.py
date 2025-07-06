"""
Deepgram Conversational Client
Full duplex STT + TTS for conversational AI
"""
import os
import asyncio
from typing import Optional, Callable, Dict, Any
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
    SpeakOptions,
)
import structlog

logger = structlog.get_logger()

class DeepgramConversationalClient:
    """Full conversational client with STT and TTS"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DEEPGRAM_API_KEY")
        self.client = DeepgramClient(
            self.api_key,
            DeepgramClientOptions(options={"keepalive": "true"})
        )
        self.stt_connection = None
        self.tts_connection = None
        self.is_connected = False
        
    async def connect(
        self,
        on_transcript: Callable,
        on_audio: Callable,
        on_error: Optional[Callable] = None,
        stt_model: str = "nova-2",
        tts_model: str = "aura-asteria-en",
        language: str = "en-US"
    ) -> bool:
        """Connect both STT and TTS for conversation"""
        try:
            # Initialize STT
            self.stt_connection = self.client.listen.asyncwebsocket.v("1")
            
            # STT Event handlers
            @self.stt_connection.on(LiveTranscriptionEvents.Open)
            async def on_stt_open(self, open, **kwargs):
                logger.info("STT connection opened")
            
            @self.stt_connection.on(LiveTranscriptionEvents.Transcript)
            async def on_stt_message(self, result, **kwargs):
                transcript = result.channel.alternatives[0].transcript
                is_final = result.is_final
                
                if transcript:
                    await on_transcript({
                        "transcript": transcript,
                        "is_final": is_final,
                        "confidence": result.channel.alternatives[0].confidence
                    })
            
            @self.stt_connection.on(LiveTranscriptionEvents.UtteranceEnd)
            async def on_utterance_end(self, utterance_end, **kwargs):
                logger.debug("Utterance ended")
                await on_transcript({
                    "event": "utterance_end"
                })
            
            @self.stt_connection.on(LiveTranscriptionEvents.Error)
            async def on_stt_error(self, error, **kwargs):
                logger.error(f"STT error: {error}")
                if on_error:
                    await on_error(f"STT: {error}")
            
            # Configure STT
            stt_options = LiveOptions(
                model=stt_model,
                language=language,
                smart_format=True,
                interim_results=True,
                utterance_end_ms=1000,
                vad_events=True,
                endpointing=300
            )
            
            # Start STT
            if await self.stt_connection.start(stt_options):
                logger.info("STT connection established")
                
                # Initialize TTS
                self.tts_connection = self.client.speak.asyncwebsocket.v("1")
                
                # TTS Event handlers
                self.tts_connection.on("Open", lambda: logger.info("TTS connection opened"))
                self.tts_connection.on("AudioData", lambda data: asyncio.create_task(on_audio(data)))
                self.tts_connection.on("Error", lambda error: logger.error(f"TTS error: {error}"))
                
                # Configure TTS
                tts_options = {
                    "model": tts_model,
                    "encoding": "linear16",
                    "sample_rate": "16000"
                }
                
                # Start TTS
                if await self.tts_connection.start(tts_options):
                    logger.info("TTS connection established")
                    self.is_connected = True
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    async def send_audio(self, audio_data: bytes) -> bool:
        """Send audio to STT"""
        if self.stt_connection and self.is_connected:
            try:
                await self.stt_connection.send(audio_data)
                return True
            except Exception as e:
                logger.error(f"Failed to send audio: {e}")
                return False
        return False
    
    async def speak(self, text: str) -> bool:
        """Send text to TTS"""
        if self.tts_connection and self.is_connected:
            try:
                await self.tts_connection.send_text(text)
                await self.tts_connection.flush()
                return True
            except Exception as e:
                logger.error(f"Failed to speak: {e}")
                return False
        return False
    
    async def disconnect(self):
        """Disconnect both STT and TTS"""
        if self.stt_connection:
            await self.stt_connection.finish()
        if self.tts_connection:
            await self.tts_connection.finish()
        self.is_connected = False
        logger.info("Conversational connections closed")