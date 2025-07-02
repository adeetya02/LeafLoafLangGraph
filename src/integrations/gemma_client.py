import os
import asyncio
import re
from typing import Dict, List, Optional
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

logger = structlog.get_logger()

# Conditional imports for Vertex AI
try:
    from google.cloud import aiplatform
    import vertexai
    from vertexai.generative_models import GenerativeModel, GenerationConfig
    VERTEX_AI_AVAILABLE = True
except ImportError:
    VERTEX_AI_AVAILABLE = False
    logger.warning("Vertex AI not available, using HuggingFace")

class GemmaResponse(BaseModel):
  text: str
  intent: Optional[str] = None
  confidence: Optional[float] = None
  metadata: Optional[Dict] = None

class GemmaClient:
  """Client for Gemma 2 9B integration - supports both HuggingFace and Vertex AI"""

  def __init__(self):
      self.environment = ENVIRONMENT
      self.use_vertex = False
      self.vertex_model = None
      
      # Initialize based on environment
      if self.environment == "production" and VERTEX_AI_AVAILABLE:
          try:
              # Initialize Vertex AI
              project_id = os.getenv("GCP_PROJECT_ID")
              location = os.getenv("GCP_LOCATION", "us-central1")
              
              vertexai.init(project=project_id, location=location)
              
              # Try to use Gemma 2 from Model Garden endpoint first
              gemma_endpoint = os.getenv("VERTEX_AI_ENDPOINT_RESOURCE_NAME")
              if gemma_endpoint:
                  # TODO: Use Gemma endpoint when available
                  logger.info(f"Gemma endpoint configured: {gemma_endpoint}")
              
              # Use Gemini 1.5 Flash as primary (zero latency on GCP)
              self.vertex_model = GenerativeModel("gemini-1.5-flash")
              self.generation_config = GenerationConfig(
                  temperature=LLM_TEMPERATURE,
                  max_output_tokens=LLM_MAX_TOKENS,
                  top_p=0.9,
                  top_k=40
              )
              self.use_vertex = True
              logger.info(f"Vertex AI Gemini 1.5 Flash initialized for project {project_id} in {location}")
              
          except Exception as e:
              logger.error(f"Failed to initialize Vertex AI: {e}, falling back to HuggingFace")
              self._init_huggingface()
      else:
          self._init_huggingface()
  
  def _init_huggingface(self):
      """Initialize HuggingFace as fallback"""
      self.hf_api_key = settings.huggingface_api_key
      # Try Mistral first, then Zephyr as fallback
      self.fallback_models = [
          "mistralai/Mistral-7B-Instruct-v0.2",
          "HuggingFaceH4/zephyr-7b-beta"
      ]
      self.hf_model_id = self.fallback_models[0]  # Start with Mistral
      self.hf_api_url = f"https://api-inference.huggingface.co/models/{self.hf_model_id}"
      self.use_vertex = False
      
      if not self.hf_api_key:
          logger.error("No HuggingFace API key found!")
      else:
          logger.info(f"LLM client initialized with {self.hf_model_id}")

  async def analyze_query(self, query: str, context: Optional[Dict] = None) -> GemmaResponse:
      """Analyze query for intent and context understanding"""

      prompt = self._build_analysis_prompt(query, context)

      if self.use_vertex:
          try:
              # Try Vertex AI (Gemini 1.5) first - near zero latency on GCP
              response = await self._call_vertex_ai(prompt)
              if response.intent != "unclear" or response.confidence > 0.0:
                  return response
              else:
                  logger.warning("Vertex AI returned unclear intent, trying HuggingFace")
                  return await self._call_huggingface(prompt)
          except Exception as e:
              logger.error(f"Vertex AI failed: {e}, falling back to HuggingFace")
              return await self._call_huggingface(prompt)
      else:
          return await self._call_huggingface(prompt)

  def _build_analysis_prompt(self, query: str, context: Optional[Dict] = None) -> str:
      """Build prompt for Zephyr to analyze grocery queries"""

      # Zephyr uses <|system|> and <|user|> tags
      prompt = f"""<|system|>
You are a grocery shopping assistant. Analyze queries and respond ONLY with valid JSON.
<|end|>
<|user|>
Analyze this query and respond ONLY with valid JSON.

Query: "{query}"

Previous context: {context if context else "None"}

Analyze and return JSON with:
1. intent: One of [product_search, add_to_order, update_order, remove_from_order, confirm_order, list_order, meal_planning, help, unclear]
2. entities: List of products/items mentioned
3. quantities: Any quantities mentioned
4. attributes: Dietary preferences, brands, or specifications
5. confidence: 0.0 to 1.0

Example response:
{{
"intent": "add_to_order",
"entities": ["bananas", "milk"],
"quantities": {{"bananas": 6, "milk": 1}},
"attributes": ["organic", "2%"],
"confidence": 0.9
}}

<|end|>
<|assistant|>"""

      return prompt

  async def _call_vertex_ai(self, prompt: str) -> GemmaResponse:
      """Call Vertex AI Gemma model"""
      try:
          # Vertex AI synchronous call (we'll wrap it)
          response = await asyncio.get_event_loop().run_in_executor(
              None,
              lambda: self.vertex_model.generate_content(
                  prompt,
                  generation_config=self.generation_config
              )
          )
          
          generated_text = response.text
          logger.info(f"Vertex AI response: {generated_text[:200]}...")
          
          # Parse JSON from response
          import json
          try:
              # Look for JSON in the response
              json_start = generated_text.find("{")
              json_end = generated_text.rfind("}") + 1
              
              if json_start >= 0 and json_end > json_start:
                  json_str = generated_text[json_start:json_end]
                  parsed = json.loads(json_str)
                  
                  return GemmaResponse(
                      text=generated_text,
                      intent=parsed.get("intent"),
                      confidence=parsed.get("confidence", 0.5),
                      metadata=parsed
                  )
          except json.JSONDecodeError:
              pass
          
          # Fallback if no JSON
          return GemmaResponse(
              text=generated_text,
              intent="product_search",  # Default intent
              confidence=0.7
          )
          
      except Exception as e:
          logger.error(f"Vertex AI error: {e}")
          return GemmaResponse(
              text="",
              intent="unclear",
              confidence=0.0
          )

  async def _call_huggingface(self, prompt: str) -> GemmaResponse:
      """Call HuggingFace Inference API with fallback models"""
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

      # Try each fallback model in order
      for i, model_id in enumerate(self.fallback_models):
          try:
              model_url = f"https://api-inference.huggingface.co/models/{model_id}"
              logger.info(f"Calling {model_id} with prompt length: {len(prompt)} chars")
              
              async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
                  response = await client.post(model_url, headers=headers, json=payload)
                  logger.info(f"{model_id} response status: {response.status_code}")

                  if response.status_code == 200:
                      result = response.json()
                      generated_text = result[0]["generated_text"] if isinstance(result, list) else result.get("generated_text", "")
                      logger.info(f"Raw LLM response from {model_id}: {generated_text[:200]}...")
                      
                      # Update the current model for future calls
                      self.hf_model_id = model_id
                      self.hf_api_url = model_url
                      
                      # Parse JSON from response
                      import json
                      try:
                          parsed = json.loads(generated_text.strip())
                          return GemmaResponse(
                              text=generated_text,
                              intent=parsed.get("intent"),
                              confidence=parsed.get("confidence", 0.5),
                              metadata=parsed
                          )
                      except json.JSONDecodeError:
                          # Fallback if JSON parsing fails
                          return GemmaResponse(
                              text=generated_text,
                              intent="unclear",
                              confidence=0.3
                          )
                  else:
                      error_detail = response.text[:200] if response.text else "No error details"
                      logger.warning(f"{model_id} failed with {response.status_code} - {error_detail}, trying next model...")
                      # Continue to next model
                      continue
                      
          except Exception as e:
              logger.error(f"{model_id} error: {str(e)}, trying next model...")
              # Continue to next model
              continue
      
      # If all models failed
      logger.error("All LLM models failed")
      return GemmaResponse(
          text="",
          intent="unclear",
          confidence=0.0
      )

  async def enhance_search_query(self, query: str) -> str:
      """Enhance search query with LLM understanding"""
      prompt = f"""<|system|>
Enhance grocery search queries by expanding abbreviations, fixing typos, and adding relevant terms.
<|end|>
<|user|>
Query: "{query}"

Return only the enhanced query, nothing else.
<|end|>
<|assistant|>"""

      response = await self._call_huggingface(prompt)
      return response.text.strip() if response.text else query

  async def calculate_dynamic_alpha(self, query: str) -> float:
      """Use LLM to determine optimal alpha for search"""
      
      # Build prompt appropriate for both Gemini and HuggingFace models
      if self.use_vertex:
          prompt = f"""Determine the search alpha value for this grocery query. Alpha controls search strategy:
- 0.0-0.3: Keyword search for specific products/brands
- 0.3-0.5: Balanced for product types 
- 0.5-0.7: More semantic for categories
- 0.7-1.0: Semantic for exploratory queries

Query: "{query}"

Examples:
- "Oatly barista edition" → 0.1
- "organic oat milk" → 0.3
- "milk" → 0.5
- "breakfast ideas" → 0.8

Return only a decimal number between 0.0 and 1.0"""
      else:
          prompt = f"""<|system|>
Determine search alpha value for grocery queries. Alpha controls search strategy:
- 0.0-0.3: Keyword search for specific products/brands
- 0.3-0.5: Balanced for product types 
- 0.5-0.7: More semantic for categories
- 0.7-1.0: Semantic for exploratory queries
<|end|>
<|user|>
Query: "{query}"

Examples:
- "Oatly barista edition" → 0.1
- "organic oat milk" → 0.3
- "milk" → 0.5
- "breakfast ideas" → 0.8

Return only a decimal number between 0.0 and 1.0
<|end|>
<|assistant|>"""

      # Try appropriate model
      if self.use_vertex:
          try:
              response = await self._call_vertex_ai(prompt)
          except Exception as e:
              logger.error(f"Vertex AI failed for alpha: {e}, using HuggingFace")
              response = await self._call_huggingface(prompt)
      else:
          response = await self._call_huggingface(prompt)
          
      try:
          import re
          # Extract decimal number from verbose response
          text = response.text.strip()
          # Look for patterns like "0.3" or "alpha value of 0.3" or "suggest 0.3"
          numbers = re.findall(r'(?:alpha.*?|suggest.*?|value.*?)?(\d+\.\d+)', text, re.IGNORECASE)
          if numbers:
              alpha = float(numbers[0])
              logger.info(f"Extracted alpha: {alpha} from response")
              return max(0.0, min(1.0, alpha))
          else:
              logger.warning(f"No alpha found in response: {text[:100]}")
              return 0.5
      except Exception as e:
          logger.error(f"Error parsing alpha: {e}")
          return 0.5  # Default fallback