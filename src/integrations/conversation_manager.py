"""
Conversation Manager for multi-turn voice interactions
Handles the flow between search, browsing, and order confirmation
"""
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import structlog
from enum import Enum

logger = structlog.get_logger()

class ConversationState(Enum):
    """Conversation states"""
    GREETING = "greeting"
    BROWSING = "browsing"
    SEARCHING = "searching"
    REVIEWING_RESULTS = "reviewing_results"
    ADDING_TO_CART = "adding_to_cart"
    REVIEWING_CART = "reviewing_cart"
    CONFIRMING_ORDER = "confirming_order"
    COMPLETED = "completed"

class ConversationManager:
    """
    Manages multi-turn conversations between user and agents
    Maintains context and handles state transitions
    """

    def __init__(self):
        self.conversations = {}
        self.transition_phrases = {
            "greeting": ["hello", "hi", "hey", "good morning", "good afternoon", "how are you"],
            "add_to_cart": ["add", "i'll take", "give me", "want", "need"],
            "browse_more": ["what else", "show more", "other options", "anything else"],
            "review_cart": ["what's in my cart", "show my order", "review order"],
            "confirm": ["that's it", "confirm", "place order", "i'm done", "checkout"],
            "remove": ["remove", "don't want", "take out"],
            "help": ["help", "what can you", "how does this work"]
        }

    async def process_conversation_turn(
        self,
        session_id: str,
        user_input: str,
        current_results: Optional[List[Dict]] = None,
        current_order: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process a conversation turn and determine next action

        Args:
            session_id: Session identifier
            user_input: What the user said
            current_results: Current search results if any
            current_order: Current cart state

        Returns:
            Action to take and response
        """
        # Get or create conversation state
        conv_state = self.conversations.get(session_id, {
            "state": ConversationState.GREETING,
            "context": {},
            "turn_count": 0
        })

        conv_state["turn_count"] += 1

        # Determine intent from user input
        intent = self._determine_intent(user_input, conv_state["state"], current_results, current_order)

        # Process based on intent
        response = await self._process_intent(intent, user_input, current_results, current_order, conv_state)

        # Update conversation state
        self.conversations[session_id] = conv_state

        return response

    def _determine_intent(
        self,
        user_input: str,
        current_state: ConversationState,
        current_results: Optional[List[Dict]],
        current_order: Optional[Dict]
    ) -> str:
        """Determine user intent from input and context"""
        input_lower = user_input.lower()

        # Check for specific intents
        for intent, phrases in self.transition_phrases.items():
            if any(phrase in input_lower for phrase in phrases):
                return intent

        # Context-based intent
        if current_state == ConversationState.GREETING:
            # Don't default to search for greetings
            if intent == "greeting":
                return "greeting"
            # Only search if it looks like a product query
            elif any(word in input_lower for word in ["milk", "bread", "organic", "fruit", "vegetable", "cheese", "yogurt"]):
                return "search"
            else:
                return "greeting"  # Default to greeting

        elif current_state == ConversationState.REVIEWING_RESULTS:
            # User might be selecting from results
            if any(word in input_lower for word in ["first", "second", "number", "#"]):
                return "select_item"
            elif "organic" in input_lower or "milk" in input_lower:
                return "refine_search"

        elif current_state == ConversationState.REVIEWING_CART:
            return "confirm" if "yes" in input_lower else "browse_more"

        # Default intents by state
        state_defaults = {
            ConversationState.BROWSING: "search",
            ConversationState.SEARCHING: "search",
            ConversationState.REVIEWING_RESULTS: "browse_more",
            ConversationState.ADDING_TO_CART: "add_to_cart",
            ConversationState.REVIEWING_CART: "review_cart"
        }

        return state_defaults.get(current_state, "search")

    async def _process_intent(
        self,
        intent: str,
        user_input: str,
        current_results: Optional[List[Dict]],
        current_order: Optional[Dict],
        conv_state: Dict
    ) -> Dict[str, Any]:
        """Process the intent and return appropriate response"""

        if intent == "greeting":
            conv_state["state"] = ConversationState.GREETING
            greetings = [
                "Hello! Welcome to Leaf and Loaf. What can I help you find today?",
                "Hi there! I'm here to help you shop. What would you like to order?",
                "Welcome! Tell me what you're looking for and I'll help you find it."
            ]
            return {
                "action": "greeting",
                "response": greetings[0],
                "voice_response": "Hello! Welcome to Leaf and Loaf. What can I help you find today?",
                "next_state": ConversationState.BROWSING
            }

        elif intent == "search" or intent == "refine_search":
            conv_state["state"] = ConversationState.SEARCHING
            return {
                "action": "search",
                "query": user_input,
                "response": f"Let me search for {user_input}...",
                "voice_response": "Let me find that for you.",
                "next_state": ConversationState.REVIEWING_RESULTS
            }

        elif intent == "browse_more":
            conv_state["state"] = ConversationState.BROWSING
            prompts = [
                "What else would you like to see?",
                "What other products are you looking for?",
                "Is there anything else you need?"
            ]
            return {
                "action": "prompt",
                "response": prompts[conv_state["turn_count"] % len(prompts)],
                "voice_response": prompts[conv_state["turn_count"] % len(prompts)],
                "maintain_results": True
            }

        elif intent == "add_to_cart":
            conv_state["state"] = ConversationState.ADDING_TO_CART
            # Parse what to add
            items_to_add = self._parse_cart_addition(user_input, current_results)

            if items_to_add:
                return {
                    "action": "add_to_order",
                    "items": items_to_add,
                    "response": f"I've added {len(items_to_add)} item(s) to your cart. What else would you like?",
                    "voice_response": "Added to your cart. Would you like anything else?",
                    "next_state": ConversationState.BROWSING
                }
            else:
                return {
                    "action": "clarify",
                    "response": "Which item would you like to add? You can say 'the first one' or describe it.",
                    "voice_response": "Which item would you like? Just tell me which one.",
                    "maintain_results": True
                }

        elif intent == "select_item":
            # Handle numbered selection
            item_number = self._extract_item_number(user_input)
            if item_number and current_results and item_number <= len(current_results):
                selected_item = current_results[item_number - 1]
                return {
                    "action": "add_to_order",
                    "items": [selected_item],
                    "response": f"Added {selected_item.get('name', 'item')} to your cart.",
                    "voice_response": f"I've added {selected_item.get('name', 'that item')} to your cart.",
                    "next_state": ConversationState.BROWSING
                }

        elif intent == "review_cart":
            conv_state["state"] = ConversationState.REVIEWING_CART
            cart_size = len(current_order.get("items", [])) if current_order else 0

            if cart_size == 0:
                return {
                    "action": "show_cart",
                    "response": "Your cart is empty. What would you like to order?",
                    "voice_response": "Your cart is empty. What can I help you find?",
                    "next_state": ConversationState.BROWSING
                }
            else:
                return {
                    "action": "show_cart",
                    "response": f"You have {cart_size} items in your cart. Would you like to confirm your order or add more items?",
                    "voice_response": f"You have {cart_size} items in your cart. Ready to checkout or need anything else?",
                    "next_state": ConversationState.REVIEWING_CART
                }

        elif intent == "confirm":
            conv_state["state"] = ConversationState.CONFIRMING_ORDER
            return {
                "action": "confirm_order",
                "response": "Your order has been confirmed. Thank you for shopping with Leaf and Loaf!",
                "voice_response": "Perfect! Your order has been confirmed. Thank you for shopping with Leaf and Loaf!",
                "next_state": ConversationState.COMPLETED
            }

        else:
            # Default fallback
            return {
                "action": "help",
                "response": "I can help you search for products, add items to your cart, or complete your order. What would you like to do?",
                "voice_response": "I can help you find products or complete your order. What would you like?",
                "maintain_state": True
            }

    def _parse_cart_addition(self, user_input: str, current_results: Optional[List[Dict]]) -> List[Dict]:
        """Parse which items to add from user input"""
        if not current_results:
            return []

        items_to_add = []
        input_lower = user_input.lower()

        # Check for "all" or "everything"
        if any(word in input_lower for word in ["all", "everything", "all of them"]):
            return current_results[:3]  # Limit to 3 for safety

        # Check for specific items mentioned
        for i, result in enumerate(current_results):
            result_name = result.get("name", "").lower()
            # Check if product name words appear in input
            name_words = result_name.split()
            if sum(1 for word in name_words if word in input_lower) >= 2:
                items_to_add.append(result)

        # If no specific items but user said "add", add first item
        if not items_to_add and any(word in input_lower for word in ["add", "yes", "that one"]):
            items_to_add.append(current_results[0])

        return items_to_add

    def _extract_item_number(self, user_input: str) -> Optional[int]:
        """Extract item number from user input"""
        import re

        # Look for patterns like "first", "1st", "#1", "number 1"
        patterns = {
            r'first|1st|one': 1,
            r'second|2nd|two': 2,
            r'third|3rd|three': 3,
            r'fourth|4th|four': 4,
            r'fifth|5th|five': 5
        }

        input_lower = user_input.lower()
        for pattern, number in patterns.items():
            if re.search(pattern, input_lower):
                return number

        # Look for direct numbers
        numbers = re.findall(r'\d+', user_input)
        if numbers:
            return int(numbers[0])

        return None

    def get_conversation_summary(self, session_id: str) -> Dict[str, Any]:
        """Get summary of conversation for context"""
        conv_state = self.conversations.get(session_id, {})
        return {
            "state": conv_state.get("state", ConversationState.GREETING).value,
            "turn_count": conv_state.get("turn_count", 0),
            "context": conv_state.get("context", {})
        }

    def end_conversation(self, session_id: str):
        """Clean up conversation state"""
        if session_id in self.conversations:
            del self.conversations[session_id]