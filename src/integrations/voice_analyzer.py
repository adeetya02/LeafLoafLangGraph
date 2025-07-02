"""
Voice Analysis for tone, emotion, and intent detection
Integrates with 11Labs and speech analysis
"""
import os
from typing import Dict, Optional, Tuple
import structlog
from dataclasses import dataclass

logger = structlog.get_logger()

@dataclass
class VoiceAnalysis:
    """Voice analysis results"""
    text: str
    emotion: str  # happy, sad, angry, neutral, frustrated, excited
    tone: str  # formal, casual, urgent, calm, questioning
    confidence: float
    intent_hints: list  # urgency, confusion, satisfaction
    speech_pace: str  # fast, normal, slow
    volume_level: str  # loud, normal, quiet

class VoiceAnalyzer:
    """Analyze voice for emotional context and intent"""

    def __init__(self):
        self.emotion_keywords = {
            "happy": ["great", "wonderful", "perfect", "love", "awesome", "fantastic"],
            "frustrated": ["again", "still", "why", "come on", "seriously"],
            "urgent": ["quickly", "hurry", "asap", "now", "immediately"],
            "confused": ["what", "which", "how", "don't understand", "unclear"]
        }

    async def analyze_voice_input(
        self,
        audio_data: bytes,
        transcribed_text: str,
        audio_features: Optional[Dict] = None
    ) -> VoiceAnalysis:
        """
        Analyze voice input for emotional context

        Args:
            audio_data: Raw audio bytes
            transcribed_text: Text from STT
            audio_features: Optional audio analysis (pitch, tempo, etc.)

        Returns:
            VoiceAnalysis with emotional context
        """
        # Analyze text for emotional cues
        emotion = self._detect_emotion_from_text(transcribed_text)
        tone = self._detect_tone(transcribed_text)
        intent_hints = self._extract_intent_hints(transcribed_text)

        # If we have audio features (from 11Labs or other service)
        if audio_features:
            # Refine based on audio characteristics
            if audio_features.get("pitch_variance", 0) > 0.7:
                emotion = "excited" if emotion == "happy" else "frustrated"
            if audio_features.get("speech_rate", 1.0) > 1.3:
                tone = "urgent"

        return VoiceAnalysis(
            text=transcribed_text,
            emotion=emotion,
            tone=tone,
            confidence=0.8,  # Would come from actual analysis
            intent_hints=intent_hints,
            speech_pace=audio_features.get("pace", "normal") if audio_features else "normal",
            volume_level=audio_features.get("volume", "normal") if audio_features else "normal"
        )

    def _detect_emotion_from_text(self, text: str) -> str:
        """Detect emotion from text content"""
        text_lower = text.lower()

        # Check for emotion indicators
        for emotion, keywords in self.emotion_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return emotion

        # Check punctuation and patterns
        if "!" in text:
            return "excited"
        elif "?" in text and any(word in text_lower for word in ["why", "how come"]):
            return "confused"
        elif any(word in text_lower for word in ["please", "could you", "would you"]):
            return "polite"

        return "neutral"

    def _detect_tone(self, text: str) -> str:
        """Detect conversational tone"""
        text_lower = text.lower()

        # Urgent indicators
        if any(word in text_lower for word in ["asap", "urgent", "quickly", "hurry"]):
            return "urgent"

        # Casual indicators
        if any(word in text_lower for word in ["hey", "gonna", "wanna", "stuff"]):
            return "casual"

        # Formal indicators
        if any(word in text_lower for word in ["kindly", "please advise", "regarding"]):
            return "formal"

        # Question tone
        if text.strip().endswith("?"):
            return "questioning"

        return "calm"

    def _extract_intent_hints(self, text: str) -> list:
        """Extract hints about user intent from voice/text"""
        hints = []
        text_lower = text.lower()

        # Urgency
        if any(word in text_lower for word in ["quick", "fast", "hurry", "asap"]):
            hints.append("urgency")

        # Confusion
        if text.count("?") > 1 or any(word in text_lower for word in ["confused", "don't get"]):
            hints.append("confusion")

        # Satisfaction
        if any(word in text_lower for word in ["perfect", "great", "exactly"]):
            hints.append("satisfaction")

        # Frustration
        if any(word in text_lower for word in ["again", "still not", "come on"]):
            hints.append("frustration")

        # Browsing vs specific
        if any(word in text_lower for word in ["just looking", "browse", "what do you have"]):
            hints.append("browsing")
        elif any(word in text_lower for word in ["need exactly", "specific", "particular"]):
            hints.append("specific_need")

        return hints

    def adjust_response_style(self, voice_analysis: VoiceAnalysis) -> Dict[str, any]:
        """
        Adjust agent response based on voice analysis

        Returns:
            Response adjustments for agents
        """
        adjustments = {
            "response_style": "normal",
            "urgency_level": "normal",
            "detail_level": "standard",
            "empathy_needed": False,
            "clarification_needed": False
        }

        # Adjust based on emotion
        if voice_analysis.emotion == "frustrated":
            adjustments["response_style"] = "helpful"
            adjustments["empathy_needed"] = True
            adjustments["detail_level"] = "concise"

        elif voice_analysis.emotion == "confused":
            adjustments["response_style"] = "clarifying"
            adjustments["clarification_needed"] = True
            adjustments["detail_level"] = "detailed"

        elif voice_analysis.emotion == "happy":
            adjustments["response_style"] = "friendly"

        # Adjust based on tone
        if voice_analysis.tone == "urgent":
            adjustments["urgency_level"] = "high"
            adjustments["detail_level"] = "minimal"

        elif voice_analysis.tone == "casual":
            adjustments["response_style"] = "conversational"

        # Adjust based on hints
        if "confusion" in voice_analysis.intent_hints:
            adjustments["clarification_needed"] = True

        return adjustments

    def generate_voice_settings(self, voice_analysis: VoiceAnalysis) -> Dict[str, float]:
        """
        Generate 11Labs voice settings based on customer emotion

        Returns:
            Voice settings for 11Labs TTS
        """
        # Default settings
        settings = {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True
        }

        # Adjust based on customer emotion
        if voice_analysis.emotion == "frustrated":
            # More stable, calming voice
            settings["stability"] = 0.7
            settings["style"] = 0.2  # Slightly warmer

        elif voice_analysis.emotion == "excited":
            # Match their energy
            settings["stability"] = 0.4
            settings["style"] = 0.3

        elif voice_analysis.tone == "urgent":
            # Slightly faster, clearer
            settings["stability"] = 0.6
            settings["similarity_boost"] = 0.8

        return settings # type: ignore