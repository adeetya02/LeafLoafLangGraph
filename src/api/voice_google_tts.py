"""
Google Cloud Text-to-Speech implementation
Handles speech synthesis with multi-voice support
"""
import asyncio
from typing import Optional, Dict, Any, List
from google.cloud import texttospeech
import structlog
from io import BytesIO
import wave

logger = structlog.get_logger()

class GoogleTTSHandler:
    """Handles Google Cloud Text-to-Speech synthesis"""
    
    # Voice profiles for different languages/accents
    VOICE_PROFILES = {
        "en-US": {
            "default": "en-US-Journey-F",  # More natural Journey voice
            "male": "en-US-Journey-D", 
            "female": "en-US-Journey-F",
            "casual": "en-US-Casual-K",  # Casual conversational voice
            "professional": "en-US-News-N",
            "friendly": "en-US-Journey-F"  # Warm, friendly voice
        },
        "en-IN": {  # Indian English
            "default": "en-IN-Neural2-A",
            "male": "en-IN-Neural2-B",
            "female": "en-IN-Neural2-A"
        },
        "es-US": {  # US Spanish
            "default": "es-US-Neural2-A",
            "male": "es-US-Neural2-B",
            "female": "es-US-Neural2-A"
        },
        "hi-IN": {  # Hindi
            "default": "hi-IN-Neural2-A",
            "male": "hi-IN-Neural2-B",
            "female": "hi-IN-Neural2-A"
        },
        "zh-CN": {  # Mandarin Chinese
            "default": "cmn-CN-Standard-A",
            "male": "cmn-CN-Standard-C",
            "female": "cmn-CN-Standard-A"
        },
        "ko-KR": {  # Korean
            "default": "ko-KR-Neural2-A",
            "male": "ko-KR-Neural2-C",
            "female": "ko-KR-Neural2-A"
        },
        "ja-JP": {  # Japanese
            "default": "ja-JP-Neural2-B",
            "male": "ja-JP-Neural2-C",
            "female": "ja-JP-Neural2-B"
        },
        "vi-VN": {  # Vietnamese
            "default": "vi-VN-Neural2-A",
            "male": "vi-VN-Neural2-D",
            "female": "vi-VN-Neural2-A"
        },
        "ar-SA": {  # Arabic
            "default": "ar-XA-Standard-A",
            "male": "ar-XA-Standard-B",
            "female": "ar-XA-Standard-A"
        },
        "pt-BR": {  # Portuguese (Brazil)
            "default": "pt-BR-Neural2-A",
            "male": "pt-BR-Neural2-B",
            "female": "pt-BR-Neural2-A"
        },
        "bn-IN": {  # Bengali
            "default": "bn-IN-Standard-A",
            "male": "bn-IN-Standard-B",
            "female": "bn-IN-Standard-A"
        },
        "ta-IN": {  # Tamil
            "default": "ta-IN-Standard-A",
            "male": "ta-IN-Standard-B",
            "female": "ta-IN-Standard-A"
        },
        "fr-FR": {  # French
            "default": "fr-FR-Neural2-A",
            "male": "fr-FR-Neural2-B",
            "female": "fr-FR-Neural2-A"
        },
        "de-DE": {  # German
            "default": "de-DE-Neural2-A",
            "male": "de-DE-Neural2-B",
            "female": "de-DE-Neural2-A"
        },
        "it-IT": {  # Italian
            "default": "it-IT-Neural2-A",
            "male": "it-IT-Neural2-C",
            "female": "it-IT-Neural2-A"
        },
        "ru-RU": {  # Russian
            "default": "ru-RU-Standard-A",
            "male": "ru-RU-Standard-B",
            "female": "ru-RU-Standard-A"
        },
        "th-TH": {  # Thai
            "default": "th-TH-Standard-A",
            "male": "th-TH-Neural2-C",
            "female": "th-TH-Standard-A"
        }
    }
    
    def __init__(self, language_code: str = "en-US", voice_type: str = "default"):
        try:
            self.client = texttospeech.TextToSpeechClient()
            logger.info("Google Text-to-Speech client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Google TTS client: {e}")
            raise
            
        self.current_language = language_code
        self.current_voice_type = voice_type
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=24000,  # Higher sample rate for better quality
            # effects_profile_id=["small-bluetooth-speaker-class-device"]  # Optimize for speakers
        )
        
    def get_voice_name(self, language_code: Optional[str] = None, voice_type: Optional[str] = None) -> str:
        """Get appropriate voice name for language and type"""
        lang = language_code or self.current_language
        vtype = voice_type or self.current_voice_type
        
        # Fallback to en-US if language not supported
        if lang not in self.VOICE_PROFILES:
            logger.warning(f"Language {lang} not configured, using en-US")
            lang = "en-US"
            
        voices = self.VOICE_PROFILES[lang]
        
        # Get voice or fallback to default
        voice_name = voices.get(vtype, voices["default"])
        logger.info(f"Selected voice: {voice_name} for {lang}/{vtype}")
        
        return voice_name
    
    async def synthesize(
        self, 
        text: str, 
        language_code: Optional[str] = None,
        voice_type: Optional[str] = None,
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
        use_ssml: bool = False
    ) -> bytes:
        """
        Synthesize text to speech
        
        Args:
            text: Text to synthesize (or SSML if use_ssml=True)
            language_code: Language code (e.g., "en-US", "es-US", "hi-IN")
            voice_type: Voice type (default, male, female, casual, professional)
            speaking_rate: Speed of speech (0.25 to 4.0, 1.0 is normal)
            pitch: Voice pitch (-20.0 to 20.0 semitones)
            use_ssml: Whether text contains SSML markup
            
        Returns:
            Audio data as bytes (16-bit PCM, 16kHz)
        """
        try:
            # Prepare synthesis input
            if use_ssml:
                synthesis_input = texttospeech.SynthesisInput(ssml=text)
            else:
                synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Get voice name
            voice_name = self.get_voice_name(language_code, voice_type)
            lang_code = language_code or self.current_language
            
            # Voice selection
            voice = texttospeech.VoiceSelectionParams(
                language_code=lang_code,
                name=voice_name
            )
            
            # Audio configuration with custom parameters
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                sample_rate_hertz=24000,  # Higher quality
                speaking_rate=speaking_rate,
                pitch=pitch,
                volume_gain_db=0.0  # Normal volume
            )
            
            # Perform synthesis
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.synthesize_speech(
                    input=synthesis_input,
                    voice=voice,
                    audio_config=audio_config
                )
            )
            
            logger.info(f"Synthesized {len(text)} chars to {len(response.audio_content)} bytes")
            return response.audio_content
            
        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")
            raise
    
    async def synthesize_ssml(self, ssml: str, language_code: Optional[str] = None) -> bytes:
        """
        Synthesize SSML markup for more natural speech
        
        Example SSML:
        <speak>
            Hello! <break time="500ms"/>
            Your order contains <emphasis level="strong">5 items</emphasis>.
            <prosody rate="slow">Should I confirm this?</prosody>
        </speak>
        """
        return await self.synthesize(ssml, language_code=language_code, use_ssml=True)
    
    def create_conversational_ssml(self, text: str, style: str = "normal", language_code: Optional[str] = None) -> str:
        """
        Create SSML for more natural conversation with cultural awareness
        
        Args:
            text: Plain text to convert
            style: Conversation style (normal, friendly, professional, empathetic)
            language_code: Language for cultural adaptation
            
        Returns:
            SSML markup
        """
        # Adapt text for cultural context
        adapted_text = self._adapt_text_for_culture(text, language_code or self.current_language)
        
        ssml = "<speak>"
        
        if style == "friendly":
            # Add slight pitch increase and rate for friendliness
            ssml += f'<prosody pitch="+1st" rate="1.05">{adapted_text}</prosody>'
        elif style == "empathetic":
            # Slower rate, lower pitch for empathy
            ssml += f'<prosody pitch="-1st" rate="0.95">{adapted_text}</prosody>'
        elif style == "professional":
            # Clear, moderate pace
            ssml += f'<prosody rate="0.98">{adapted_text}</prosody>'
        elif style == "excited":
            # For promotions or special offers
            ssml += f'<prosody pitch="+2st" rate="1.1" volume="+2dB">{adapted_text}</prosody>'
        else:
            ssml += adapted_text
            
        ssml += "</speak>"
        return ssml
    
    def _adapt_text_for_culture(self, text: str, language_code: str) -> str:
        """Adapt text with cultural awareness and product name pronunciation"""
        # Product name adaptations for better pronunciation
        product_adaptations = {
            "en-IN": {
                "atta": '<say-as interpret-as="verbatim">atta</say-as>',
                "dal": '<phoneme alphabet="ipa" ph="dɑːl">dal</phoneme>',
                "ghee": '<phoneme alphabet="ipa" ph="ɡiː">ghee</phoneme>',
                "paneer": '<phoneme alphabet="ipa" ph="pəˈnɪər">paneer</phoneme>',
                "basmati": '<say-as interpret-as="verbatim">basmati</say-as>',
            },
            "es-US": {
                "jalapeño": '<phoneme alphabet="ipa" ph="xalaˈpeɲo">jalapeño</phoneme>',
                "cilantro": '<say-as interpret-as="verbatim">cilantro</say-as>',
                "tortilla": '<phoneme alphabet="ipa" ph="torˈtiʎa">tortilla</phoneme>',
            },
            "ko-KR": {
                "kimchi": '<phoneme alphabet="ipa" ph="kimtɕʰi">kimchi</phoneme>',
                "gochujang": '<phoneme alphabet="ipa" ph="kotɕʰudʑaŋ">gochujang</phoneme>',
            },
            "zh-CN": {
                "tofu": '<phoneme alphabet="ipa" ph="tou˥˩fu˩">tofu</phoneme>',
                "bok choy": '<say-as interpret-as="verbatim">bok choy</say-as>',
            },
            "ja-JP": {
                "miso": '<phoneme alphabet="ipa" ph="miꜜso">miso</phoneme>',
                "wasabi": '<phoneme alphabet="ipa" ph="wasabi">wasabi</phoneme>',
                "sake": '<phoneme alphabet="ipa" ph="sake">sake</phoneme>',
            },
            "vi-VN": {
                "pho": '<phoneme alphabet="ipa" ph="fəː˧˩">pho</phoneme>',
                "banh mi": '<say-as interpret-as="verbatim">banh mi</say-as>',
            },
            "ar-SA": {
                "tahini": '<phoneme alphabet="ipa" ph="tˤaħiːna">tahini</phoneme>',
                "zaatar": '<phoneme alphabet="ipa" ph="zaʕtar">zaatar</phoneme>',
                "halva": '<phoneme alphabet="ipa" ph="ħalwa">halva</phoneme>',
            },
            "pt-BR": {
                "açaí": '<phoneme alphabet="ipa" ph="asaˈi">açaí</phoneme>',
                "pão de queijo": '<say-as interpret-as="verbatim">pão de queijo</say-as>',
            },
            "th-TH": {
                "pad thai": '<say-as interpret-as="verbatim">pad thai</say-as>',
                "tom yum": '<say-as interpret-as="verbatim">tom yum</say-as>',
            }
        }
        
        # Apply adaptations for the current language
        adaptations = product_adaptations.get(language_code, {})
        adapted_text = text
        
        for product, pronunciation in adaptations.items():
            if product.lower() in adapted_text.lower():
                # Case-insensitive replacement
                import re
                adapted_text = re.sub(
                    re.escape(product), 
                    pronunciation, 
                    adapted_text, 
                    flags=re.IGNORECASE
                )
        
        # AI-first approach: Cultural adaptations should be done by LLM
        # based on full context, not hardcoded patterns
        # TODO: Let supervisor/LLM handle cultural text adaptations
        
        return adapted_text
    
    async def list_voices(self, language_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available voices for a language"""
        try:
            response = self.client.list_voices(language_code=language_code)
            
            voices = []
            for voice in response.voices:
                voices.append({
                    "name": voice.name,
                    "language_codes": voice.language_codes,
                    "gender": voice.ssml_gender.name,
                    "sample_rate": voice.natural_sample_rate_hertz
                })
                
            return voices
            
        except Exception as e:
            logger.error(f"Error listing voices: {e}")
            return []
    
    def set_default_voice(self, language_code: str, voice_type: str = "default"):
        """Update default voice settings"""
        self.current_language = language_code
        self.current_voice_type = voice_type
        logger.info(f"Updated default voice to {language_code}/{voice_type}")
    
    def save_audio_to_wav(self, audio_content: bytes, filename: str):
        """Save audio content to WAV file for testing"""
        with wave.open(filename, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(16000)  # 16kHz
            wav_file.writeframes(audio_content)
    
    def select_voice_for_context(self, text: str, language_code: str, voice_features: Optional[Dict[str, Any]] = None) -> str:
        """
        Select voice based on LLM analysis of context
        
        Args:
            text: Text to be spoken
            language_code: Detected or selected language
            voice_features: Voice features from STT (pace, clarity, etc.)
            
        Returns:
            Appropriate voice type
        """
        # AI-first approach: Let the LLM decide based on full context
        # For now, return default until LLM integration is complete
        # TODO: Pass to supervisor/LLM for voice selection
        # voice_context = {
        #     "response_text": text,
        #     "language": language_code,
        #     "user_voice_features": voice_features,
        #     "available_voices": list(self.VOICE_PROFILES.get(language_code, {}).keys())
        # }
        # voice_type = await llm.analyze_voice_context(voice_context)
        
        return "default"
    
    def detect_emotion_from_text(self, text: str) -> str:
        """Emotion detection delegated to LLM"""
        # AI-first approach: Let the LLM analyze emotion
        # TODO: Integrate with supervisor/LLM for emotion analysis
        # emotion_context = {
        #     "text": text,
        #     "conversation_history": self.conversation_history
        # }
        # emotion = await llm.analyze_emotion(emotion_context)
        
        return "neutral"