"""
Conversational Agent - Manages natural dialogue flow
"""
from typing import Dict, Any, List, Optional
import structlog
from datetime import datetime

logger = structlog.get_logger()

class ConversationalAgent:
    """Manages conversational flow and context"""
    
    def __init__(self):
        self.logger = logger.bind(agent="conversational")
        
        # Conversation patterns
        self.conversation_patterns = {
            "greeting": {
                "patterns": ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"],
                "responses": {
                    "first_time": [
                        "Welcome to Leaf & Loaf! I'm here to help with your grocery shopping. What can I get for you today?",
                        "Hi there! Ready to help you find everything you need. What are you looking for?",
                        "Hello! Great to have you here. What's on your shopping list today?"
                    ],
                    "returning": [
                        "Welcome back! How can I help you today?",
                        "Good to see you again! What can I get for you?",
                        "Hi again! Ready for your shopping? What do you need?"
                    ]
                }
            },
            
            "clarification": {
                "patterns": ["what", "which", "how many", "what kind"],
                "responses": {
                    "product_type": "What type of {product} are you looking for? We have several options.",
                    "quantity": "How many would you like?",
                    "preference": "Do you have a preference for brand or type?"
                }
            },
            
            "confirmation": {
                "patterns": ["yes", "yeah", "sure", "ok", "correct", "that's right"],
                "responses": {
                    "item_added": "Great! I've added that to your cart.",
                    "order_confirmed": "Perfect! Your order is confirmed.",
                    "understood": "Got it! Let me help you with that."
                }
            },
            
            "negation": {
                "patterns": ["no", "not", "don't", "wrong", "different"],
                "responses": {
                    "try_again": "No problem, let's try something else. What would you prefer?",
                    "clarify": "I understand. Can you tell me more about what you're looking for?",
                    "alternatives": "Let me show you some other options."
                }
            },
            
            "completion": {
                "patterns": ["done", "that's all", "finish", "checkout", "complete"],
                "responses": {
                    "confirm_complete": "Is that everything for your order today?",
                    "checkout": "Great! Let me total that up for you.",
                    "thank_you": "Thank you for shopping with Leaf & Loaf!"
                }
            }
        }
        
        # Context understanding
        self.context_handlers = {
            "quantity_mentioned": self._handle_quantity,
            "brand_mentioned": self._handle_brand,
            "dietary_mentioned": self._handle_dietary,
            "price_concern": self._handle_price,
            "quality_concern": self._handle_quality
        }
        
    async def analyze_conversation_intent(
        self, 
        transcript: str,
        conversation_history: List[Dict],
        current_context: Dict
    ) -> Dict[str, Any]:
        """Analyze the conversational intent"""
        
        transcript_lower = transcript.lower()
        
        # Check conversation patterns
        for pattern_type, pattern_data in self.conversation_patterns.items():
            if any(p in transcript_lower for p in pattern_data["patterns"]):
                return {
                    "pattern_type": pattern_type,
                    "confidence": 0.8,
                    "suggested_responses": pattern_data["responses"]
                }
        
        # Analyze context clues
        context_clues = []
        
        # Check for quantities
        quantity_words = ["one", "two", "three", "dozen", "pound", "gallon", "bunch"]
        if any(q in transcript_lower for q in quantity_words):
            context_clues.append("quantity_mentioned")
            
        # Check for brands
        # This would ideally check against known brands
        if any(word[0].isupper() for word in transcript.split() if len(word) > 2):
            context_clues.append("brand_mentioned")
            
        # Check for dietary preferences
        dietary_words = ["organic", "gluten-free", "vegan", "vegetarian", "non-gmo", "sugar-free"]
        if any(d in transcript_lower for d in dietary_words):
            context_clues.append("dietary_mentioned")
            
        # Check for price concerns
        price_words = ["cheap", "expensive", "budget", "price", "cost", "afford"]
        if any(p in transcript_lower for p in price_words):
            context_clues.append("price_concern")
            
        # Check for quality concerns
        quality_words = ["fresh", "quality", "best", "good", "ripe", "expired"]
        if any(q in transcript_lower for q in quality_words):
            context_clues.append("quality_concern")
            
        return {
            "pattern_type": "general",
            "context_clues": context_clues,
            "requires_search": len(context_clues) > 0 or self._is_product_query(transcript),
            "confidence": 0.6
        }
        
    def _is_product_query(self, transcript: str) -> bool:
        """Check if transcript mentions products"""
        product_indicators = ["need", "want", "looking for", "get", "buy", "find"]
        return any(indicator in transcript.lower() for indicator in product_indicators)
        
    def _handle_quantity(self, transcript: str, context: Dict) -> Dict:
        """Handle quantity extraction"""
        # Simple quantity extraction
        quantity_map = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
            "dozen": 12, "half dozen": 6
        }
        
        for word, num in quantity_map.items():
            if word in transcript.lower():
                return {"quantity": num, "unit": "each"}
                
        return {"quantity": 1, "unit": "each"}
        
    def _handle_brand(self, transcript: str, context: Dict) -> Dict:
        """Handle brand extraction"""
        # Extract capitalized words as potential brands
        words = transcript.split()
        brands = [w for w in words if w[0].isupper() and len(w) > 2]
        return {"preferred_brands": brands}
        
    def _handle_dietary(self, transcript: str, context: Dict) -> Dict:
        """Handle dietary preference extraction"""
        dietary_prefs = []
        dietary_map = {
            "organic": "organic",
            "gluten-free": "gluten_free",
            "gluten free": "gluten_free",
            "vegan": "vegan",
            "vegetarian": "vegetarian",
            "non-gmo": "non_gmo",
            "non gmo": "non_gmo",
            "sugar-free": "sugar_free",
            "sugar free": "sugar_free"
        }
        
        transcript_lower = transcript.lower()
        for phrase, pref in dietary_map.items():
            if phrase in transcript_lower:
                dietary_prefs.append(pref)
                
        return {"dietary_preferences": dietary_prefs}
        
    def _handle_price(self, transcript: str, context: Dict) -> Dict:
        """Handle price concern extraction"""
        if any(word in transcript.lower() for word in ["cheap", "budget", "affordable"]):
            return {"price_preference": "budget"}
        elif any(word in transcript.lower() for word in ["best", "premium", "quality"]):
            return {"price_preference": "premium"}
        return {"price_preference": "normal"}
        
    def _handle_quality(self, transcript: str, context: Dict) -> Dict:
        """Handle quality preference extraction"""
        if any(word in transcript.lower() for word in ["fresh", "ripe", "today"]):
            return {"quality_preference": "fresh"}
        return {"quality_preference": "normal"}
        
    def generate_contextual_response(
        self,
        action: str,
        result: Dict,
        context: Dict,
        tone: str = "friendly"
    ) -> str:
        """Generate contextual response based on action and result"""
        
        if action == "greeting":
            if context.get("first_time", True):
                return self.conversation_patterns["greeting"]["responses"]["first_time"][0]
            else:
                return self.conversation_patterns["greeting"]["responses"]["returning"][0]
                
        elif action == "search":
            products = result.get("products", [])
            if not products:
                return "I couldn't find that exact item. Could you describe what you're looking for in more detail?"
                
            count = len(products)
            if count == 1:
                p = products[0]
                return f"I found {p['product_name']} from {p.get('supplier', 'our store')} for ${p['price']:.2f}. Would you like me to add it to your cart?"
            else:
                return f"I found {count} options for you. Let me show you the best matches."
                
        elif action == "cart_update":
            if result.get("success"):
                items_in_cart = len(context.get("current_order", {}).get("items", []))
                if items_in_cart == 1:
                    return "I've added that to your cart. What else can I get for you?"
                else:
                    return f"Added! You now have {items_in_cart} items in your cart. Anything else?"
            else:
                return "I had trouble with that. Could you tell me which item you'd like to add?"
                
        elif action == "checkout":
            order = result.get("order", {})
            items = order.get("items", [])
            if items:
                total = sum(item["price"] * item["quantity"] for item in items)
                return f"Your order of {len(items)} items comes to ${total:.2f}. Shall I confirm this order for you?"
            else:
                return "Your cart is empty. Would you like to add some items?"
                
        else:
            return "How else can I help you today?"
            
    def should_clarify(self, transcript: str, context: Dict) -> Optional[str]:
        """Determine if clarification is needed"""
        
        transcript_lower = transcript.lower()
        
        # Ambiguous product requests
        if "milk" in transcript_lower and not any(
            type in transcript_lower 
            for type in ["whole", "2%", "skim", "almond", "oat", "soy"]
        ):
            return "What type of milk would you prefer? We have whole, 2%, skim, and non-dairy options."
            
        # Missing quantity for bulk items
        bulk_items = ["apples", "bananas", "potatoes", "onions", "tomatoes"]
        for item in bulk_items:
            if item in transcript_lower and not self._has_quantity(transcript):
                return f"How many {item} would you like?"
                
        # Ambiguous size
        if any(size_product in transcript_lower for size_product in ["eggs", "juice", "bread"]):
            if "eggs" in transcript_lower and not any(
                size in transcript_lower for size in ["dozen", "half", "6", "12", "18"]
            ):
                return "What size egg carton would you like? We have half dozen, dozen, and 18-count."
                
        return None
        
    def _has_quantity(self, transcript: str) -> bool:
        """Check if transcript contains quantity"""
        quantity_indicators = [
            "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
            "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
            "dozen", "pound", "pounds", "lb", "lbs", "kg", "gallon", "quart", "pint",
            "bunch", "bag", "box", "pack", "package"
        ]
        return any(q in transcript.lower() for q in quantity_indicators)