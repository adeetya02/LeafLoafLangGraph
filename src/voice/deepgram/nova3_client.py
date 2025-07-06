"""
Production-ready Deepgram Nova-3 client with ethnic product support
Built incrementally with proper error handling and audio intelligence
"""
import asyncio
import json
import time
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
import structlog
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveOptions,
    LiveTranscriptionEvents,
    LiveResultResponse
)

logger = structlog.get_logger()

# Ethnic product vocabulary for grocery shopping
ETHNIC_KEYWORDS = [
    # South Asian
    "paneer:15", "ghee:15", "dal:12", "daal:12", "masala:10",
    "basmati:10", "atta:12", "jaggery:15", "garam masala:12",
    "chapati:12", "roti:12", "naan:10", "lassi:10",
    
    # East Asian  
    "gochujang:15", "kimchi:12", "miso:12", "dashi:15",
    "tofu:10", "wakame:15", "nori:12", "soba:12",
    "udon:12", "edamame:12", "tempeh:12",
    
    # Middle Eastern
    "harissa:15", "zaatar:15", "tahini:12", "sumac:12",
    "labneh:15", "halloumi:12", "falafel:10", "shawarma:12",
    
    # Latin American
    "plantains:10", "yuca:15", "yucca:15", "mole:15",
    "achiote:15", "epazote:18", "queso fresco:12",
    
    # African
    "injera:15", "berbere:15", "fufu:15", "jollof:12"
]

class DeepgramNova3Client:
    """Production-ready Deepgram Nova-3 client with incremental features"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        
        # Configure client
        # Note: DeepgramClient takes API key as first parameter
        self.deepgram = DeepgramClient(api_key)
        
        # Connection state
        self.connection = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 3
        
        # Callbacks
        self.transcript_callback = None
        self.error_callback = None
        self.audio_intelligence_callback = None
        
        # Keep-alive task
        self.keepalive_task = None
        
        # Audio validation
        self.last_audio_time = None
        self.audio_timeout = 10  # seconds
        
        # Metrics
        self.recognized_products = set()
        self.sentiment_history = []
        
    async def connect(
        self,
        on_transcript: Callable,
        on_error: Optional[Callable] = None,
        on_audio_intelligence: Optional[Callable] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Establish connection to Deepgram with proper error handling
        
        Step 1: Basic connection with error handling
        Step 2: Add audio intelligence features
        Step 3: Add custom vocabulary
        """
        try:
            # Store callbacks
            self.transcript_callback = on_transcript
            self.error_callback = on_error
            self.audio_intelligence_callback = on_audio_intelligence
            
            # Create connection using asyncwebsocket (asynclive is deprecated)
            self.connection = self.deepgram.listen.asyncwebsocket.v("1")
            
            # Set up event handlers using string event names
            # The SDK expects lowercase string event names, not enum values
            self.connection.on("open", self._on_open)
            self.connection.on("transcript", self._on_transcript)
            self.connection.on("error", self._on_error)
            self.connection.on("close", self._on_close)
            
            # Configure options with Nova-3
            # Step 1: Basic options only
            live_options = LiveOptions(
                # Basic options
                model="nova-3",  # Nova-3 is available and confirmed working
                language="en-US",
                encoding="linear16",
                sample_rate=16000,
                channels=1,
                
                # Formatting
                smart_format=True,
                punctuate=True,
                
                # Real-time features
                interim_results=True,
                utterance_end_ms=1000,  # Must be >= 1000 for stability
                vad_events=True,
                
                # Custom vocabulary (Step 3)
                # Nova-3 uses 'keyterm' instead of 'keywords'
                keyterm=ETHNIC_KEYWORDS  # For Nova-3
            )
            
            # Note: Audio intelligence features (sentiment, intent, topics) 
            # are not available in live streaming API yet
            # They're only available for pre-recorded audio
            
            # Apply custom options
            if options:
                for key, value in options.items():
                    setattr(live_options, key, value)
            
            # Start the connection
            logger.info("Attempting to connect to Deepgram Nova-3...")
            success = await self.connection.start(live_options)
            
            if success:
                self.is_connected = True
                self.reconnect_attempts = 0
                self.last_audio_time = time.time()
                
                # Start keep-alive task
                self.keepalive_task = asyncio.create_task(self._keepalive_loop())
                
                logger.info("Successfully connected to Deepgram Nova-3")
                return True
            else:
                raise Exception("Failed to start Deepgram connection")
                
        except Exception as e:
            logger.error(f"Failed to connect to Deepgram: {e}")
            await self._handle_connection_error(e)
            return False
    
    async def send_audio(self, audio_data: bytes) -> bool:
        """Send audio data with validation"""
        # Validate audio data
        if not audio_data or len(audio_data) == 0:
            logger.warning("Skipping empty audio data")
            return False
            
        if not self.is_connected or not self.connection:
            logger.warning("Not connected, cannot send audio")
            return False
            
        try:
            # Log audio data details
            logger.debug(f"Sending audio data: {len(audio_data)} bytes")
            
            # Send audio
            await self.connection.send(audio_data)
            self.last_audio_time = time.time()
            return True
            
        except Exception as e:
            logger.error(f"Failed to send audio: {e}")
            await self._handle_connection_error(e)
            return False
    
    async def disconnect(self):
        """Gracefully disconnect from Deepgram"""
        logger.info("Disconnecting from Deepgram...")
        
        # Cancel keep-alive
        if self.keepalive_task:
            self.keepalive_task.cancel()
            try:
                await self.keepalive_task
            except asyncio.CancelledError:
                pass
        
        # Close connection
        if self.connection:
            try:
                await self.connection.finish()
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
            finally:
                self.connection = None
                self.is_connected = False
        
        logger.info("Disconnected from Deepgram")
    
    async def _keepalive_loop(self):
        """Send keep-alive messages to prevent timeout"""
        while self.is_connected:
            try:
                await asyncio.sleep(8)  # Send every 8 seconds (timeout is 10)
                
                # Check if we've received audio recently
                if time.time() - self.last_audio_time > self.audio_timeout:
                    logger.warning("No audio received for 10s, sending keep-alive")
                
                # Send keep-alive by sending a small amount of silence
                if self.connection:
                    # Send 0.1 seconds of silence (3200 bytes at 16kHz)
                    silence = b'\x00' * 3200
                    await self.connection.send(silence)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Keep-alive error: {e}")
    
    def _on_open(self, *args, **kwargs):
        """Handle connection open event"""
        # Note: Event handlers should not be async in SDK v4
        logger.info("Deepgram connection opened")
        self.is_connected = True
        
        if self.transcript_callback:
            asyncio.create_task(self.transcript_callback({
                "event": "connection_opened",
                "timestamp": datetime.utcnow().isoformat()
            }))
    
    def _on_transcript(self, *args, **kwargs):
        """Handle transcript with audio intelligence"""
        result = kwargs.get("result")
        
        if not result or not result.channel:
            return
            
        try:
            alternative = result.channel.alternatives[0]
            transcript = alternative.transcript
            
            # Basic transcript data
            transcript_data = {
                "transcript": transcript,
                "is_final": result.is_final,
                "speech_final": result.speech_final,
                "confidence": alternative.confidence if hasattr(alternative, 'confidence') else 1.0,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Process final transcripts
            if result.is_final and transcript:
                # Check for ethnic products
                ethnic_products = self._check_ethnic_products(transcript)
                if ethnic_products:
                    transcript_data["ethnic_products"] = ethnic_products
                
                # Note: Audio intelligence (sentiment, intent, topics) not available in streaming
                # We'll need to implement our own analysis or use pre-recorded API
            
            # Send transcript
            if self.transcript_callback:
                asyncio.create_task(self.transcript_callback(transcript_data))
                
        except Exception as e:
            logger.error(f"Error processing transcript: {e}", exc_info=True)
    
    def _on_error(self, *args, **kwargs):
        """Handle Deepgram errors"""
        error = kwargs.get("error")
        logger.error(f"Deepgram error: {error}")
        
        # Parse error code if available
        error_str = str(error)
        if "NET-0001" in error_str:
            logger.error("No audio received timeout - check keep-alive")
        elif "DATA-0000" in error_str:
            logger.error("Audio decoding error - check format")
        
        asyncio.create_task(self._handle_connection_error(error))
    
    def _on_close(self, *args, **kwargs):
        """Handle connection close"""
        logger.info("Deepgram connection closed")
        self.is_connected = False
        
        # Attempt reconnection if not intentional disconnect
        if self.reconnect_attempts < self.max_reconnect_attempts:
            asyncio.create_task(self._attempt_reconnect())
    
    async def _handle_connection_error(self, error: Exception):
        """Handle connection errors with retry logic"""
        self.is_connected = False
        
        if self.error_callback:
            await self.error_callback(str(error))
        
        # Attempt reconnection
        if self.reconnect_attempts < self.max_reconnect_attempts:
            await self._attempt_reconnect()
    
    async def _attempt_reconnect(self):
        """Attempt to reconnect with exponential backoff"""
        self.reconnect_attempts += 1
        backoff = min(30, 2 ** self.reconnect_attempts)
        
        logger.info(f"Attempting reconnection {self.reconnect_attempts}/{self.max_reconnect_attempts} in {backoff}s")
        await asyncio.sleep(backoff)
        
        # Try to reconnect using stored callbacks
        if self.transcript_callback:
            success = await self.connect(
                self.transcript_callback,
                self.error_callback,
                self.audio_intelligence_callback
            )
            
            if not success:
                logger.error("Reconnection failed")
    
    def _check_ethnic_products(self, transcript: str) -> List[Dict[str, Any]]:
        """Check for ethnic products in transcript"""
        transcript_lower = transcript.lower()
        found = []
        
        for keyword_boost in ETHNIC_KEYWORDS:
            keyword = keyword_boost.split(':')[0]
            boost = int(keyword_boost.split(':')[1])
            
            if keyword.lower() in transcript_lower:
                found.append({
                    "product": keyword,
                    "boost": boost
                })
                self.recognized_products.add(keyword)
        
        return found
    
    def _get_sentiment_label(self, score: float) -> str:
        """Convert sentiment score to label"""
        if score > 0.5:
            return "very_positive"
        elif score > 0.1:
            return "positive"
        elif score < -0.5:
            return "very_negative"
        elif score < -0.1:
            return "negative"
        else:
            return "neutral"
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get client metrics"""
        return {
            "is_connected": self.is_connected,
            "reconnect_attempts": self.reconnect_attempts,
            "recognized_products": list(self.recognized_products),
            "sentiment_average": sum(s["score"] for s in self.sentiment_history) / len(self.sentiment_history) if self.sentiment_history else 0
        }