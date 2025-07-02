import os
import asyncio
import re
import json
from typing import Dict, List, Optional, Any
import httpx
from pydantic import BaseModel
import structlog
from src.config.settings import settings
from src.config.constants import (
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SECONDS,
    ENVIRONMENT
)

# Conditional imports for Vertex AI
try:
    from google.cloud import aiplatform
    import vertexai
    from vertexai.generative_models import GenerativeModel, GenerationConfig
    VERTEX_AI_AVAILABLE = True
except ImportError:
    VERTEX_AI_AVAILABLE = False
    logger.warning("Vertex AI not available")

logger = structlog.get_logger()

class GemmaResponse(BaseModel):
    text: str
    intent: Optional[str] = None
    confidence: Optional[float] = None
    metadata: Optional[Dict] = None

class GemmaClientV2:
    """Enhanced Gemma client with deployed endpoint as primary and Generative AI as fallback"""

    def __init__(self):
        self.environment = ENVIRONMENT
        self.endpoint_client = None
        self.generative_model = None
        self.hf_api_key = None
        self.deployment_info = None
        
        # Try to load deployment info
        self._load_deployment_info()
        
        # Initialize in order of preference - use deployed endpoint if available
        if VERTEX_AI_AVAILABLE and self.deployment_info:
            # 1. First try deployed endpoint
            if self._init_deployed_endpoint():
                logger.info("✅ Using deployed Gemma endpoint (primary)")
            # 2. Fall back to Generative AI
            elif self._init_generative_ai():
                logger.info("✅ Using Generative AI API (fallback)")
            # 3. Final fallback to HuggingFace
            else:
                self._init_huggingface()
                logger.info("✅ Using HuggingFace (final fallback)")
        else:
            # Non-production: use HuggingFace
            self._init_huggingface()
    
    def _load_deployment_info(self):
        """Load deployment information if available"""
        try:
            deployment_file = "gemma_deployment_info.json"
            if os.path.exists(deployment_file):
                with open(deployment_file, 'r') as f:
                    self.deployment_info = json.load(f)
                logger.info(f"Loaded deployment info from {deployment_file}")
        except Exception as e:
            logger.error(f"Failed to load deployment info: {e}")
            self.deployment_info = None
    
    def _init_deployed_endpoint(self) -> bool:
        """Initialize deployed model endpoint"""
        if not self.deployment_info:
            return False
            
        try:
            project_id = os.getenv("GCP_PROJECT_ID", self.deployment_info.get("project_id"))
            location = os.getenv("GCP_LOCATION", self.deployment_info.get("location", "us-central1"))
            
            # Initialize AI Platform
            aiplatform.init(project=project_id, location=location)
            
            # Get endpoint
            endpoint_name = self.deployment_info.get("endpoint_resource_name")
            if not endpoint_name:
                endpoint_id = self.deployment_info.get("endpoint_id")
                if endpoint_id:
                    endpoint_name = f"projects/{project_id}/locations/{location}/endpoints/{endpoint_id}"
            if not endpoint_name:
                logger.error("No endpoint resource name in deployment info")
                return False
            
            self.endpoint_client = aiplatform.Endpoint(endpoint_name)
            
            # Test the endpoint
            test_response = self.endpoint_client.predict(
                instances=[{
                    "prompt": "Test",
                    "temperature": 0.1,
                    "max_tokens": 10
                }]
            )
            
            logger.info(f"Deployed endpoint initialized: {endpoint_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize deployed endpoint: {e}")
            return False
    
    def _init_generative_ai(self) -> bool:
        """Initialize Generative AI API as fallback"""
        try:
            project_id = os.getenv("GCP_PROJECT_ID")
            location = os.getenv("GCP_LOCATION", "us-central1")
            
            vertexai.init(project=project_id, location=location)
            
            # Use Gemma 2 9B via Generative AI
            self.generative_model = GenerativeModel("gemma-2-9b-it")
            self.generation_config = GenerationConfig(
                temperature=LLM_TEMPERATURE,
                max_output_tokens=LLM_MAX_TOKENS,
                top_p=0.9,
                top_k=40
            )
            
            logger.info(f"Generative AI initialized for project {project_id} in {location}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Generative AI: {e}")
            return False
    
    def _init_huggingface(self):
        """Initialize HuggingFace as final fallback"""
        self.hf_api_key = settings.huggingface_api_key
        self.hf_model_id = "HuggingFaceH4/zephyr-7b-beta"
        self.hf_api_url = f"https://api-inference.huggingface.co/models/{self.hf_model_id}"
        
        if not self.hf_api_key:
            logger.error("No HuggingFace API key found!")
        else:
            logger.info(f"HuggingFace initialized with {self.hf_model_id}")

    async def analyze_query(self, query: str, context: Optional[Dict] = None) -> GemmaResponse:
        """Analyze query for intent and context understanding"""
        prompt = self._build_analysis_prompt(query, context)
        
        # Try in order of preference
        if self.endpoint_client:
            return await self._call_deployed_endpoint(prompt)
        elif self.generative_model:
            return await self._call_generative_ai(prompt)
        else:
            return await self._call_huggingface(prompt)

    def _build_analysis_prompt(self, query: str, context: Optional[Dict] = None) -> str:
        """Build prompt for grocery query analysis with Aloha decision-making"""
        
        # Build context string
        context_str = ""
        if context:
            if context.get("recent_products"):
                products_list = ', '.join(p['name'] for p in context['recent_products'][:3])
                context_str += f"Recent search results: {products_list}\n"
            if context.get("current_cart"):
                cart_items = len(context['current_cart'])
                context_str += f"Current cart: {cart_items} items\n"
            if context.get("last_intent"):
                context_str += f"Last action: {context['last_intent']}\n"
        
        # Enhanced prompt with Aloha approach for conversational understanding
        prompt = f"""You are an intelligent grocery shopping assistant with natural language understanding capabilities.

Your task: Analyze user input, determine intent, and make decisions for online ordering operations.

USER INPUT: "{query}"
CONTEXT:
{context_str}

ANALYSIS APPROACH:
1. **Input Processing**: Break down the input into tokens and identify key phrases
2. **Intent Classification**: Determine what the user wants to accomplish
3. **Entity Extraction**: Identify products, quantities, attributes mentioned
4. **Decision Making**: Choose appropriate action based on conversational context

INTENT PATTERNS (with natural language variations):
- **Product Search**: "I need", "looking for", "find me", "do you have", "where is"
- **Add to Cart**: "I'll take", "add", "throw in", "grab", "get me", "put in", "yes", "sounds good", "that one"
- **Remove from Cart**: "remove", "take out", "don't want", "delete", "drop", "forget", "actually no"
- **Update Cart**: "make it", "change to", "instead", "double it", "more", "less", "switch"
- **View Cart**: "what's in", "show me", "my cart", "my order", "what do I have"
- **Checkout**: "checkout", "done", "that's it", "place order", "confirm", "looks good"
- **Help/Info**: "help", "how", "what can", "explain"

CONVERSATIONAL CONTEXT RULES:
- If recent products shown + affirmative response ("yes", "sounds good") → likely ADD_TO_ORDER
- If user says "that" or "those" → refers to recent search results
- If quantity mentioned without product → applies to recent products
- Voice patterns: casual language, contractions, incomplete sentences are normal

OUTPUT FORMAT (JSON only):
{{
  "intent": "one_of_[product_search, add_to_order, update_order, remove_from_order, confirm_order, list_order, help, unclear]",
  "entities": ["products_or_references_mentioned"],
  "quantities": ["any_numbers_or_amounts"],
  "attributes": ["organic", "brand_names", "sizes"],
  "confidence": 0.95,
  "search_alpha": 0.3,
  "reasoning": "brief_explanation_of_decision"
}}"""
        
        return prompt

    async def _call_deployed_endpoint(self, prompt: str) -> GemmaResponse:
        """Call deployed model endpoint"""
        try:
            # Prepare instance for prediction
            instance = {
                "prompt": prompt,
                "temperature": LLM_TEMPERATURE,
                "max_tokens": LLM_MAX_TOKENS,
                "top_p": 0.9,
                "top_k": 40
            }
            
            # Make prediction
            start_time = asyncio.get_event_loop().time()
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.endpoint_client.predict(instances=[instance])
            )
            latency = (asyncio.get_event_loop().time() - start_time) * 1000
            
            # Extract prediction
            if response.predictions:
                generated_text = response.predictions[0]
                logger.info(f"Deployed endpoint response ({latency:.2f}ms): {generated_text[:200]}...")
                
                return self._parse_response(generated_text)
            else:
                raise Exception("No predictions returned")
                
        except Exception as e:
            logger.error(f"Deployed endpoint error: {e}, falling back to Generative AI")
            # Try fallback
            if self._init_generative_ai():
                return await self._call_generative_ai(prompt)
            elif self._init_huggingface():
                return await self._call_huggingface(prompt)
            else:
                return GemmaResponse(
                    text="",
                    intent="unclear",
                    confidence=0.0
                )

    async def _call_generative_ai(self, prompt: str) -> GemmaResponse:
        """Call Generative AI API"""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.generative_model.generate_content(
                    prompt,
                    generation_config=self.generation_config
                )
            )
            
            generated_text = response.text
            logger.info(f"Generative AI response: {generated_text[:200]}...")
            
            return self._parse_response(generated_text)
            
        except Exception as e:
            logger.error(f"Generative AI error: {e}, falling back to HuggingFace")
            # Try final fallback
            if not self.hf_api_key:
                self._init_huggingface()
            return await self._call_huggingface(prompt)

    async def _call_huggingface(self, prompt: str) -> GemmaResponse:
        """Call HuggingFace Inference API"""
        headers = {
            "Authorization": f"Bearer {self.hf_api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": LLM_MAX_TOKENS,
                "temperature": LLM_TEMPERATURE,
                "do_sample": False,
                "return_full_text": False,
                "repetition_penalty": 1.1
            }
        }

        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
                response = await client.post(self.hf_api_url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    generated_text = result[0]["generated_text"] if isinstance(result, list) else result.get("generated_text", "")
                    logger.info(f"HuggingFace response: {generated_text[:200]}...")
                    
                    return self._parse_response(generated_text)
                else:
                    logger.error(f"HuggingFace API error: {response.status_code}")
                    return GemmaResponse(
                        text="",
                        intent="unclear",
                        confidence=0.0,
                        metadata={}
                    )

        except Exception as e:
            logger.error(f"HuggingFace error: {str(e)}")
            return GemmaResponse(
                text="",
                intent="unclear",
                confidence=0.0
            )

    def _parse_response(self, generated_text: str) -> GemmaResponse:
        """Parse JSON response from any model with enhanced Aloha understanding"""
        try:
            # Look for JSON in the response
            json_start = generated_text.find("{")
            json_end = generated_text.rfind("}") + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = generated_text[json_start:json_end]
                parsed = json.loads(json_str)
                
                # Extract enhanced metadata
                metadata = {
                    "entities": parsed.get("entities", []),
                    "quantities": parsed.get("quantities", []),
                    "attributes": parsed.get("attributes", []),
                    "search_alpha": parsed.get("search_alpha", 0.5),
                    "reasoning": parsed.get("reasoning", ""),
                    "raw_response": generated_text
                }
                
                return GemmaResponse(
                    text=generated_text,
                    intent=parsed.get("intent", "unclear"),
                    confidence=parsed.get("confidence", 0.5),
                    metadata=metadata
                )
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}, attempting fallback parsing")
        
        # Enhanced fallback parsing with conversational patterns
        return self._fallback_parse(generated_text)
    
    def _fallback_parse(self, text: str) -> GemmaResponse:
        """Enhanced fallback parsing for conversational understanding"""
        text_lower = text.lower()
        
        # Enhanced intent detection patterns
        if any(phrase in text_lower for phrase in ["add", "take", "grab", "throw", "yes", "sounds good", "i'll have"]):
            intent = "add_to_order"
            confidence = 0.8
        elif any(phrase in text_lower for phrase in ["remove", "delete", "don't want", "take it out", "take out", "forget"]):
            intent = "remove_from_order"
            confidence = 0.8
        elif any(phrase in text_lower for phrase in ["show", "what's in", "cart", "what do i have", "my order", "list"]):
            intent = "list_order"
            confidence = 0.8
        elif any(phrase in text_lower for phrase in ["checkout", "done", "confirm", "place my order", "place order", "that's it"]):
            intent = "confirm_order"
            confidence = 0.8
        elif any(phrase in text_lower for phrase in ["need", "looking for", "find", "search", "do you have"]):
            intent = "product_search"
            confidence = 0.8
        else:
            intent = "unclear"
            confidence = 0.3
        
        # Extract basic entities (simple approach)
        import re
        quantities = re.findall(r'\b\d+\b', text)
        
        metadata = {
            "entities": [],
            "quantities": quantities,
            "attributes": [],
            "search_alpha": 0.5,
            "reasoning": f"Fallback parsing detected: {intent}",
            "raw_response": text
        }
        
        return GemmaResponse(
            text=text,
            intent=intent,
            confidence=confidence,
            metadata=metadata
        )

    async def calculate_dynamic_alpha(self, query: str) -> float:
        """Calculate optimal alpha value for search"""
        
        # If we have a deployed endpoint with fine-tuning, it should return alpha
        if self.endpoint_client or self.generative_model:
            response = await self.analyze_query(query)
            if response.metadata and "search_alpha" in response.metadata:
                return response.metadata["search_alpha"]
        
        # Fallback to simple heuristics
        query_lower = query.lower()
        
        # Specific product/brand names = low alpha (keyword search)
        specific_brands = ["oatly", "horizon", "organic valley", "nature's path"]
        if any(brand in query_lower for brand in specific_brands):
            return 0.1
        
        # Exploratory queries = high alpha (semantic search)
        exploratory_terms = ["ideas", "suggestions", "what's good", "recommendations", "help me"]
        if any(term in query_lower for term in exploratory_terms):
            return 0.8
        
        # Category searches = medium alpha
        category_terms = ["breakfast", "dairy", "snacks", "frozen", "produce"]
        if any(term in query_lower for term in category_terms):
            return 0.5
        
        # Default balanced
        return 0.5

    async def enhance_search_query(self, query: str) -> str:
        """Enhance search query with understanding"""
        
        # Quick enhancement without full LLM call for performance
        query_lower = query.lower()
        
        # Expand common abbreviations
        replacements = {
            "gf": "gluten free",
            "df": "dairy free",
            "org": "organic",
            "ww": "whole wheat",
            "pb": "peanut butter"
        }
        
        enhanced = query
        for abbr, full in replacements.items():
            if f" {abbr} " in f" {query_lower} ":
                enhanced = enhanced.replace(abbr, full)
        
        return enhanced.strip()
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about current model configuration"""
        if self.endpoint_client:
            return {
                "type": "deployed_endpoint",
                "model": "gemma-2-9b-it",
                "endpoint": self.deployment_info.get("endpoint_id", "unknown"),
                "fine_tuned": self.deployment_info.get("fine_tuned", False)
            }
        elif self.generative_model:
            return {
                "type": "generative_ai",
                "model": "gemma-2-9b-it",
                "location": os.getenv("GCP_LOCATION", "us-central1")
            }
        else:
            return {
                "type": "huggingface",
                "model": self.hf_model_id
            }

# Create singleton instance
gemma_client = GemmaClientV2()