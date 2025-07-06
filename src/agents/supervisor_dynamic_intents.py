"""
Fully Dynamic Intent Supervisor
No hardcoded intents - learns and classifies dynamically based on context
"""
from typing import Dict, Any, Optional, List
import asyncio
import time
import json
import os
import re
from langsmith import traceable
from src.agents.memory_aware_base import MemoryAwareAgent
from src.models.state import SearchState
from src.memory.graphiti_wrapper import GraphitiMemoryWrapper
from src.memory.memory_manager import memory_manager
from src.voice.deepgram.dynamic_intent_learner import DynamicIntentLearner
from src.config.constants import (
    FAST_MODE, 
    SUPERVISOR_TIMEOUT_MS,
    SUPERVISOR_MAX_REASONING_STEPS
)
from src.tracing.voice_tracer import trace_voice_request, trace_supervisor_analysis, trace_voice_influence
import structlog

logger = structlog.get_logger()


class DynamicIntentSupervisor(MemoryAwareAgent):
    """
    Voice-native supervisor with fully dynamic intent classification
    No hardcoded intent categories - learns from patterns
    """

    def __init__(self):
        super().__init__("supervisor")
        self.llm = self._init_gemma2_9b()
        self.graphiti_wrapper = GraphitiMemoryWrapper()
        self.memory = memory_manager.session_memory
        self.intent_learner = DynamicIntentLearner()
        
        # Dynamic intent categories discovered through usage
        self.discovered_intents = set()
        
    def _init_gemma2_9b(self):
        """Initialize Gemini Pro for intent classification"""
        # Always try Gemini Pro first for intent classification
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            
            # Try different Gemini models
            for model_name in ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']:
                try:
                    model = genai.GenerativeModel(model_name)
                    # Test the model
                    test_response = model.generate_content("Say yes")
                    if test_response.text:
                        logger.info(f"Using {model_name} for intent classification")
                        return model
                except Exception as e:
                    logger.debug(f"{model_name} failed: {e}")
                    continue
                        
        except Exception as e:
            logger.error(f"Gemini API setup failed: {e}")
        
        # Fallback to HuggingFace (for Gemma)
        logger.info("Falling back to HuggingFace models")
        api_key = os.getenv("HUGGINGFACE_API_KEY")
        if api_key:
            try:
                return self._init_huggingface_gemma(api_key)
            except Exception as e:
                logger.warning(f"HuggingFace failed: {e}")
        
        # Last resort fallback
        logger.warning("All LLM options failed, using simple analyzer")
        from src.integrations.simple_intent_analyzer import SimpleIntentAnalyzer
        return SimpleIntentAnalyzer()
    
    def _init_huggingface_gemma(self, api_key: str):
        """Initialize HuggingFace Gemma"""
        from huggingface_hub import InferenceClient
        
        models_to_try = [
            "HuggingFaceH4/zephyr-7b-beta",  # Fast, good quality
            "mistralai/Mistral-7B-Instruct-v0.2",  # Reliable fallback
            "microsoft/phi-2",  # Smaller, faster
            "google/flan-t5-xl"  # Good for classification
        ]
        
        client = InferenceClient(token=api_key)
        
        for model_id in models_to_try:
            try:
                test_response = client.text_generation(
                    "Hi",
                    model=model_id,
                    max_new_tokens=10
                )
                if test_response:
                    logger.info(f"Using {model_id} via HuggingFace Pro")
                    break
            except Exception as e:
                logger.debug(f"{model_id} not available: {e}")
                continue
        else:
            model_id = "mistralai/Mistral-7B-Instruct-v0.3"
            logger.info(f"Falling back to {model_id}")
        
        class HFModel:
            def __init__(self, client, model_name):
                self.client = client
                self.model_name = model_name
                
            def generate_content(self, prompt: str) -> Any:
                try:
                    response = self.client.text_generation(
                        prompt,
                        model=self.model_name,
                        max_new_tokens=200,
                        temperature=0.3,
                        top_p=0.95,
                        do_sample=True,
                        return_full_text=False
                    )
                    
                    class Response:
                        def __init__(self, text):
                            self.text = text
                    
                    return Response(response)
                except Exception as e:
                    logger.error(f"HuggingFace generation failed: {e}")
                    raise
        
        return HFModel(client, model_id)
    
    async def get_learned_intents(self) -> List[str]:
        """Get list of intents that have been learned so far"""
        stats = self.intent_learner.get_intent_statistics()
        return list(stats.keys())
    
    async def _get_agent_specific_context(self, user_id: str, session_id: str, query: str, base_context: Dict) -> Dict[str, Any]:
        """Get context including learned intent patterns"""
        try:
            # Get learned intents and patterns
            intent_stats = self.intent_learner.get_intent_statistics()
            custom_intents = self.intent_learner.generate_deepgram_custom_intents()
            
            # Get recent patterns for this user
            recent_patterns = []
            if hasattr(self.intent_learner, 'get_recent_patterns'):
                recent_patterns = self.intent_learner.get_recent_patterns(hours=24)
            
            return {
                "learned_intents": list(intent_stats.keys()),
                "intent_counts": intent_stats,
                "custom_patterns": custom_intents[:10],  # Top 10 patterns
                "recent_patterns": recent_patterns[:5],
                "total_observations": len(self.intent_learner.intent_observations),
                "has_memory": True
            }
        except Exception as e:
            logger.debug(f"Failed to get intent context: {e}")
            return {"has_memory": False, "learned_intents": []}
    
    async def analyze_with_voice_context(self, query: str, voice_metadata: Dict, memory_context: Dict) -> Dict[str, Any]:
        """
        Fully dynamic intent classification
        No hardcoded categories - learns from usage
        """
        
        # Get learned context
        intent_context = await self._get_agent_specific_context(
            memory_context.get('user_id', 'unknown'),
            memory_context.get('session_id', 'unknown'),
            query,
            memory_context
        )
        
        # Build dynamic prompt
        prompt = f"""<task>
You are an AI assistant for a grocery shopping app. Analyze this voice query and classify its intent.

Voice Context:
- Pace: {voice_metadata.get('pace', 'normal')}
- Emotion: {voice_metadata.get('emotion', 'neutral')}
- Volume: {voice_metadata.get('volume', 'normal')}
- Background noise: {voice_metadata.get('noise_level', 'quiet')}

User said: "{query}"

Previously Learned Intents (with occurrence counts):
{json.dumps(intent_context.get('intent_counts', {}), indent=2) if intent_context.get('intent_counts') else 'No intents learned yet'}

Recent Similar Queries:
{json.dumps(intent_context.get('recent_patterns', [])[:3], indent=2) if intent_context.get('recent_patterns') else 'No recent patterns'}

Instructions:
1. Classify the intent of this query
2. You can use an existing intent from the learned list OR create a new intent if none fit
3. Intent names should be descriptive and action-oriented (e.g., "search_organic_products", "add_item_to_cart", "ask_about_delivery")
4. Be consistent - use existing intents when appropriate

For grocery shopping, common intent patterns include:
- Product searches (finding items)
- Cart operations (add, remove, update, view)
- Order operations (checkout, confirm)
- Information queries (prices, availability, nutrition)
- Customer service (complaints, help, feedback)

Output JSON:
{{
  "intent": "descriptive_intent_name",
  "confidence": 0.0-1.0,
  "is_new_intent": true/false,
  "similar_to": "existing_intent_if_applicable",
  "search_parameters": {{
    "needs_product_search": true/false,
    "search_type": "exact|category|exploratory|none",
    "search_alpha": 0.0-1.0
  }},
  "urgency": "low|medium|high",
  "response_style": "brief|normal|detailed",
  "reasoning": "One sentence explanation",
  "entities": {{
    "products": ["list", "of", "products"],
    "quantities": {{}},
    "attributes": ["organic", "gluten-free", etc]
  }}
}}

Search Alpha Guidelines:
- 0.0-0.3: User wants exact match (specific brand, product name)
- 0.4-0.6: General product search
- 0.7-1.0: Exploratory/browsing (ideas, suggestions)
</task>

Output only valid JSON, no other text."""
        
        try:
            # Get LLM response
            if hasattr(self.llm, 'generate_content'):
                if asyncio.iscoroutinefunction(self.llm.generate_content):
                    response = await self.llm.generate_content(prompt)
                else:
                    loop = asyncio.get_event_loop()
                    response = await asyncio.wait_for(
                        loop.run_in_executor(None, self.llm.generate_content, prompt),
                        timeout=10.0
                    )
                
                result_text = response.text.strip() if response.text else ""
            else:
                # Fallback
                return {
                    "intent": "general_query",
                    "confidence": 0.5,
                    "is_new_intent": False,
                    "search_parameters": {"needs_product_search": True, "search_alpha": 0.5},
                    "urgency": "medium",
                    "response_style": "normal",
                    "reasoning": "Fallback classification"
                }
            
            # Parse response
            cleaned_text = result_text.strip()
            
            # Remove markdown if present
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
                if cleaned_text.endswith('```'):
                    cleaned_text = cleaned_text[:-3]
                cleaned_text = cleaned_text.strip()
            
            # Extract JSON
            json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
            if json_match:
                cleaned_text = json_match.group(0)
            
            result = json.loads(cleaned_text)
            
            # Record this classification for learning
            intent = result.get("intent", "unknown")
            confidence = result.get("confidence", 0.5)
            
            # Learn from this classification
            await self.intent_learner.observe_intent(query, intent, confidence)
            
            # Track new intents
            if result.get("is_new_intent", False):
                self.discovered_intents.add(intent)
                logger.info(f"Discovered new intent: {intent}")
            
            # Add backward compatibility fields
            result["search_alpha"] = result.get("search_parameters", {}).get("search_alpha", 0.5)
            
            # Log the classification
            logger.info(f"Dynamic classification - Query: '{query}' -> Intent: '{intent}' (confidence: {confidence})")
            
            return result
            
        except Exception as e:
            logger.error(f"Dynamic intent analysis failed: {e}", exc_info=True)
            
            # Emergency fallback
            return {
                "intent": "product_search",  # Safe default
                "confidence": 0.3,
                "is_new_intent": False,
                "search_parameters": {
                    "needs_product_search": True,
                    "search_type": "general",
                    "search_alpha": 0.5
                },
                "urgency": "medium",
                "response_style": "normal",
                "reasoning": "Error fallback - defaulting to product search",
                "entities": {}
            }
    
    async def get_intent_suggestions(self) -> Dict[str, Any]:
        """Get suggestions for intent consolidation based on patterns"""
        suggestions = self.intent_learner.suggest_intent_consolidation()
        return {
            "suggestions": suggestions,
            "total_intents": len(self.intent_learner.get_intent_statistics()),
            "discovered_intents": list(self.discovered_intents)
        }
    
    async def export_learned_intents(self) -> Dict[str, Any]:
        """Export all learned intents and patterns for analysis"""
        return {
            "intent_statistics": self.intent_learner.get_intent_statistics(),
            "custom_patterns": self.intent_learner.generate_deepgram_custom_intents(),
            "discovered_intents": list(self.discovered_intents),
            "total_observations": len(self.intent_learner.intent_observations),
            "confidence_patterns": self.intent_learner.get_confidence_weighted_patterns()
        }
    
    async def _run(self, state: SearchState) -> SearchState:
        """Required abstract method - not used in supervisor"""
        # Supervisor doesn't directly process state, it analyzes queries
        return state