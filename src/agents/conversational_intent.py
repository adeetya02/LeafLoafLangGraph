"""
Conversational intent recognition for when LLM is unavailable
"""
import re
from typing import Dict, Any, Optional, List

class ConversationalIntentRecognizer:
    """Recognize intents from conversational language patterns"""
    
    def __init__(self):
        # Expanded patterns for conversational language
        self.patterns = {
            "add_to_order": [
                # Direct additions
                r"\b(add|put|place|throw|toss)\b.*\b(cart|basket|bag|order)\b",
                r"\b(i'?ll|let me|can i|could i|i'd like to)\s+(take|have|get|grab)\b",
                r"\b(give me|get me|grab me|bring me)\b",
                r"\b(want|need|looking for|after)\b.*\b(some|those?|that|them|it)\b",
                
                # Affirmative responses (context-dependent)
                r"^(yes|yeah|yep|sure|ok|okay|alright|sounds? good|perfect|great)(\s|,|!|$)",
                r"^(that'?s? )?(the one|it|them|those|what i need)",
                r"^(i'?ll have|i want|gimme|please)\b",
                
                # Quantity patterns
                r"\b(one|two|three|four|five|\d+)\s+(of\s+)?(those?|them|that)\b",
                r"\b(a couple|a few|some)\s+(of\s+)?(those?|them|that)\b",
            ],
            
            "remove_from_order": [
                r"\b(remove|delete|drop|take out|forget|cancel)\b.*\b(from\s+)?(cart|basket|order|that|it)\b",
                r"\b(don'?t|do not|no longer)\s+(want|need)\b",
                r"\b(actually|wait|hold on),?\s*(no|not|nevermind|forget)\b",
                r"^(no|nope|nah|not that|wrong one)",
            ],
            
            "update_order": [
                r"\b(change|update|modify|make it|switch to)\b",
                r"\b(instead of|rather than|replace)\b",
                r"\b(double|triple|half|increase|decrease)\b.*\b(that|it|order)\b",
                r"\b(more|less|fewer)\s+(of\s+)?(that|those|them)\b",
            ],
            
            "list_order": [
                r"\b(show|what'?s?|list|view|see|check)\b.*\b(cart|basket|order|got|have)\b",
                r"\bmy\s+(cart|basket|order|stuff|items)\b",
                r"\b(how much|what do)\s+(i have|is that)\b",
            ],
            
            "confirm_order": [
                r"\b(confirm|checkout|place|complete|finalize)\b.*\b(order|cart|that)?\b",
                r"\b(that'?s?|i'?m)\s+(all|it|done|good|finished)\b",
                r"\b(ready to|let'?s?)\s+(checkout|pay|order)\b",
                r"^(done|finished|complete|that'?s? everything)$",
            ]
        }
        
        # Compile patterns for efficiency
        self.compiled_patterns = {}
        for intent, patterns in self.patterns.items():
            self.compiled_patterns[intent] = [re.compile(p, re.IGNORECASE) for p in patterns]
    
    def analyze_query(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Analyze query for intent using patterns"""
        query_lower = query.lower().strip()
        
        # Check if this might be a contextual response
        is_short_response = len(query_lower.split()) <= 3
        has_recent_search = context and context.get("recent_products")
        
        # Check each intent
        for intent, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(query_lower):
                    # For short affirmative responses, only treat as add_to_order if there's context
                    if intent == "add_to_order" and is_short_response and not has_recent_search:
                        continue
                    
                    return {
                        "intent": intent,
                        "confidence": 0.85,
                        "entities": self._extract_entities(query_lower),
                        "attributes": self._extract_attributes(query_lower),
                        "metadata": {
                            "search_alpha": self._calculate_alpha(query_lower, intent)
                        }
                    }
        
        # Default to product search
        return {
            "intent": "product_search",
            "confidence": 0.7,
            "entities": self._extract_entities(query_lower),
            "attributes": self._extract_attributes(query_lower),
            "metadata": {
                "search_alpha": self._calculate_alpha(query_lower, "product_search")
            }
        }
    
    def _extract_entities(self, query: str) -> List[str]:
        """Extract potential product entities"""
        # Common product words
        products = []
        product_words = ["spinach", "milk", "bread", "eggs", "cheese", "chicken", 
                        "banana", "apple", "tomato", "lettuce", "carrot", "potato",
                        "yogurt", "butter", "cereal", "pasta", "rice", "salmon"]
        
        for product in product_words:
            if product in query:
                products.append(product)
        
        # Also check for referential words
        if any(word in query for word in ["those", "that", "them", "it", "first", "last"]):
            products.append("_reference")  # Indicates reference to previous search
        
        return products
    
    def _extract_attributes(self, query: str) -> List[str]:
        """Extract attributes like organic, brand names, etc."""
        attributes = []
        
        # Dietary attributes
        dietary = ["organic", "gluten-free", "vegan", "dairy-free", "non-gmo", "sugar-free"]
        for attr in dietary:
            if attr in query:
                attributes.append(attr)
        
        # Brand names
        brands = ["oatly", "horizon", "pacific", "silk", "organic valley"]
        for brand in brands:
            if brand in query:
                attributes.append(brand)
        
        return attributes
    
    def _calculate_alpha(self, query: str, intent: str) -> float:
        """Calculate search alpha based on query characteristics"""
        if intent != "product_search":
            return 0.5  # Default for non-search intents
        
        # Check for specific indicators
        if any(brand in query for brand in ["oatly", "horizon", "organic valley"]):
            return 0.2  # Very keyword-focused for brands
        
        if any(word in query for word in ["ideas", "suggestions", "recommend", "what's good"]):
            return 0.8  # Semantic for exploratory
        
        if len(query.split()) <= 2:
            return 0.3  # Short queries are usually specific
        
        return 0.5  # Default balanced