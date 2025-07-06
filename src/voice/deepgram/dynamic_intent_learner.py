"""
Dynamic Intent Learning System
Learns from supervisor's intent classifications to improve Deepgram custom intents
"""
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import structlog

logger = structlog.get_logger()


class DynamicIntentLearner:
    """
    Learns intent patterns from supervisor classifications
    No hardcoded mappings - fully dynamic based on actual usage
    """
    
    def __init__(self):
        self.intent_observations = []
        self.transcript_to_intent_patterns = {}
        self.confidence_weighted_patterns = defaultdict(lambda: defaultdict(float))
        
    async def observe_intent(self, transcript: str, intent: str, confidence: float):
        """
        Record an intent classification from the supervisor
        
        Args:
            transcript: The user's spoken text
            intent: The intent determined by supervisor (dynamic, not predefined)
            confidence: Supervisor's confidence in the classification
        """
        # Record the observation
        self.intent_observations.append({
            "transcript": transcript,
            "intent": intent,
            "confidence": confidence,
            "timestamp": datetime.utcnow()
        })
        
        # Extract phrases and update patterns
        phrases = self._extract_phrases(transcript)
        
        for phrase in phrases:
            # Initialize pattern tracking
            if phrase not in self.transcript_to_intent_patterns:
                self.transcript_to_intent_patterns[phrase] = {}
            
            # Count occurrences
            if intent not in self.transcript_to_intent_patterns[phrase]:
                self.transcript_to_intent_patterns[phrase][intent] = 0
            self.transcript_to_intent_patterns[phrase][intent] += 1
            
            # Track confidence-weighted patterns
            self.confidence_weighted_patterns[phrase][intent] += confidence
        
        logger.info(f"Observed intent: '{intent}' for transcript: '{transcript}' (confidence: {confidence})")
    
    def _extract_phrases(self, transcript: str) -> List[str]:
        """
        Extract meaningful phrases from transcript
        No hardcoding - uses n-gram approach
        
        Args:
            transcript: The input text
            
        Returns:
            List of phrases (unigrams, bigrams, trigrams)
        """
        words = transcript.lower().split()
        phrases = []
        
        # Unigrams (single words)
        phrases.extend(words)
        
        # Bigrams (two-word phrases)
        for i in range(len(words) - 1):
            phrases.append(f"{words[i]} {words[i+1]}")
        
        # Trigrams (three-word phrases)
        for i in range(len(words) - 2):
            phrases.append(f"{words[i]} {words[i+1]} {words[i+2]}")
        
        return phrases
    
    def generate_deepgram_custom_intents(self) -> List[str]:
        """
        Generate custom intents for Deepgram based on learned patterns
        
        Returns phrases that strongly correlate with specific intents
        Limited to 100 most predictive phrases (Deepgram's limit)
        """
        predictive_phrases = []
        
        # Analyze each phrase's predictive power
        for phrase, intent_counts in self.transcript_to_intent_patterns.items():
            if not intent_counts:
                continue
                
            # Calculate statistics
            total_occurrences = sum(intent_counts.values())
            
            # Need at least 3 occurrences for statistical significance
            if total_occurrences < 3:
                continue
            
            # Find dominant intent
            dominant_intent = max(intent_counts, key=intent_counts.get)
            dominant_count = intent_counts[dominant_intent]
            
            # Calculate correlation strength
            correlation = dominant_count / total_occurrences
            
            # Include if correlation > 70%
            if correlation > 0.7:
                predictive_phrases.append((phrase, correlation, total_occurrences))
        
        # Sort by correlation strength and occurrence count
        predictive_phrases.sort(key=lambda x: (x[1], x[2]), reverse=True)
        
        # Return top 100 phrases
        return [phrase for phrase, _, _ in predictive_phrases[:100]]
    
    def get_confidence_weighted_patterns(self) -> Dict[str, Dict[str, float]]:
        """
        Get patterns weighted by confidence scores
        
        Returns:
            Dictionary of phrase -> intent -> weighted score
        """
        return dict(self.confidence_weighted_patterns)
    
    def get_intent_statistics(self) -> Dict[str, int]:
        """
        Get statistics about observed intents
        
        Returns:
            Dictionary of intent -> occurrence count
        """
        intent_counts = defaultdict(int)
        for observation in self.intent_observations:
            intent_counts[observation["intent"]] += 1
        return dict(intent_counts)
    
    def get_recent_patterns(self, hours: int = 24) -> List[Tuple[str, str, float]]:
        """
        Get patterns from recent observations
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of (transcript, intent, confidence) tuples
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent = []
        
        for obs in self.intent_observations:
            if obs["timestamp"] > cutoff_time:
                recent.append((
                    obs["transcript"],
                    obs["intent"],
                    obs["confidence"]
                ))
        
        return recent
    
    def suggest_intent_consolidation(self) -> Dict[str, List[str]]:
        """
        Suggest similar intents that could be consolidated
        Based on shared phrases and patterns
        
        Returns:
            Dictionary of potential intent group -> list of similar intents
        """
        # Find intents that share many phrases
        intent_phrases = defaultdict(set)
        
        for phrase, intents in self.transcript_to_intent_patterns.items():
            for intent in intents:
                intent_phrases[intent].add(phrase)
        
        # Find overlapping intents
        suggestions = {}
        processed = set()
        
        for intent1, phrases1 in intent_phrases.items():
            if intent1 in processed:
                continue
                
            similar_intents = []
            
            for intent2, phrases2 in intent_phrases.items():
                if intent1 != intent2 and intent2 not in processed:
                    # Calculate overlap
                    overlap = len(phrases1.intersection(phrases2))
                    union = len(phrases1.union(phrases2))
                    
                    if union > 0 and overlap / union > 0.5:  # 50% similarity
                        similar_intents.append(intent2)
                        processed.add(intent2)
            
            if similar_intents:
                processed.add(intent1)
                group_name = f"group_{intent1}"
                suggestions[group_name] = [intent1] + similar_intents
        
        return suggestions


# Add missing import
from datetime import timedelta