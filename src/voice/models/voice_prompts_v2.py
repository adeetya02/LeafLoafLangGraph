"""
Voice Prompts Configuration for Gemini (v2)
Let Gemini handle intent detection and context understanding
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

class VoicePromptsV2:
    """
    Simplified voice prompts that lets Gemini handle intent detection
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.join(
            os.path.dirname(__file__), 
            "prompts_config.json"
        )
        self.conversation_styles = self._load_default_styles()
        self.base_prompt = self._get_base_prompt()
        
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
    
    def _get_base_prompt(self) -> str:
        """Get base prompt that lets Gemini handle intent detection"""
        return """You are an AI grocery shopping assistant for LeafLoaf.

Your task is to:
1. Understand the user's intent from their message
2. Respond appropriately based on the context
3. Extract relevant entities when applicable

Common intents you'll encounter:
- Greeting/General conversation
- Product search/browsing
- Cart management (add/remove/update)
- Asking for recommendations
- Completing an order
- Asking for clarification

Always:
- Keep responses concise for voice (2-3 sentences max)
- Be conversational and natural
- Acknowledge what you're doing
- Extract product names, brands, quantities when mentioned

Context-aware responses:
- If greeting → Be welcoming
- If searching → Acknowledge and indicate you're searching
- If adding to cart → Confirm the action
- If asking for recommendations → Provide helpful suggestions
- If completing order → Summarize and confirm

When extracting entities, format as:
RESPONSE: [your conversational response]
ENTITIES: {"products": [...], "brands": [...], "quantities": [...], "intent": "detected_intent"}"""
    
    def get_prompt_with_style(
        self, 
        style: str = "friendly_assistant",
        extract_entities: bool = True
    ) -> str:
        """
        Get complete prompt with conversation style
        Let Gemini detect intent rather than pre-categorizing
        """
        conversation_style = self.conversation_styles.get(style)
        
        if not conversation_style:
            conversation_style = self.conversation_styles["friendly_assistant"]
        
        # Build complete prompt
        prompt_parts = [self.base_prompt]
        
        # Add style characteristics
        prompt_parts.append(f"\nConversation style: {conversation_style.tone}")
        prompt_parts.append(f"Response length: {conversation_style.response_length}")
        
        if conversation_style.personality_traits:
            traits = ", ".join(conversation_style.personality_traits)
            prompt_parts.append(f"Personality: {traits}")
        
        if conversation_style.example_phrases:
            prompt_parts.append("\nExample phrases that match your style:")
            for phrase in conversation_style.example_phrases[:3]:
                prompt_parts.append(f"- {phrase}")
        
        if not extract_entities:
            prompt_parts.append("\nDo not extract entities, just provide the conversational response.")
        
        return "\n".join(prompt_parts)
    
    def get_simple_prompt(self) -> str:
        """Get a simple prompt without entity extraction"""
        return """You are a friendly grocery shopping assistant for LeafLoaf.
Help users with their shopping needs.
Keep responses brief (2-3 sentences) since they'll be spoken aloud.
Be conversational and natural."""
    
    def add_conversation_style(self, name: str, style: ConversationStyle):
        """Add a new conversation style"""
        self.conversation_styles[name] = style
    
    def list_available_styles(self) -> List[str]:
        """List all available conversation styles"""
        return list(self.conversation_styles.keys())
    
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
                    
        except Exception as e:
            print(f"Error loading custom config: {e}")