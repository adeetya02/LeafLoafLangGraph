"""
Conversation Memory - Tracks full conversation context
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import structlog

logger = structlog.get_logger()

class ConversationMemory:
    """Manages conversation history and context"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.turns = []
        self.context = {
            "start_time": datetime.utcnow(),
            "user_preferences": {},
            "detected_patterns": {},
            "conversation_summary": "",
            "key_topics": [],
            "sentiment_trajectory": []
        }
        
    async def add_turn(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """Add a conversation turn"""
        turn = {
            "turn_id": len(self.turns) + 1,
            "timestamp": datetime.utcnow().isoformat(),
            "role": role,
            "content": content,
            "metadata": metadata or {}
        }
        
        self.turns.append(turn)
        
        # Update context based on turn
        if role == "user" and metadata:
            await self._update_context_from_turn(turn)
            
    async def _update_context_from_turn(self, turn: Dict):
        """Update conversation context from turn"""
        metadata = turn.get("metadata", {})
        
        # Update sentiment trajectory
        if "audio_intelligence" in metadata:
            intelligence = metadata["audio_intelligence"]
            if intelligence.get("sentiment"):
                self.context["sentiment_trajectory"].append({
                    "turn": turn["turn_id"],
                    "sentiment": intelligence["sentiment"],
                    "score": intelligence.get("sentiment_score", 0)
                })
                
        # Extract preferences
        if "strategy" in metadata:
            strategy = metadata["strategy"]
            if strategy.get("flow") == "shopping":
                # Track what user is shopping for
                self._extract_shopping_preferences(turn["content"])
                
        # Update key topics
        if "audio_intelligence" in metadata:
            topics = metadata["audio_intelligence"].get("topics", [])
            for topic in topics:
                if topic not in self.context["key_topics"]:
                    self.context["key_topics"].append(topic)
                    
    def _extract_shopping_preferences(self, content: str):
        """Extract shopping preferences from content"""
        content_lower = content.lower()
        
        # Dietary preferences
        dietary_keywords = {
            "organic": "prefers_organic",
            "gluten-free": "gluten_free",
            "vegan": "vegan",
            "vegetarian": "vegetarian",
            "sugar-free": "sugar_free",
            "low-sodium": "low_sodium"
        }
        
        for keyword, pref in dietary_keywords.items():
            if keyword in content_lower:
                self.context["user_preferences"][pref] = True
                
        # Brand preferences
        # Would need actual brand list
        
        # Price sensitivity
        if any(word in content_lower for word in ["cheap", "budget", "save"]):
            self.context["user_preferences"]["price_sensitive"] = True
        elif any(word in content_lower for word in ["best", "premium", "quality"]):
            self.context["user_preferences"]["quality_focused"] = True
            
    def get_recent_context(self, num_turns: int = 5) -> List[Dict]:
        """Get recent conversation turns"""
        return self.turns[-num_turns:] if self.turns else []
        
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get conversation summary"""
        if not self.turns:
            return {}
            
        user_turns = [t for t in self.turns if t["role"] == "user"]
        assistant_turns = [t for t in self.turns if t["role"] == "assistant"]
        
        # Calculate average sentiment
        avg_sentiment = 0
        if self.context["sentiment_trajectory"]:
            sentiments = self.context["sentiment_trajectory"]
            sentiment_scores = {
                "positive": 1,
                "neutral": 0,
                "negative": -1
            }
            scores = [sentiment_scores.get(s["sentiment"], 0) for s in sentiments]
            avg_sentiment = sum(scores) / len(scores) if scores else 0
            
        return {
            "session_id": self.session_id,
            "duration_seconds": (datetime.utcnow() - self.context["start_time"]).total_seconds(),
            "total_turns": len(self.turns),
            "user_messages": len(user_turns),
            "assistant_messages": len(assistant_turns),
            "key_topics": self.context["key_topics"],
            "user_preferences": self.context["user_preferences"],
            "average_sentiment": avg_sentiment,
            "sentiment_trajectory": self.context["sentiment_trajectory"]
        }
        
    def should_summarize(self) -> bool:
        """Determine if conversation should be summarized"""
        # Summarize every 10 turns or after 5 minutes
        if len(self.turns) % 10 == 0:
            return True
            
        duration = (datetime.utcnow() - self.context["start_time"]).total_seconds()
        return duration > 300  # 5 minutes
        
    def get_context_for_response(self) -> Dict[str, Any]:
        """Get relevant context for generating response"""
        recent_turns = self.get_recent_context(3)
        
        # Get last user sentiment
        last_sentiment = None
        if self.context["sentiment_trajectory"]:
            last_sentiment = self.context["sentiment_trajectory"][-1]["sentiment"]
            
        # Get conversation flow
        last_user_turn = next(
            (t for t in reversed(self.turns) if t["role"] == "user"), 
            None
        )
        
        flow = "general"
        if last_user_turn and "metadata" in last_user_turn:
            strategy = last_user_turn["metadata"].get("strategy", {})
            flow = strategy.get("flow", "general")
            
        return {
            "recent_turns": recent_turns,
            "user_preferences": self.context["user_preferences"],
            "last_sentiment": last_sentiment,
            "conversation_flow": flow,
            "key_topics": self.context["key_topics"][-3:],  # Last 3 topics
            "turn_count": len(self.turns)
        }