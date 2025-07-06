"""
Voice Prompts Configuration for Gemini
Customizable prompts for different conversation scenarios
"""
from typing import Dict, Optional, List
from dataclasses import dataclass, field
import json
import os

@dataclass
class ConversationStyle:
    """Defines a conversation style with specific characteristics"""
    name: str
    tone: str  # friendly, professional, casual, helpful
    response_length: str  # brief, moderate, detailed
    personality_traits: List[str] = field(default_factory=list)
    example_phrases: List[str] = field(default_factory=list)
    
@dataclass 
class ScenarioPrompt:
    """Defines prompts for specific scenarios"""
    scenario: str
    description: str
    system_prompt: str
    example_interactions: List[Dict[str, str]] = field(default_factory=list)
    entity_focus: List[str] = field(default_factory=list)  # products, brands, categories, etc.

class VoicePrompts:
    """
    Manages voice prompts for different conversation scenarios
    Allows customization of how Gemini handles different types of conversations
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.join(
            os.path.dirname(__file__), 
            "prompts_config.json"
        )
        self.conversation_styles = self._load_default_styles()
        self.scenario_prompts = self._load_default_scenarios()
        
        # Load custom config if exists
        if os.path.exists(self.config_path):
            self._load_custom_config()
    
    def _load_default_styles(self) -> Dict[str, ConversationStyle]:
        """Load default conversation styles"""
        return {
            "friendly_assistant": ConversationStyle(
                name="Friendly Shopping Assistant",
                tone="friendly",
                response_length="brief",
                personality_traits=[
                    "warm", "helpful", "knowledgeable", "patient"
                ],
                example_phrases=[
                    "I'd be happy to help you find that!",
                    "Great choice! Let me look that up for you.",
                    "Is there anything specific you're looking for?"
                ]
            ),
            "efficient_helper": ConversationStyle(
                name="Efficient Helper",
                tone="professional",
                response_length="brief",
                personality_traits=[
                    "concise", "accurate", "efficient"
                ],
                example_phrases=[
                    "Found it. Adding to cart.",
                    "3 options available.",
                    "Confirmed. What else?"
                ]
            ),
            "personal_shopper": ConversationStyle(
                name="Personal Shopper",
                tone="casual",
                response_length="moderate",
                personality_traits=[
                    "personable", "recommendations-focused", "detail-oriented"
                ],
                example_phrases=[
                    "Based on what you usually get, you might also like...",
                    "I remember you prefer organic options!",
                    "This brand is similar but more budget-friendly."
                ]
            )
        }
    
    def _load_default_scenarios(self) -> Dict[str, ScenarioPrompt]:
        """Load default scenario prompts"""
        return {
            "greeting": ScenarioPrompt(
                scenario="greeting",
                description="Initial greeting and conversation starter",
                system_prompt="""You are a friendly grocery shopping assistant for LeafLoaf.
When greeted, respond warmly and offer help with shopping.
Keep responses brief (1-2 sentences) since they'll be spoken aloud.
Don't immediately ask what they want to buy - be conversational first.""",
                example_interactions=[
                    {"user": "Hello!", "assistant": "Hi there! How can I help you today?"},
                    {"user": "How are you?", "assistant": "I'm doing great, thanks for asking! Ready to help with your shopping whenever you are."}
                ]
            ),
            
            "product_search": ScenarioPrompt(
                scenario="product_search", 
                description="User searching for specific products",
                system_prompt="""You are helping find grocery products.
Be helpful and informative but concise.
Extract product names, brands, and categories from the query.
Acknowledge the search request naturally.""",
                example_interactions=[
                    {"user": "I need milk", "assistant": "I'll find milk options for you."},
                    {"user": "Show me organic bananas", "assistant": "Looking for organic bananas now."}
                ],
                entity_focus=["products", "brands", "categories", "attributes"]
            ),
            
            "cart_management": ScenarioPrompt(
                scenario="cart_management",
                description="Adding, removing, or modifying cart items",
                system_prompt="""You are managing the shopping cart.
Confirm actions clearly and mention quantities.
Be brief but specific about what you're doing.""",
                example_interactions=[
                    {"user": "Add 2 milks to cart", "assistant": "Added 2 milks to your cart."},
                    {"user": "Remove the bananas", "assistant": "Removed bananas from your cart."}
                ]
            ),
            
            "recommendations": ScenarioPrompt(
                scenario="recommendations",
                description="Providing personalized product suggestions",
                system_prompt="""You are providing personalized recommendations.
Base suggestions on user history and preferences when available.
Explain briefly why you're recommending something.
Keep it conversational and helpful.""",
                example_interactions=[
                    {"user": "What should I get for breakfast?", "assistant": "Based on your usual picks, you might like our whole grain cereals or Greek yogurt with granola."},
                    {"user": "Any deals today?", "assistant": "Yes! There's 20% off on your favorite pasta brand today."}
                ]
            ),
            
            "order_completion": ScenarioPrompt(
                scenario="order_completion",
                description="Finalizing and confirming orders",
                system_prompt="""You are helping complete an order.
Summarize key details (items count, total if known).
Be clear about next steps.
Express appreciation.""",
                example_interactions=[
                    {"user": "That's everything", "assistant": "Great! You have 12 items in your cart. Ready to checkout?"},
                    {"user": "Checkout please", "assistant": "Perfect! Proceeding to checkout now. Thanks for shopping with LeafLoaf!"}
                ]
            ),
            
            "clarification": ScenarioPrompt(
                scenario="clarification",
                description="When user intent is unclear",
                system_prompt="""You need to clarify what the user wants.
Ask specific, helpful questions.
Provide options when appropriate.
Stay patient and friendly.""",
                example_interactions=[
                    {"user": "I need that thing", "assistant": "Could you tell me more about what you're looking for?"},
                    {"user": "The usual", "assistant": "Would you like me to show your frequently ordered items?"}
                ]
            )
        }
    
    def get_prompt_for_scenario(
        self, 
        scenario: str,
        style: str = "friendly_assistant",
        include_examples: bool = True
    ) -> str:
        """
        Get a complete prompt for a specific scenario with chosen style
        
        Args:
            scenario: The conversation scenario (greeting, product_search, etc.)
            style: The conversation style to use
            include_examples: Whether to include example interactions
            
        Returns:
            Complete system prompt for Gemini
        """
        scenario_prompt = self.scenario_prompts.get(scenario)
        conversation_style = self.conversation_styles.get(style)
        
        if not scenario_prompt:
            # Default fallback
            return self._get_default_prompt()
        
        # Build complete prompt
        prompt_parts = [scenario_prompt.system_prompt]
        
        # Add style characteristics
        if conversation_style:
            prompt_parts.append(f"\nConversation style: {conversation_style.tone}")
            prompt_parts.append(f"Response length: {conversation_style.response_length}")
            
            if conversation_style.personality_traits:
                traits = ", ".join(conversation_style.personality_traits)
                prompt_parts.append(f"Personality: {traits}")
        
        # Add examples if requested
        if include_examples and scenario_prompt.example_interactions:
            prompt_parts.append("\nExample interactions:")
            for example in scenario_prompt.example_interactions[:2]:
                prompt_parts.append(f"User: {example['user']}")
                prompt_parts.append(f"Assistant: {example['assistant']}")
        
        return "\n".join(prompt_parts)
    
    def get_entity_focus(self, scenario: str) -> List[str]:
        """Get which entities to focus on for a scenario"""
        scenario_prompt = self.scenario_prompts.get(scenario)
        if scenario_prompt:
            return scenario_prompt.entity_focus
        return ["products", "brands", "categories"]  # default
    
    def detect_scenario(self, user_input: str, conversation_history: List[Dict] = None) -> str:
        """
        Detect which scenario best matches the user input
        
        Simple rule-based detection - can be enhanced with ML later
        """
        input_lower = user_input.lower()
        
        # Greeting detection
        greeting_words = ["hello", "hi", "hey", "good morning", "good afternoon", "how are you"]
        if any(word in input_lower for word in greeting_words):
            return "greeting"
        
        # Cart management detection  
        cart_words = ["add", "remove", "delete", "cart", "update quantity", "change amount"]
        if any(word in input_lower for word in cart_words):
            return "cart_management"
        
        # Order completion detection
        completion_words = ["checkout", "that's all", "that's everything", "finish", "complete order"]
        done_words = ["done", "finished", "that's it"]
        if any(word in input_lower for word in completion_words):
            return "order_completion"
        if any(word == input_lower.strip() for word in done_words):
            return "order_completion"
        
        # Recommendations detection
        recommendation_words = ["recommend", "suggest", "what should", "ideas", "deals", "special", "on sale", 
                                "what's good", "any suggestions", "help me choose"]
        if any(word in input_lower for word in recommendation_words):
            return "recommendations"
        
        # Clarification detection
        vague_words = ["that", "thing", "stuff", "something"]
        if any(word in input_lower for word in vague_words) and len(input_lower.split()) < 5:
            return "clarification"
            
        # Check for "usual" separately as it's often product search
        if "usual" in input_lower or "regular" in input_lower:
            return "product_search"
        
        # Default to product search
        return "product_search"
    
    def _get_default_prompt(self) -> str:
        """Get default prompt when no scenario matches"""
        return """You are a helpful grocery shopping assistant for LeafLoaf.
Keep responses concise (2-3 sentences max) since they will be spoken aloud.
Be conversational and natural.
Help users find products, manage their cart, and complete orders."""
    
    def save_custom_config(self, config: Dict):
        """Save custom configuration to file"""
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
    
    def _load_custom_config(self):
        """Load custom configuration from file"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                
            # Load custom styles
            if "styles" in config:
                for style_name, style_data in config["styles"].items():
                    self.conversation_styles[style_name] = ConversationStyle(**style_data)
            
            # Load custom scenarios
            if "scenarios" in config:
                for scenario_name, scenario_data in config["scenarios"].items():
                    self.scenario_prompts[scenario_name] = ScenarioPrompt(**scenario_data)
                    
        except Exception as e:
            print(f"Error loading custom config: {e}")
    
    def add_conversation_style(self, name: str, style: ConversationStyle):
        """Add a new conversation style"""
        self.conversation_styles[name] = style
    
    def add_scenario_prompt(self, name: str, prompt: ScenarioPrompt):
        """Add a new scenario prompt"""
        self.scenario_prompts[name] = prompt
    
    def list_available_styles(self) -> List[str]:
        """List all available conversation styles"""
        return list(self.conversation_styles.keys())
    
    def list_available_scenarios(self) -> List[str]:
        """List all available scenarios"""
        return list(self.scenario_prompts.keys())