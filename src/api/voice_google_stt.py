"""
Google Cloud Speech-to-Text streaming implementation
Handles real-time speech recognition with multi-language support
"""
import asyncio
import json
from typing import AsyncGenerator, Optional, Dict, Any
from google.cloud import speech
from google.api_core import exceptions
import structlog
from datetime import datetime

logger = structlog.get_logger()

class GoogleSTTHandler:
    """Handles Google Cloud Speech-to-Text streaming"""
    
    def __init__(self):
        try:
            self.client = speech.SpeechClient()
            logger.info("Google Speech-to-Text client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Google STT client: {e}")
            raise
            
        # Multi-language configuration with automatic detection
        self.primary_language = "en-US"
        self.alternative_languages = [
            "es-US",  # Spanish (US)
            "hi-IN",  # Hindi (India)
            "zh-CN",  # Chinese (Simplified)
            "ko-KR",  # Korean
            "en-IN",  # English (India)
            "es-MX",  # Spanish (Mexico)
            "en-GB",  # English (UK)
            "vi-VN",  # Vietnamese
            "tl-PH",  # Filipino/Tagalog
            "ja-JP",  # Japanese
            "ar-SA",  # Arabic (Saudi)
            "fa-IR",  # Persian/Farsi
            "pt-BR",  # Portuguese (Brazil)
            "bn-IN",  # Bengali (India)
            "pa-IN",  # Punjabi (India)
            "ta-IN",  # Tamil (India)
            "ur-PK",  # Urdu (Pakistan)
            "th-TH",  # Thai
            "fr-FR",  # French
            "de-DE",  # German
            "it-IT",  # Italian
            "ru-RU",  # Russian
            "pl-PL",  # Polish
        ]
        
        # Enhanced configuration with multi-language support
        self.config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code=self.primary_language,
            alternative_language_codes=self.alternative_languages[:3],  # Google allows up to 4 total
            # Note: For broader language support, we rotate through alternatives
            # based on detected language in previous interactions
            enable_automatic_punctuation=True,
            enable_word_time_offsets=True,
            enable_word_confidence=True,
            model="latest_short",  # Better for real-time streaming
            use_enhanced=True,  # Better accuracy
            # Speech contexts for grocery-specific terms
            speech_contexts=[
                speech.SpeechContext(
                    phrases=[
                        # Common grocery terms
                        "organic", "gluten-free", "vegan", "vegetarian", "kosher", "halal",
                        # South Asian products
                        "basmati", "atta", "ghee", "paneer", "dal", "masoor", "chana",
                        "garam masala", "turmeric", "cardamom", "methi", "jaggery",
                        # East Asian products  
                        "kimchi", "gochujang", "soy sauce", "miso", "nori", "wasabi",
                        "tofu", "tempeh", "mirin", "sake", "dashi", "kombu", "wakame",
                        "jasmine rice", "sticky rice", "rice noodles", "udon", "soba",
                        # Southeast Asian products
                        "fish sauce", "coconut milk", "lemongrass", "galangal", "kaffir lime",
                        "tamarind", "palm sugar", "rice paper", "pho", "sriracha",
                        # Middle Eastern products
                        "tahini", "hummus", "pita", "falafel", "zaatar", "sumac",
                        "pomegranate molasses", "halva", "labneh", "bulgur", "freekeh",
                        # Latin American products
                        "tortillas", "salsa", "cilantro", "jalapeño", "tamales", "mole",
                        "queso fresco", "chorizo", "adobo", "sofrito", "plantains",
                        # African products
                        "injera", "berbere", "harissa", "couscous", "cassava", "yam",
                        # European products
                        "prosciutto", "mortadella", "pecorino", "gnocchi", "polenta",
                        # Common brands
                        "Oatly", "Silk", "Goya", "Kikkoman", "Lee Kum Kee", "Shan",
                    ],
                    boost=20.0,  # Strong boost for these terms
                ),
                speech.SpeechContext(
                    phrases=[
                        # Multi-lingual greetings
                        "hello", "hola", "namaste", "ni hao", "annyeong", "konnichiwa",
                        "assalamu alaikum", "bonjour", "guten tag", "ciao", "olá",
                        "xin chào", "merhaba", "sawadee", "zdravstvuyte",
                        # Common queries in multiple languages
                        "I need", "show me", "add to cart", "remove", "how much",
                        "मुझे चाहिए", "necesito", "我需要", "필요해요", "私は必要",
                        "أحتاج", "eu preciso", "আমার দরকার", "मला पाहिजे",
                        "എനിക്ക് വേണം", "مجھے چاہیے", "ฉันต้องการ", "j'ai besoin",
                        "ich brauche", "ho bisogno", "мне нужно", "potrzebuję",
                    ],
                    boost=15.0,
                ),
            ],
        )
        
        self.streaming_config = speech.StreamingRecognitionConfig(
            config=self.config,
            interim_results=True,  # Get results while speaking
            single_utterance=False,  # Continuous conversation
        )
        
    async def stream_recognize(self, audio_generator: AsyncGenerator[bytes, None]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process audio stream and yield recognition results
        
        Args:
            audio_generator: Async generator yielding audio chunks
            
        Yields:
            Dictionary with transcript and metadata
        """
        try:
            # Convert async generator to sync using a simple queue and thread
            import queue
            import threading
            
            audio_queue = queue.Queue()
            
            # Thread to collect audio from async generator
            def audio_collector():
                # Create new event loop for this thread
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def collect():
                    try:
                        async for chunk in audio_generator:
                            if chunk:
                                audio_queue.put(chunk)
                                logger.debug(f"Queued audio chunk: {len(chunk)} bytes")
                    except Exception as e:
                        logger.error(f"Audio collection error: {e}")
                    finally:
                        audio_queue.put(None)  # Sentinel
                
                loop.run_until_complete(collect())
                loop.close()
            
            # Start collector thread
            collector_thread = threading.Thread(target=audio_collector, daemon=True)
            collector_thread.start()
            
            # Simple request generator that yields audio as it arrives
            def request_generator():
                logger.info("Starting request generator for Google STT")
                
                request_count = 0
                # Wait for first chunk with longer timeout to ensure audio is flowing
                first_chunk = None
                while first_chunk is None:
                    try:
                        first_chunk = audio_queue.get(timeout=1.0)
                        if first_chunk is None:
                            logger.error("No audio received")
                            return
                    except queue.Empty:
                        logger.debug("Waiting for first audio chunk...")
                        continue
                
                # Yield first chunk immediately
                logger.info("First audio chunk received, starting stream")
                yield speech.StreamingRecognizeRequest(audio_content=first_chunk)
                request_count = 1
                
                # Continue with remaining chunks
                while True:
                    try:
                        # Use shorter timeout for subsequent chunks
                        chunk = audio_queue.get(timeout=0.05)
                        
                        if chunk is None:  # Sentinel value
                            logger.info("End of audio stream")
                            break
                            
                        request_count += 1
                        if request_count % 10 == 0:
                            logger.debug(f"Sent {request_count} audio chunks")
                            
                        yield speech.StreamingRecognizeRequest(audio_content=chunk)
                        
                    except queue.Empty:
                        # For streaming, we should yield empty requests to keep connection alive
                        pass
                    except Exception as e:
                        logger.error(f"Request generator error: {e}")
                        break
                
                logger.info(f"Request generator finished after {request_count} audio requests")
            
            # Process responses - Google API expects config and requests
            logger.info("Starting Google STT streaming_recognize")
            
            # Call streaming_recognize with config and requests as positional args
            responses = self.client.streaming_recognize(
                self.streaming_config,
                request_generator()
            )
            
            for response in responses:
                if not response.results:
                    continue
                    
                # Process each result
                for result in response.results:
                    if not result.alternatives:
                        continue
                        
                    # Get best alternative
                    alternative = result.alternatives[0]
                    
                    # Extract word timings if available
                    words = []
                    if hasattr(alternative, 'words'):
                        words = [
                            {
                                "word": w.word,
                                "start_time": w.start_time.total_seconds() if w.start_time else 0,
                                "end_time": w.end_time.total_seconds() if w.end_time else 0,
                            }
                            for w in alternative.words
                        ]
                    
                    # Extract confidence
                    confidence = alternative.confidence if hasattr(alternative, 'confidence') else 0.0
                    
                    # Extract voice features
                    voice_features = self._extract_voice_features(
                        alternative.transcript,
                        words,
                        confidence
                    )
                    
                    yield {
                        "transcript": alternative.transcript,
                        "is_final": result.is_final,
                        "confidence": confidence,
                        "words": words,
                        "language_code": result.language_code if hasattr(result, 'language_code') else self.primary_language,
                        "timestamp": datetime.utcnow().isoformat(),
                        "voice_features": voice_features,
                        
                        # Backward compatibility
                        "speaking_rate": voice_features["speaking_rate"],
                    }
                    
        except exceptions.DeadlineExceeded:
            logger.warning("Speech recognition deadline exceeded")
            yield {
                "error": "timeout",
                "message": "Speech recognition timed out"
            }
        except Exception as e:
            logger.error(f"Speech recognition error: {e}")
            yield {
                "error": "recognition_failed", 
                "message": str(e)
            }
    
    def _calculate_speaking_rate(self, words: list) -> Optional[float]:
        """Calculate words per minute from word timings"""
        if not words or len(words) < 2:
            return None
            
        # Get duration from first to last word
        duration = words[-1]["end_time"] - words[0]["start_time"]
        if duration <= 0:
            return None
            
        # Calculate words per minute
        wpm = (len(words) / duration) * 60
        return round(wpm, 1)
    
    def _extract_voice_features(self, transcript: str, words: list, confidence: float) -> Dict[str, Any]:
        """Extract voice features for multi-modal analysis"""
        features = {
            "speaking_rate": self._calculate_speaking_rate(words) if words else None,
            "confidence": confidence,
            "word_count": len(transcript.split()) if transcript else 0,
        }
        
        # Analyze speaking patterns for emotion hints
        if features["speaking_rate"]:
            rate = features["speaking_rate"]
            if rate > 180:
                features["pace_indicator"] = "fast"  # Possibly excited or urgent
            elif rate < 120:
                features["pace_indicator"] = "slow"  # Possibly careful or uncertain
            else:
                features["pace_indicator"] = "normal"
        
        # Analyze confidence patterns
        if confidence > 0.9:
            features["clarity"] = "high"
        elif confidence > 0.7:
            features["clarity"] = "medium"
        else:
            features["clarity"] = "low"
        
        # Detect hesitation from word timings
        if words and len(words) > 1:
            pauses = []
            for i in range(1, len(words)):
                gap = words[i]["start_time"] - words[i-1]["end_time"]
                if gap > 0.5:  # More than 500ms pause
                    pauses.append(gap)
            
            features["hesitation_count"] = len(pauses)
            features["max_pause"] = max(pauses) if pauses else 0
        
        return features
    
    async def recognize_once(self, audio_content: bytes) -> Dict[str, Any]:
        """
        Single-shot recognition for testing
        
        Args:
            audio_content: Complete audio data
            
        Returns:
            Recognition result
        """
        try:
            audio = speech.RecognitionAudio(content=audio_content)
            
            response = self.client.recognize(
                config=self.config,
                audio=audio
            )
            
            if not response.results:
                return {
                    "success": False,
                    "message": "No speech detected"
                }
            
            # Get best result
            result = response.results[0]
            alternative = result.alternatives[0]
            
            return {
                "success": True,
                "transcript": alternative.transcript,
                "confidence": alternative.confidence,
                "language_code": result.language_code if hasattr(result, 'language_code') else "en-US"
            }
            
        except Exception as e:
            logger.error(f"Recognition error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def update_language(self, language_code: str):
        """Update primary recognition language while keeping alternatives"""
        self.primary_language = language_code
        
        # Reorder alternatives to prioritize languages similar to the selected one
        language_families = {
            "en": ["en-US", "en-IN", "en-GB"],
            "es": ["es-US", "es-MX"],
            "zh": ["zh-CN", "zh-TW"],
            "hi": ["hi-IN", "en-IN", "pa-IN", "bn-IN"],
            "ko": ["ko-KR"],
            "ja": ["ja-JP"],
            "vi": ["vi-VN"],
            "tl": ["tl-PH", "en-US"],
            "ar": ["ar-SA", "ar-EG"],
            "fa": ["fa-IR"],
            "pt": ["pt-BR", "pt-PT"],
            "bn": ["bn-IN", "hi-IN"],
            "pa": ["pa-IN", "hi-IN"],
            "ta": ["ta-IN", "en-IN"],
            "ur": ["ur-PK", "hi-IN"],
            "th": ["th-TH"],
            "fr": ["fr-FR", "fr-CA"],
            "de": ["de-DE"],
            "it": ["it-IT"],
            "ru": ["ru-RU"],
            "pl": ["pl-PL"],
        }
        
        # Get language family
        lang_family = language_code.split("-")[0]
        prioritized_langs = language_families.get(lang_family, [])
        
        # Build new alternative list
        new_alternatives = []
        # Add languages from same family first
        for lang in prioritized_langs:
            if lang != language_code and lang not in new_alternatives:
                new_alternatives.append(lang)
        
        # Add remaining languages
        for lang in self.alternative_languages:
            if lang != language_code and lang not in new_alternatives:
                new_alternatives.append(lang)
        
        # Update config with new language ordering
        self.config.language_code = language_code
        self.config.alternative_language_codes = new_alternatives[:3]  # Google allows up to 4 total
        
        # Recreate streaming config
        self.streaming_config = speech.StreamingRecognitionConfig(
            config=self.config,
            interim_results=True,
            single_utterance=False,
        )
        
        logger.info(f"Updated STT language to: {language_code} with alternatives: {new_alternatives[:3]}")