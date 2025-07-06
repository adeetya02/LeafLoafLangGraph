"""
Gemini Voice Model for Conversational AI
Handles conversation and entity extraction for Graphiti/Spanner
"""
import os
import asyncio
from typing import Dict, List, Optional, Any, Tuple
import google.generativeai as genai
from vertexai.generative_models import GenerativeModel
import structlog
import json
from .voice_prompts import VoicePrompts

logger = structlog.get_logger()

class GeminiVoiceModel:
    """
    Gemini model for voice conversations with entity extraction
    Supports both Google AI Studio (for dev) and Vertex AI (for prod)
    """
    
    def __init__(
        self,
        model_name: str = "gemini-1.5-flash",
        use_vertex: bool = False,
        project_id: Optional[str] = None,
        location: str = "us-central1",
        prompts_config: Optional[str] = None
    ):
        self.model_name = model_name
        self.use_vertex = use_vertex
        self.conversation_history = []
        self.voice_prompts = VoicePrompts(prompts_config)
        self.current_style = "friendly_assistant"
        
        if use_vertex:
            # Use Vertex AI (production)
            import vertexai
            vertexai.init(project=project_id, location=location)
            self.model = GenerativeModel(model_name)
        else:
            # Use Google AI Studio (development)
            api_key = os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_AI_API_KEY or GEMINI_API_KEY required")
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model_name)
    
    async def generate_response(
        self,
        user_input: str,
        system_prompt: Optional[str] = None,
        extract_entities: bool = True,
        conversation_context: Optional[List[Dict]] = None,
        conversation_style: Optional[str] = None,
        auto_detect_scenario: bool = True
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Generate conversational response with optional entity extraction
        
        Args:
            user_input: The user's spoken input
            system_prompt: Optional custom prompt (overrides scenario detection)
            extract_entities: Whether to extract entities for Graphiti
            conversation_context: Optional conversation history
            conversation_style: Optional style override (e.g., "efficient_helper")
            auto_detect_scenario: Whether to auto-detect the scenario
            
        Returns:
            Tuple of (response_text, extracted_entities)
        """
        try:
            # Use provided context or internal history
            context = conversation_context or self.conversation_history
            
            # Set conversation style if provided
            if conversation_style:
                self.current_style = conversation_style
            
            # Auto-detect scenario if enabled and no custom prompt
            if auto_detect_scenario and not system_prompt:
                scenario = self.voice_prompts.detect_scenario(user_input, context)
                system_prompt = self.voice_prompts.get_prompt_for_scenario(
                    scenario, 
                    self.current_style,
                    include_examples=True
                )
                
                # Get entity focus for this scenario
                if extract_entities:
                    entity_focus = self.voice_prompts.get_entity_focus(scenario)
                    logger.info(f"Detected scenario: {scenario}, entity focus: {entity_focus}")
            
            # Build the prompt
            prompt = self._build_prompt(user_input, system_prompt, extract_entities, context)
            
            # Generate response
            if self.use_vertex:
                response = await self._generate_vertex(prompt)
            else:
                response = await self._generate_genai(prompt)
            
            # Parse response and entities
            response_text, entities = self._parse_response(response, extract_entities)
            
            # Update conversation history
            self.conversation_history.append({"role": "user", "content": user_input})
            self.conversation_history.append({"role": "assistant", "content": response_text})
            
            # Keep history manageable
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]
            
            return response_text, entities
            
        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            return "I'm having trouble understanding. Could you please rephrase?", None
    
    def _build_prompt(
        self,
        user_input: str,
        system_prompt: Optional[str],
        extract_entities: bool,
        context: List[Dict]
    ) -> str:
        """Build the full prompt with instructions"""
        
        # Default system prompt for grocery assistant
        if not system_prompt:
            system_prompt = """You are a friendly and helpful grocery shopping assistant for LeafLoaf.
Keep responses concise (2-3 sentences max) since they will be spoken aloud.
Be conversational and natural."""
        
        # Add entity extraction instructions if needed
        if extract_entities:
            system_prompt += """

When users mention products, brands, or categories, extract them as entities.
Format your response as:
RESPONSE: [your conversational response]
ENTITIES: {"products": [...], "brands": [...], "categories": [...]}"""
        
        # Build conversation context
        conversation = f"System: {system_prompt}\n\n"
        
        # Add conversation history
        for msg in context[-10:]:  # Last 10 messages
            role = "Customer" if msg["role"] == "user" else "Assistant"
            conversation += f"{role}: {msg['content']}\n"
        
        # Add current input
        conversation += f"Customer: {user_input}\nAssistant:"
        
        return conversation
    
    async def _generate_vertex(self, prompt: str) -> str:
        """Generate using Vertex AI"""
        response = await asyncio.to_thread(
            self.model.generate_content,
            prompt,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 200,
            }
        )
        return response.text
    
    async def _generate_genai(self, prompt: str) -> str:
        """Generate using Google AI Studio"""
        import asyncio
        response = await asyncio.to_thread(
            self.model.generate_content,
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.7,
                max_output_tokens=200,
            )
        )
        return response.text
    
    def _parse_response(self, response: str, extract_entities: bool) -> Tuple[str, Optional[Dict]]:
        """Parse response and extract entities if requested"""
        
        if not extract_entities:
            return response.strip(), None
        
        # Try to parse structured response
        if "RESPONSE:" in response and "ENTITIES:" in response:
            try:
                parts = response.split("ENTITIES:")
                response_text = parts[0].replace("RESPONSE:", "").strip()
                entities_json = parts[1].strip()
                
                # Parse entities
                entities = json.loads(entities_json)
                
                # Log for Graphiti integration
                if entities:
                    logger.info("Extracted entities for Graphiti", entities=entities)
                
                return response_text, entities
                
            except Exception as e:
                logger.error(f"Entity parsing error: {e}")
                # Return full response if parsing fails
                return response.strip(), None
        
        return response.strip(), None
    
    def reset_conversation(self):
        """Reset conversation history"""
        self.conversation_history = []
    
    def get_conversation_summary(self) -> str:
        """Get a summary of the conversation for context"""
        if not self.conversation_history:
            return "No conversation yet"
        
        # Simple summary of topics discussed
        user_messages = [msg["content"] for msg in self.conversation_history if msg["role"] == "user"]
        return f"Topics discussed: {', '.join(user_messages[:5])}"
    
    def set_conversation_style(self, style: str):
        """Set the conversation style"""
        if style in self.voice_prompts.list_available_styles():
            self.current_style = style
            logger.info(f"Conversation style set to: {style}")
        else:
            logger.warning(f"Unknown style: {style}. Available: {self.voice_prompts.list_available_styles()}")
    
    def add_custom_scenario(self, scenario_name: str, prompt: str, examples: List[Dict] = None):
        """Add a custom scenario prompt"""
        from .voice_prompts import ScenarioPrompt
        
        scenario = ScenarioPrompt(
            scenario=scenario_name,
            description=f"Custom scenario: {scenario_name}",
            system_prompt=prompt,
            example_interactions=examples or []
        )
        self.voice_prompts.add_scenario_prompt(scenario_name, scenario)
        logger.info(f"Added custom scenario: {scenario_name}")
    
    def get_available_styles(self) -> List[str]:
        """Get list of available conversation styles"""
        return self.voice_prompts.list_available_styles()
    
    def get_available_scenarios(self) -> List[str]:
        """Get list of available scenarios"""
        return self.voice_prompts.list_available_scenarios()