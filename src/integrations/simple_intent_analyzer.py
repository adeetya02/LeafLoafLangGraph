"""
Simple intent analyzer that works without external LLMs
"""
import json
import re
from typing import Dict, Any

class SimpleIntentAnalyzer:
    """Rule-based intent analyzer as ultimate fallback"""
    
    def generate_content(self, prompt: str) -> Any:
        """Analyze prompt and extract intent using rules"""
        
        # Extract the query from the prompt
        query_match = re.search(r'User said: "([^"]+)"', prompt)
        if not query_match:
            query_match = re.search(r'"([^"]+)"', prompt)
        
        query = query_match.group(1).lower() if query_match else prompt.lower()
        
        # Analyze intent
        result = self._analyze_query(query)
        
        # Return in expected format
        class Response:
            def __init__(self, text):
                self.text = text
        
        return Response(json.dumps(result))
    
    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """Simple rule-based intent analysis"""
        
        # Greeting patterns
        if any(word in query for word in ['hello', 'hi', 'hey', 'good morning', 'good afternoon']):
            return {
                "intent": "general_chat",
                "confidence": 0.95,
                "search_alpha": 0.5,
                "urgency": "low",
                "response_style": "friendly",
                "reasoning": "Greeting detected",
                "voice_synthesis": {
                    "voice_type": "friendly",
                    "emotion": "welcoming",
                    "speaking_rate": 1.0,
                    "pitch_adjustment": 0.5,
                    "cultural_adaptation": "greeting",
                    "adapted_text": None
                }
            }
        
        # Cart operations
        if any(word in query for word in ['add', 'put', 'place']) and any(word in query for word in ['cart', 'basket', 'order']):
            return {
                "intent": "add_to_order",
                "confidence": 0.9,
                "search_alpha": 0.3,
                "urgency": "medium",
                "response_style": "brief",
                "reasoning": "Add to cart intent detected",
                "voice_synthesis": {
                    "voice_type": "professional",
                    "emotion": "neutral",
                    "speaking_rate": 1.0,
                    "pitch_adjustment": 0.0,
                    "cultural_adaptation": "none",
                    "adapted_text": None
                }
            }
        
        # View cart
        if any(phrase in query for phrase in ['show cart', 'view cart', 'what\'s in my', 'check my order']):
            return {
                "intent": "list_order",
                "confidence": 0.95,
                "search_alpha": 0.5,
                "urgency": "medium",
                "response_style": "detailed",
                "reasoning": "View cart request",
                "voice_synthesis": {
                    "voice_type": "professional",
                    "emotion": "informative",
                    "speaking_rate": 1.0,
                    "pitch_adjustment": 0.0,
                    "cultural_adaptation": "none",
                    "adapted_text": None
                }
            }
        
        # Checkout
        if any(word in query for word in ['checkout', 'confirm', 'place order', 'buy']):
            return {
                "intent": "confirm_order",
                "confidence": 0.9,
                "search_alpha": 0.5,
                "urgency": "high",
                "response_style": "detailed",
                "reasoning": "Checkout intent detected",
                "voice_synthesis": {
                    "voice_type": "professional",
                    "emotion": "neutral",
                    "speaking_rate": 0.95,
                    "pitch_adjustment": 0.0,
                    "cultural_adaptation": "none",
                    "adapted_text": None
                }
            }
        
        # Default to product search
        return {
            "intent": "product_search",
            "confidence": 0.8,
            "search_alpha": 0.5,
            "urgency": "medium",
            "response_style": "normal",
            "reasoning": "Default to product search",
            "voice_synthesis": {
                "voice_type": "default",
                "emotion": "neutral",
                "speaking_rate": 1.0,
                "pitch_adjustment": 0.0,
                "cultural_adaptation": "none",
                "adapted_text": None
            }
        }