"""
Production-ready voice handler with multiple STT/TTS providers
Handles failures gracefully with automatic fallbacks
"""
import asyncio
import json
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from enum import Enum
import structlog
from dataclasses import dataclass, field
import os

from src.voice.deepgram_nova3_client import DeepgramNova3Client
from src.config.settings import settings

logger = structlog.get_logger()

class STTProvider(Enum):
    """Available Speech-to-Text providers"""
    DEEPGRAM = "deepgram"
    GOOGLE = "google"
    WHISPER = "whisper"

class TTSProvider(Enum):
    """Available Text-to-Speech providers"""
    DEEPGRAM = "deepgram"
    ELEVENLABS = "elevenlabs"
    GOOGLE = "google"

@dataclass
class VoiceConfig:
    """Production voice configuration"""
    # STT settings
    stt_provider: STTProvider = STTProvider.DEEPGRAM
    stt_fallback: Optional[STTProvider] = STTProvider.GOOGLE
    stt_language: str = "en-US"
    stt_model: str = "nova-3"
    
    # TTS settings
    tts_provider: TTSProvider = TTSProvider.ELEVENLABS
    tts_fallback: Optional[TTSProvider] = TTSProvider.DEEPGRAM
    tts_voice: str = "sarah"
    
    # Connection settings
    max_retries: int = 3
    retry_delay: float = 1.0
    connection_timeout: float = 10.0
    keepalive_interval: float = 8.0
    
    # Audio settings
    sample_rate: int = 16000
    channels: int = 1
    encoding: str = "linear16"
    
    # Feature flags
    enable_ethnic_products: bool = True
    enable_interim_results: bool = True
    enable_voice_activity_detection: bool = True
    enable_metrics: bool = True

@dataclass
class ConnectionHealth:
    """Track connection health metrics"""
    provider: str
    connected: bool = False
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    failure_count: int = 0
    success_count: int = 0
    average_latency: float = 0.0
    
    def record_success(self, latency: float = 0.0):
        """Record successful operation"""
        self.last_success = datetime.utcnow()
        self.success_count += 1
        self.connected = True
        self.failure_count = 0  # Reset on success
        
        # Update average latency
        if latency > 0:
            self.average_latency = (
                (self.average_latency * (self.success_count - 1) + latency) 
                / self.success_count
            )
    
    def record_failure(self):
        """Record failed operation"""
        self.last_failure = datetime.utcnow()
        self.failure_count += 1
        self.connected = False
    
    def is_healthy(self) -> bool:
        """Check if provider is healthy"""
        # Consider unhealthy after 3 consecutive failures
        return self.failure_count < 3

class ProductionVoiceHandler:
    """
    Production-ready voice handler with fallbacks and monitoring
    """
    
    def __init__(self, config: Optional[VoiceConfig] = None):
        self.config = config or VoiceConfig()
        
        # Provider health tracking
        self.stt_health: Dict[str, ConnectionHealth] = {
            provider.value: ConnectionHealth(provider.value)
            for provider in STTProvider
        }
        self.tts_health: Dict[str, ConnectionHealth] = {
            provider.value: ConnectionHealth(provider.value)
            for provider in TTSProvider
        }
        
        # Active connections
        self.stt_client = None
        self.tts_client = None
        self.is_connected = False
        
        # Callbacks
        self.on_transcript: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        self.on_metrics: Optional[Callable] = None
        
        # Metrics
        self.session_start = None
        self.transcripts_count = 0
        self.audio_bytes_sent = 0
        self.audio_bytes_received = 0
        
        # Background tasks
        self.health_check_task = None
        self.metrics_task = None
    
    async def connect(
        self,
        on_transcript: Callable,
        on_error: Optional[Callable] = None,
        on_metrics: Optional[Callable] = None
    ) -> bool:
        """
        Connect to voice services with automatic fallback
        """
        self.on_transcript = on_transcript
        self.on_error = on_error
        self.on_metrics = on_metrics
        self.session_start = datetime.utcnow()
        
        # Try primary STT provider
        stt_connected = await self._connect_stt(self.config.stt_provider)
        
        # Try fallback if primary fails
        if not stt_connected and self.config.stt_fallback:
            logger.warning(f"Primary STT {self.config.stt_provider.value} failed, trying fallback")
            stt_connected = await self._connect_stt(self.config.stt_fallback)
        
        if not stt_connected:
            await self._handle_error("Failed to connect to any STT provider")
            return False
        
        self.is_connected = True
        
        # Start background tasks
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        if self.config.enable_metrics:
            self.metrics_task = asyncio.create_task(self._metrics_loop())
        
        logger.info("Production voice handler connected successfully")
        return True
    
    async def _connect_stt(self, provider: STTProvider) -> bool:
        """Connect to specific STT provider"""
        start_time = time.time()
        
        try:
            if provider == STTProvider.DEEPGRAM:
                # Use our Deepgram Nova-3 client
                api_key = os.getenv("DEEPGRAM_API_KEY")
                if not api_key:
                    raise ValueError("DEEPGRAM_API_KEY not configured")
                
                self.stt_client = DeepgramNova3Client(api_key)
                
                # Connect with our production callbacks
                success = await self.stt_client.connect(
                    on_transcript=self._handle_transcript,
                    on_error=self._handle_stt_error,
                    options={
                        "model": self.config.stt_model,
                        "language": self.config.stt_language,
                        "interim_results": self.config.enable_interim_results,
                        "vad_events": self.config.enable_voice_activity_detection
                    }
                )
                
                if success:
                    latency = time.time() - start_time
                    self.stt_health[provider.value].record_success(latency)
                    logger.info(f"Connected to {provider.value} in {latency:.2f}s")
                    return True
                
            elif provider == STTProvider.GOOGLE:
                # TODO: Implement Google STT connection
                logger.warning("Google STT not yet implemented")
                return False
                
            elif provider == STTProvider.WHISPER:
                # TODO: Implement Whisper connection
                logger.warning("Whisper STT not yet implemented")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to {provider.value}: {e}")
            self.stt_health[provider.value].record_failure()
            
        return False
    
    async def send_audio(self, audio_data: bytes) -> bool:
        """
        Send audio data to STT provider
        """
        if not self.is_connected or not self.stt_client:
            return False
        
        try:
            # Track metrics
            self.audio_bytes_sent += len(audio_data)
            
            # Send to active STT client
            if isinstance(self.stt_client, DeepgramNova3Client):
                return await self.stt_client.send_audio(audio_data)
            else:
                # Handle other providers
                return False
                
        except Exception as e:
            logger.error(f"Failed to send audio: {e}")
            await self._handle_error(f"Audio send error: {e}")
            return False
    
    async def synthesize_speech(
        self,
        text: str,
        voice_settings: Optional[Dict[str, Any]] = None
    ) -> Optional[bytes]:
        """
        Convert text to speech with automatic fallback
        """
        # Try primary TTS provider
        audio = await self._synthesize_with_provider(
            self.config.tts_provider,
            text,
            voice_settings
        )
        
        # Try fallback if primary fails
        if not audio and self.config.tts_fallback:
            logger.warning(f"Primary TTS {self.config.tts_provider.value} failed, trying fallback")
            audio = await self._synthesize_with_provider(
                self.config.tts_fallback,
                text,
                voice_settings
            )
        
        if audio:
            self.audio_bytes_received += len(audio)
            
        return audio
    
    async def _synthesize_with_provider(
        self,
        provider: TTSProvider,
        text: str,
        voice_settings: Optional[Dict[str, Any]] = None
    ) -> Optional[bytes]:
        """Synthesize with specific TTS provider"""
        start_time = time.time()
        
        try:
            audio = None
            if provider == TTSProvider.ELEVENLABS:
                # Use ElevenLabs
                from src.integrations.elevenlabs_voice import ElevenLabsClient
                client = ElevenLabsClient()
                audio = await client.text_to_speech(text, voice_settings)
                
            elif provider == TTSProvider.DEEPGRAM:
                # TODO: Implement Deepgram TTS
                logger.warning("Deepgram TTS not yet implemented")
                return None
                
            elif provider == TTSProvider.GOOGLE:
                # TODO: Implement Google TTS
                logger.warning("Google TTS not yet implemented")
                return None
            
            if audio:
                latency = time.time() - start_time
                self.tts_health[provider.value].record_success(latency)
                return audio
                
        except Exception as e:
            logger.error(f"TTS error with {provider.value}: {e}")
            self.tts_health[provider.value].record_failure()
            
        return None
    
    async def disconnect(self):
        """Gracefully disconnect all services"""
        logger.info("Disconnecting production voice handler")
        
        # Cancel background tasks
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
                
        if self.metrics_task:
            self.metrics_task.cancel()
            try:
                await self.metrics_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect STT
        if self.stt_client:
            if isinstance(self.stt_client, DeepgramNova3Client):
                await self.stt_client.disconnect()
            # Handle other providers
        
        self.is_connected = False
        
        # Final metrics
        if self.session_start:
            session_duration = (datetime.utcnow() - self.session_start).total_seconds()
            logger.info(
                "Session summary",
                duration_seconds=session_duration,
                transcripts=self.transcripts_count,
                audio_sent_mb=self.audio_bytes_sent / 1024 / 1024,
                audio_received_mb=self.audio_bytes_received / 1024 / 1024
            )
    
    async def _handle_transcript(self, data: Dict[str, Any]):
        """Handle transcript from STT provider"""
        self.transcripts_count += 1
        
        # Add provider info
        data["provider"] = "deepgram"  # Or detect dynamically
        data["session_metrics"] = {
            "transcripts_count": self.transcripts_count,
            "session_duration": (datetime.utcnow() - self.session_start).total_seconds()
            if self.session_start else 0
        }
        
        if self.on_transcript:
            await self.on_transcript(data)
    
    async def _handle_stt_error(self, error: str):
        """Handle STT errors"""
        current_provider = self._get_current_stt_provider()
        if current_provider:
            self.stt_health[current_provider].record_failure()
        
        await self._handle_error(f"STT error: {error}")
    
    async def _handle_error(self, error: str):
        """Central error handler"""
        logger.error(error)
        if self.on_error:
            await self.on_error(error)
    
    def _get_current_stt_provider(self) -> Optional[str]:
        """Get current STT provider name"""
        if isinstance(self.stt_client, DeepgramNova3Client):
            return STTProvider.DEEPGRAM.value
        # Add other provider checks
        return None
    
    async def _health_check_loop(self):
        """Monitor provider health"""
        while self.is_connected:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                # Log health status
                healthy_stt = [
                    provider for provider, health in self.stt_health.items()
                    if health.is_healthy()
                ]
                healthy_tts = [
                    provider for provider, health in self.tts_health.items()
                    if health.is_healthy()
                ]
                
                logger.debug(
                    "Provider health check",
                    healthy_stt=healthy_stt,
                    healthy_tts=healthy_tts
                )
                
                # TODO: Implement automatic provider switching on health degradation
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
    
    async def _metrics_loop(self):
        """Report metrics periodically"""
        while self.is_connected:
            try:
                await asyncio.sleep(10)  # Report every 10 seconds
                
                if self.on_metrics:
                    metrics = self.get_metrics()
                    await self.on_metrics(metrics)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics error: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current session metrics"""
        session_duration = (
            (datetime.utcnow() - self.session_start).total_seconds()
            if self.session_start else 0
        )
        
        return {
            "session": {
                "duration_seconds": session_duration,
                "transcripts_count": self.transcripts_count,
                "audio_sent_bytes": self.audio_bytes_sent,
                "audio_received_bytes": self.audio_bytes_received,
                "is_connected": self.is_connected
            },
            "providers": {
                "stt": {
                    provider: {
                        "healthy": health.is_healthy(),
                        "connected": health.connected,
                        "success_count": health.success_count,
                        "failure_count": health.failure_count,
                        "average_latency_ms": health.average_latency * 1000
                    }
                    for provider, health in self.stt_health.items()
                },
                "tts": {
                    provider: {
                        "healthy": health.is_healthy(),
                        "connected": health.connected,
                        "success_count": health.success_count,
                        "failure_count": health.failure_count,
                        "average_latency_ms": health.average_latency * 1000
                    }
                    for provider, health in self.tts_health.items()
                }
            }
        }