"""
Conversation Insights Extraction Pipeline
Captures raw Deepgram data and extracts ML insights for personalization
Updates Graphiti and Spanner with voice-based patterns
"""
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import asyncio
import structlog
from collections import defaultdict

from src.analytics.bigquery_client import BigQueryAnalytics
from src.memory.graphiti_wrapper import GraphitiMemoryWrapper
from src.integrations.spanner_graph_client import SpannerGraphClient

logger = structlog.get_logger()

@dataclass
class RawConversationData:
    """Raw data from Deepgram - everything we capture"""
    session_id: str
    turn_id: str
    timestamp: datetime
    
    # Audio metadata
    audio_duration_ms: float
    audio_format: str = "webm"
    
    # Transcription
    transcript: str
    transcript_confidence: float
    words: List[Dict[str, Any]] = field(default_factory=list)  # word-level timing
    
    # Deepgram Intelligence
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None
    intent: Optional[str] = None
    intent_confidence: Optional[float] = None
    topics: List[str] = field(default_factory=list)
    entities: List[Dict[str, Any]] = field(default_factory=list)
    summary: Optional[str] = None
    detected_language: Optional[str] = None
    
    # Speech characteristics
    speaking_rate_wpm: Optional[float] = None
    silence_ratio: Optional[float] = None
    filler_words_ratio: Optional[float] = None
    
    # Voice characteristics
    pitch_variance: Optional[float] = None  # Future: from audio analysis
    volume_variance: Optional[float] = None
    
    # Conversation context
    is_interruption: bool = False
    previous_turn_sentiment: Optional[str] = None
    turns_in_session: int = 1
    
    def to_bigquery_row(self) -> Dict[str, Any]:
        """Convert to BigQuery row format"""
        return {
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "timestamp": self.timestamp.isoformat(),
            "audio_duration_ms": self.audio_duration_ms,
            "transcript": self.transcript,
            "transcript_confidence": self.transcript_confidence,
            "words": json.dumps(self.words),
            "sentiment": self.sentiment,
            "sentiment_score": self.sentiment_score,
            "intent": self.intent,
            "intent_confidence": self.intent_confidence,
            "topics": self.topics,
            "entities": json.dumps(self.entities),
            "summary": self.summary,
            "detected_language": self.detected_language,
            "speaking_rate_wpm": self.speaking_rate_wpm,
            "silence_ratio": self.silence_ratio,
            "filler_words_ratio": self.filler_words_ratio,
            "is_interruption": self.is_interruption,
            "previous_turn_sentiment": self.previous_turn_sentiment,
            "turns_in_session": self.turns_in_session
        }

@dataclass
class ExtractedInsights:
    """Insights extracted from raw conversation data for ML and personalization"""
    
    # User Communication Style
    communication_style: str = "neutral"  # brief, detailed, conversational, urgent
    emotional_pattern: str = "stable"  # stable, variable, escalating, frustrated
    language_complexity: float = 0.5  # 0-1, simple to complex
    
    # Search Behavior
    search_clarity: float = 0.5  # 0-1, how clear are their searches
    refinement_pattern: str = "none"  # none, clarifying, exploring, struggling
    brand_specificity: float = 0.0  # 0-1, generic to very specific
    
    # Shopping Patterns
    urgency_level: float = 0.0  # 0-1, relaxed to urgent
    decision_speed: str = "normal"  # quick, normal, deliberate, indecisive
    price_sensitivity_indicators: List[str] = field(default_factory=list)
    
    # Satisfaction Indicators
    satisfaction_trajectory: str = "neutral"  # improving, declining, stable
    frustration_triggers: List[str] = field(default_factory=list)
    success_indicators: List[str] = field(default_factory=list)
    
    # Product Discovery
    exploration_style: str = "focused"  # focused, browsing, discovering
    category_confidence: Dict[str, float] = field(default_factory=dict)  # category -> confidence
    problematic_searches: List[str] = field(default_factory=list)
    
    # Personalization Opportunities
    preferred_interaction_length: str = "medium"  # brief, medium, detailed
    needs_guidance: bool = False
    responds_to_suggestions: bool = True
    cultural_indicators: List[str] = field(default_factory=list)  # "uses_hindi_terms", "metric_preference"

class ConversationInsightsExtractor:
    """Extracts insights from raw conversation data"""
    
    def __init__(self):
        self.bigquery = BigQueryAnalytics()
        self.graphiti = GraphitiMemoryWrapper()
        self.spanner = SpannerGraphClient()
        
        # Insight extraction patterns
        self.urgency_indicators = {
            "words": ["need", "urgent", "now", "today", "asap", "running out", "last"],
            "sentiment": ["negative"],
            "speaking_rate": 150  # WPM threshold
        }
        
        self.satisfaction_indicators = {
            "positive": ["perfect", "great", "exactly", "thanks", "yes"],
            "negative": ["no", "wrong", "not what", "frustrated", "confused"]
        }
        
        self.cultural_patterns = {
            "indian": ["sabzi", "dal", "atta", "ghee", "masala", "paneer"],
            "hispanic": ["tortilla", "salsa", "cilantro", "jalapeño"],
            "measurement": ["pounds", "kilos", "dozen", "liters", "gallons"]
        }
    
    async def capture_raw_conversation(
        self,
        session_id: str,
        turn_data: Dict[str, Any],
        audio_metadata: Dict[str, Any]
    ) -> RawConversationData:
        """Capture and store raw conversation data"""
        
        # Create raw data object
        raw_data = RawConversationData(
            session_id=session_id,
            turn_id=turn_data.get("turn_id"),
            timestamp=datetime.utcnow(),
            audio_duration_ms=audio_metadata.get("duration_ms", 0),
            
            # From Deepgram
            transcript=turn_data.get("transcript", ""),
            transcript_confidence=turn_data.get("confidence", 0.0),
            words=turn_data.get("words", []),
            
            # Intelligence features
            sentiment=turn_data.get("sentiment", {}).get("sentiment"),
            sentiment_score=turn_data.get("sentiment", {}).get("confidence"),
            intent=turn_data.get("intents", [{}])[0].get("intent") if turn_data.get("intents") else None,
            intent_confidence=turn_data.get("intents", [{}])[0].get("confidence") if turn_data.get("intents") else None,
            topics=[t.get("topic") for t in turn_data.get("topics", [])],
            entities=turn_data.get("entities", []),
            summary=turn_data.get("summaries", [{}])[0].get("summary") if turn_data.get("summaries") else None,
            detected_language=turn_data.get("detected_language"),
            
            # Speech characteristics
            speaking_rate_wpm=self._calculate_speaking_rate(turn_data.get("words", [])),
            silence_ratio=self._calculate_silence_ratio(turn_data.get("words", [])),
            filler_words_ratio=self._calculate_filler_ratio(turn_data.get("words", []))
        )
        
        # Store raw data immediately
        await self._store_raw_data(raw_data)
        
        return raw_data
    
    async def extract_insights(
        self,
        user_id: str,
        session_data: List[RawConversationData]
    ) -> ExtractedInsights:
        """Extract insights from a conversation session"""
        
        insights = ExtractedInsights()
        
        # Analyze communication style
        insights.communication_style = self._analyze_communication_style(session_data)
        insights.emotional_pattern = self._analyze_emotional_pattern(session_data)
        insights.language_complexity = self._calculate_language_complexity(session_data)
        
        # Analyze search behavior
        insights.search_clarity = self._analyze_search_clarity(session_data)
        insights.refinement_pattern = self._detect_refinement_pattern(session_data)
        insights.brand_specificity = self._calculate_brand_specificity(session_data)
        
        # Analyze shopping patterns
        insights.urgency_level = self._calculate_urgency(session_data)
        insights.decision_speed = self._analyze_decision_speed(session_data)
        insights.price_sensitivity_indicators = self._detect_price_sensitivity(session_data)
        
        # Analyze satisfaction
        insights.satisfaction_trajectory = self._analyze_satisfaction_trajectory(session_data)
        insights.frustration_triggers = self._identify_frustration_triggers(session_data)
        insights.success_indicators = self._identify_success_indicators(session_data)
        
        # Analyze product discovery
        insights.exploration_style = self._analyze_exploration_style(session_data)
        insights.category_confidence = self._calculate_category_confidence(session_data)
        insights.problematic_searches = self._identify_problematic_searches(session_data)
        
        # Personalization opportunities
        insights.preferred_interaction_length = self._determine_interaction_preference(session_data)
        insights.needs_guidance = self._assess_guidance_needs(session_data)
        insights.cultural_indicators = self._detect_cultural_indicators(session_data)
        
        # Update systems with insights
        await self._update_graphiti(user_id, insights)
        await self._update_spanner(user_id, insights)
        await self._queue_ml_features(user_id, session_data, insights)
        
        return insights
    
    def _calculate_speaking_rate(self, words: List[Dict]) -> float:
        """Calculate words per minute"""
        if not words or len(words) < 2:
            return 0.0
            
        duration = words[-1]["end"] - words[0]["start"]
        return (len(words) / duration) * 60 if duration > 0 else 0.0
    
    def _calculate_silence_ratio(self, words: List[Dict]) -> float:
        """Calculate ratio of silence in speech"""
        if not words or len(words) < 2:
            return 0.0
            
        total_duration = words[-1]["end"] - words[0]["start"]
        speech_duration = sum(w["end"] - w["start"] for w in words)
        
        return 1 - (speech_duration / total_duration) if total_duration > 0 else 0.0
    
    def _calculate_filler_ratio(self, words: List[Dict]) -> float:
        """Calculate ratio of filler words"""
        if not words:
            return 0.0
            
        filler_words = {"um", "uh", "like", "you know", "so", "well"}
        filler_count = sum(1 for w in words if w.get("word", "").lower() in filler_words)
        
        return filler_count / len(words)
    
    def _analyze_communication_style(self, session_data: List[RawConversationData]) -> str:
        """Determine user's communication style"""
        if not session_data:
            return "neutral"
            
        # Average transcript length
        avg_length = sum(len(d.transcript.split()) for d in session_data) / len(session_data)
        
        # Speaking rate
        avg_rate = sum(d.speaking_rate_wpm or 0 for d in session_data) / len(session_data)
        
        # Decision logic
        if avg_length < 5 and avg_rate > 150:
            return "brief"
        elif avg_length > 20:
            return "detailed"
        elif any(d.sentiment == "negative" and d.speaking_rate_wpm > 160 for d in session_data):
            return "urgent"
        else:
            return "conversational"
    
    def _analyze_emotional_pattern(self, session_data: List[RawConversationData]) -> str:
        """Analyze emotional patterns throughout conversation"""
        if not session_data:
            return "stable"
            
        sentiments = [d.sentiment for d in session_data if d.sentiment]
        
        if not sentiments:
            return "stable"
            
        # Check for escalation
        if sentiments[:len(sentiments)//2].count("positive") > sentiments[len(sentiments)//2:].count("positive"):
            return "declining"
        elif sentiments[:len(sentiments)//2].count("negative") > sentiments[len(sentiments)//2:].count("negative"):
            return "improving"
        elif sentiments.count("negative") > len(sentiments) * 0.6:
            return "frustrated"
        else:
            return "stable"
    
    def _analyze_search_clarity(self, session_data: List[RawConversationData]) -> float:
        """Analyze how clear user's searches are"""
        if not session_data:
            return 0.5
            
        clarity_scores = []
        
        for data in session_data:
            score = 0.0
            
            # High confidence transcription
            score += data.transcript_confidence * 0.3
            
            # Clear intent
            if data.intent_confidence and data.intent_confidence > 0.8:
                score += 0.3
                
            # Specific entities
            if data.entities:
                score += min(len(data.entities) * 0.1, 0.4)
                
            clarity_scores.append(score)
            
        return sum(clarity_scores) / len(clarity_scores)
    
    def _calculate_urgency(self, session_data: List[RawConversationData]) -> float:
        """Calculate overall urgency level"""
        if not session_data:
            return 0.0
            
        urgency_score = 0.0
        
        for data in session_data:
            turn_urgency = 0.0
            
            # Check urgency words
            transcript_lower = data.transcript.lower()
            for word in self.urgency_indicators["words"]:
                if word in transcript_lower:
                    turn_urgency += 0.1
                    
            # Sentiment factor
            if data.sentiment == "negative":
                turn_urgency += 0.2
                
            # Speaking rate factor
            if data.speaking_rate_wpm and data.speaking_rate_wpm > self.urgency_indicators["speaking_rate"]:
                turn_urgency += 0.2
                
            urgency_score += min(turn_urgency, 1.0)
            
        return min(urgency_score / len(session_data), 1.0)
    
    def _detect_cultural_indicators(self, session_data: List[RawConversationData]) -> List[str]:
        """Detect cultural and linguistic patterns"""
        indicators = set()
        
        for data in session_data:
            transcript_lower = data.transcript.lower()
            
            # Check cultural terms
            for culture, terms in self.cultural_patterns.items():
                if any(term in transcript_lower for term in terms):
                    indicators.add(f"{culture}_terms")
                    
            # Language mixing
            if data.detected_language and data.detected_language != "en":
                indicators.add(f"uses_{data.detected_language}")
                
        return list(indicators)
    
    async def _update_graphiti(self, user_id: str, insights: ExtractedInsights):
        """Update Graphiti with voice-based insights"""
        
        # Create voice profile relationships
        relationships = []
        
        # Communication style
        relationships.append({
            "type": "COMMUNICATES_WITH_STYLE",
            "properties": {
                "style": insights.communication_style,
                "emotional_pattern": insights.emotional_pattern,
                "language_complexity": insights.language_complexity
            }
        })
        
        # Shopping behavior
        relationships.append({
            "type": "SHOPS_WITH_PATTERN",
            "properties": {
                "urgency_typical": insights.urgency_level,
                "decision_speed": insights.decision_speed,
                "exploration_style": insights.exploration_style
            }
        })
        
        # Frustration triggers
        for trigger in insights.frustration_triggers:
            relationships.append({
                "type": "FRUSTRATED_BY",
                "target": trigger,
                "properties": {"frequency": 1}
            })
        
        # Category confidence
        for category, confidence in insights.category_confidence.items():
            if confidence > 0.7:
                relationships.append({
                    "type": "CONFIDENT_IN_CATEGORY",
                    "target": category,
                    "properties": {"confidence": confidence}
                })
            elif confidence < 0.3:
                relationships.append({
                    "type": "STRUGGLES_WITH_CATEGORY",
                    "target": category,
                    "properties": {"confidence": confidence}
                })
        
        # Update Graphiti
        try:
            memory = await self.graphiti.get_memory_instance(user_id)
            for rel in relationships:
                await memory.add_relationship(
                    source_id=user_id,
                    relationship_type=rel["type"],
                    target_id=rel.get("target", "voice_profile"),
                    properties=rel.get("properties", {})
                )
        except Exception as e:
            logger.error(f"Failed to update Graphiti: {e}")
    
    async def _update_spanner(self, user_id: str, insights: ExtractedInsights):
        """Update Spanner with structured voice insights"""
        
        voice_profile = {
            "user_id": user_id,
            "updated_at": datetime.utcnow().isoformat(),
            "communication_style": insights.communication_style,
            "emotional_pattern": insights.emotional_pattern,
            "urgency_level": insights.urgency_level,
            "decision_speed": insights.decision_speed,
            "exploration_style": insights.exploration_style,
            "preferred_interaction_length": insights.preferred_interaction_length,
            "needs_guidance": insights.needs_guidance,
            "satisfaction_trajectory": insights.satisfaction_trajectory,
            "problematic_searches": json.dumps(insights.problematic_searches),
            "cultural_indicators": json.dumps(insights.cultural_indicators)
        }
        
        try:
            await self.spanner.upsert_voice_profile(user_id, voice_profile)
        except Exception as e:
            logger.error(f"Failed to update Spanner: {e}")
    
    async def _queue_ml_features(
        self,
        user_id: str,
        session_data: List[RawConversationData],
        insights: ExtractedInsights
    ):
        """Queue features for ML pipeline"""
        
        features = {
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            
            # Aggregated session features
            "session_length": len(session_data),
            "total_duration_ms": sum(d.audio_duration_ms for d in session_data),
            "avg_speaking_rate": sum(d.speaking_rate_wpm or 0 for d in session_data) / len(session_data),
            "sentiment_changes": len(set(d.sentiment for d in session_data if d.sentiment)),
            
            # Extracted insights
            "communication_style": insights.communication_style,
            "urgency_level": insights.urgency_level,
            "search_clarity": insights.search_clarity,
            "brand_specificity": insights.brand_specificity,
            
            # Success metrics
            "found_products": any(d.intent == "add_to_cart" for d in session_data),
            "completed_order": any(d.intent == "confirm_order" for d in session_data),
            
            # Labels for supervised learning
            "label_satisfaction": insights.satisfaction_trajectory,
            "label_needs_help": insights.needs_guidance
        }
        
        # Queue for ML pipeline
        await self.bigquery.insert_rows(
            table_id="ml_voice_features",
            rows=[features]
        )
    
    async def _store_raw_data(self, raw_data: RawConversationData):
        """Store raw conversation data to BigQuery"""
        await self.bigquery.insert_rows(
            table_id="raw_voice_conversations",
            rows=[raw_data.to_bigquery_row()]
        )