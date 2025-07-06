"""
Gemini Voice Model - GCP Auto-Detection Version
Automatically uses Vertex AI when on GCP, falls back to Google AI Studio locally
"""
import os
import asyncio
from typing import Dict, List, Optional, Any, Tuple
import structlog
import json

logger = structlog.get_logger()

class GeminiVoiceGCP:
    """
    Gemini voice model with automatic GCP detection
    Uses Vertex AI on GCP, Google AI Studio locally
    """
    
    def __init__(
        self,
        model_name: str = "gemini-1.5-flash",
        project_id: Optional[str] = None,
        location: str = "us-central1"
    ):
        self.model_name = model_name
        self.conversation_history = []
        self.is_gcp = self._detect_gcp_environment()
        
        if self.is_gcp:
            logger.info("Detected GCP environment, using Vertex AI")
            self._init_vertex_ai(project_id, location)
        else:
            logger.info("Local environment detected, using Google AI Studio")
            self._init_google_ai_studio()
    
    def _detect_gcp_environment(self) -> bool:
        """Detect if running on GCP"""
        # Check for common GCP environment variables
        gcp_indicators = [
            "K_SERVICE",  # Cloud Run
            "GAE_ENV",    # App Engine
            "GOOGLE_CLOUD_PROJECT",
            "GCE_METADATA_HOST",
            "GCLOUD_PROJECT"
        ]
        
        return any(os.getenv(var) for var in gcp_indicators)
    
    def _init_vertex_ai(self, project_id: Optional[str], location: str):
        """Initialize Vertex AI for GCP"""
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel
            
            # Use provided project_id or try to detect
            if not project_id:
                project_id = (
                    os.getenv("GOOGLE_CLOUD_PROJECT") or
                    os.getenv("GCLOUD_PROJECT") or
                    os.getenv("GCP_PROJECT")
                )
            
            if not project_id:
                raise ValueError("No GCP project ID found. Set GOOGLE_CLOUD_PROJECT env var.")
            
            vertexai.init(project=project_id, location=location)
            self.model = GenerativeModel(self.model_name)
            self.use_vertex = True
            logger.info(f"Initialized Vertex AI with project: {project_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI: {e}")
            logger.info("Falling back to Google AI Studio")
            self._init_google_ai_studio()
    
    def _init_google_ai_studio(self):
        """Initialize Google AI Studio for local development"""
        try:
            import google.generativeai as genai
            
            api_key = os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError(
                    "No API key found. Set GOOGLE_AI_API_KEY or GEMINI_API_KEY env var."
                )
            
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(self.model_name)
            self.use_vertex = False
            logger.info("Initialized Google AI Studio")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google AI Studio: {e}")
            raise
    
    async def generate_response(
        self,
        user_input: str,
        system_prompt: Optional[str] = None,
        extract_entities: bool = True
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Generate response with automatic intent detection
        
        Returns:
            Tuple of (response_text, extracted_data)
        """
        try:
            # Use default prompt if none provided
            if not system_prompt:
                system_prompt = self._get_default_prompt(extract_entities)
            
            # Build conversation
            prompt = self._build_conversation(user_input, system_prompt)
            
            # Generate based on platform
            if self.use_vertex:
                response = await self._generate_vertex(prompt)
            else:
                response = await self._generate_google_ai(prompt)
            
            # Parse response
            response_text, extracted_data = self._parse_response(response, extract_entities)
            
            # Update history
            self.conversation_history.append({"role": "user", "content": user_input})
            self.conversation_history.append({"role": "assistant", "content": response_text})
            
            # Trim history
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]
            
            return response_text, extracted_data
            
        except Exception as e:
            logger.error(f"Generation error: {e}")
            return "I'm having trouble understanding. Could you please try again?", None
    
    def _get_default_prompt(self, extract_entities: bool) -> str:
        """Get default prompt for grocery assistant"""
        base = """You are a helpful grocery shopping assistant for LeafLoaf.
Keep responses brief (2-3 sentences max) for voice.
Be conversational and natural.

Understand the user's intent and respond appropriately:
- Greeting → Be welcoming
- Product search → Acknowledge and search
- Cart management → Confirm actions
- Recommendations → Provide suggestions
- Order completion → Summarize and confirm"""
        
        if extract_entities:
            base += """

Extract relevant information and format as:
RESPONSE: [your response]
ENTITIES: {"intent": "[detected_intent]", "products": [...], "quantities": [...]}"""
        
        return base
    
    def _build_conversation(self, user_input: str, system_prompt: str) -> str:
        """Build conversation prompt"""
        prompt = f"System: {system_prompt}\n\n"
        
        # Add recent history
        if self.conversation_history:
            prompt += "Recent conversation:\n"
            for msg in self.conversation_history[-6:]:
                role = "User" if msg["role"] == "user" else "Assistant"
                prompt += f"{role}: {msg['content']}\n"
            prompt += "\n"
        
        prompt += f"User: {user_input}\nAssistant:"
        return prompt
    
    async def _generate_vertex(self, prompt: str) -> str:
        """Generate using Vertex AI"""
        response = await asyncio.to_thread(
            self.model.generate_content,
            prompt,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 150,
            }
        )
        return response.text
    
    async def _generate_google_ai(self, prompt: str) -> str:
        """Generate using Google AI Studio"""
        import google.generativeai as genai
        
        response = await asyncio.to_thread(
            self.model.generate_content,
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.7,
                max_output_tokens=150,
            )
        )
        return response.text
    
    def _parse_response(self, response: str, extract_entities: bool) -> Tuple[str, Optional[Dict]]:
        """Parse response and extract entities"""
        if not extract_entities:
            return response.strip(), None
        
        if "RESPONSE:" in response and "ENTITIES:" in response:
            try:
                parts = response.split("ENTITIES:")
                response_text = parts[0].replace("RESPONSE:", "").strip()
                entities_json = parts[1].strip()
                entities = json.loads(entities_json)
                return response_text, entities
            except Exception as e:
                logger.error(f"Parse error: {e}")
        
        return response.strip(), None
    
    def reset_conversation(self):
        """Reset conversation history"""
        self.conversation_history = []
    
    def get_platform_info(self) -> Dict[str, Any]:
        """Get information about current platform"""
        return {
            "is_gcp": self.is_gcp,
            "platform": "Vertex AI" if self.use_vertex else "Google AI Studio",
            "model": self.model_name,
            "project_id": os.getenv("GOOGLE_CLOUD_PROJECT") if self.is_gcp else None
        }