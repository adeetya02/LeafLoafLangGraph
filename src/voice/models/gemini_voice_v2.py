"""
Gemini Voice Model v2 - Let Gemini handle intent detection
"""
import os
import asyncio
from typing import Dict, List, Optional, Any, Tuple
import google.generativeai as genai
from vertexai.generative_models import GenerativeModel
import structlog
import json
from .voice_prompts_v2 import VoicePromptsV2

logger = structlog.get_logger()

class GeminiVoiceModelV2:
    """
    Simplified Gemini model that handles its own intent detection
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
        self.voice_prompts = VoicePromptsV2(prompts_config)
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
        conversation_style: Optional[str] = None,
        extract_entities: bool = True,
        conversation_context: Optional[List[Dict]] = None
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Generate response and let Gemini detect intent
        
        Args:
            user_input: The user's spoken input
            conversation_style: Optional style override
            extract_entities: Whether to extract entities and intent
            conversation_context: Optional conversation history
            
        Returns:
            Tuple of (response_text, extracted_data)
        """
        try:
            # Use provided context or internal history
            context = conversation_context or self.conversation_history
            
            # Set conversation style if provided
            if conversation_style:
                self.current_style = conversation_style
            
            # Get the prompt with style
            system_prompt = self.voice_prompts.get_prompt_with_style(
                self.current_style,
                extract_entities
            )
            
            # Build the full conversation
            prompt = self._build_conversation(user_input, system_prompt, context)
            
            # Generate response
            if self.use_vertex:
                response = await self._generate_vertex(prompt)
            else:
                response = await self._generate_genai(prompt)
            
            # Parse response
            response_text, extracted_data = self._parse_response(response, extract_entities)
            
            # Log detected intent if available
            if extracted_data and "intent" in extracted_data:
                logger.info(f"Gemini detected intent: {extracted_data['intent']}")
            
            # Update conversation history
            self.conversation_history.append({"role": "user", "content": user_input})
            self.conversation_history.append({"role": "assistant", "content": response_text})
            
            # Keep history manageable
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]
            
            return response_text, extracted_data
            
        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            return "I'm having trouble understanding. Could you please rephrase?", None
    
    def _build_conversation(
        self,
        user_input: str,
        system_prompt: str,
        context: List[Dict]
    ) -> str:
        """Build the full conversation prompt"""
        
        # Start with system prompt
        conversation = f"System: {system_prompt}\n\n"
        
        # Add conversation history
        if context:
            conversation += "Previous conversation:\n"
            for msg in context[-10:]:  # Last 10 messages
                role = "Customer" if msg["role"] == "user" else "Assistant"
                conversation += f"{role}: {msg['content']}\n"
            conversation += "\n"
        
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
        """Parse response and extract data if requested"""
        
        if not extract_entities:
            return response.strip(), None
        
        # Try to parse structured response
        if "RESPONSE:" in response and "ENTITIES:" in response:
            try:
                parts = response.split("ENTITIES:")
                response_text = parts[0].replace("RESPONSE:", "").strip()
                entities_json = parts[1].strip()
                
                # Parse entities
                extracted_data = json.loads(entities_json)
                
                # Log for debugging
                logger.info("Extracted data from Gemini", data=extracted_data)
                
                return response_text, extracted_data
                
            except Exception as e:
                logger.error(f"Entity parsing error: {e}")
                # Return full response if parsing fails
                return response.strip(), None
        
        return response.strip(), None
    
    def set_conversation_style(self, style: str):
        """Set the conversation style"""
        if style in self.voice_prompts.list_available_styles():
            self.current_style = style
            logger.info(f"Conversation style set to: {style}")
        else:
            available = self.voice_prompts.list_available_styles()
            logger.warning(f"Unknown style: {style}. Available: {available}")
    
    def reset_conversation(self):
        """Reset conversation history"""
        self.conversation_history = []
    
    def get_conversation_summary(self) -> str:
        """Get a summary of the conversation for context"""
        if not self.conversation_history:
            return "No conversation yet"
        
        # Get recent user messages
        user_messages = [msg["content"] for msg in self.conversation_history if msg["role"] == "user"]
        return f"Recent topics: {', '.join(user_messages[-5:])}"