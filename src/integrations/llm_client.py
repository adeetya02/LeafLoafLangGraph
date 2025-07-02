"""
LLM Client that works with available models
Falls back to models that are actually available on HuggingFace free tier
"""
import os
import json
import time
from typing import Dict, Optional
import httpx
import structlog
from pydantic import BaseModel
from src.config.settings import settings

logger = structlog.get_logger()

class LLMAnalysis(BaseModel):
    """Analysis result from LLM"""
    intent: str
    confidence: float
    enhanced_query: str
    alpha_value: float
    entities: list
    attributes: list
    reasoning: str

class LLMClient:
    """LLM client that uses available models"""
    
    def __init__(self):
        self.hf_api_key = settings.huggingface_api_key
        # Use Mistral as it's reliable and available on free tier
        self.model_id = "mistralai/Mistral-7B-Instruct-v0.2"
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model_id}"
        
        logger.info(f"LLM client using {self.model_id}")
        
    async def analyze_query(self, query: str, context: Optional[Dict] = None) -> LLMAnalysis:
        """Analyze query for intent and search parameters"""
        
        prompt = f"""[INST] You are a grocery shopping assistant. Analyze this query and return ONLY valid JSON.

Query: "{query}"

Determine:
1. Intent: Is the user searching for products, adding to cart, viewing cart, or confirming order?
2. Alpha: How specific is the search? (0.0=very specific like brand names, 1.0=exploratory like meal ideas)
3. Enhanced query: Improve the query for better search results

Return ONLY this JSON structure:
{{
  "intent": "product_search",
  "confidence": 0.9,
  "enhanced_query": "{query}",
  "alpha_value": 0.3,
  "entities": ["oat", "milk"],
  "attributes": ["organic"],
  "reasoning": "User wants specific organic oat milk products"
}}

Examples:
- "organic oat milk" → alpha: 0.3 (specific product type)
- "Oatly" → alpha: 0.1 (brand search)
- "dinner ideas" → alpha: 0.8 (exploratory)

[/INST] JSON Response:"""

        try:
            response_text = await self._call_llm(prompt)
            return self._parse_response(response_text, query)
        except Exception as e:
            logger.error(f"LLM error: {e}, using fallback")
            return self._get_fallback_analysis(query)
    
    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM API"""
        headers = {
            "Authorization": f"Bearer {self.hf_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 150,
                "temperature": 0.1,
                "top_p": 0.9,
                "do_sample": True,
                "return_full_text": False
            }
        }
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(self.api_url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list):
                    return result[0].get("generated_text", "")
                return result.get("generated_text", "")
            elif response.status_code == 503:
                # Model loading, wait and retry once
                logger.info("Model loading, waiting 10s...")
                await asyncio.sleep(10)
                response = await client.post(self.api_url, headers=headers, json=payload)
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, list):
                        return result[0].get("generated_text", "")
                    return result.get("generated_text", "")
            
            raise Exception(f"API error: {response.status_code} - {response.text[:200]}")
    
    def _parse_response(self, response_text: str, original_query: str) -> LLMAnalysis:
        """Parse LLM response"""
        try:
            # Find JSON in response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                data = json.loads(json_str)
                
                return LLMAnalysis(
                    intent=data.get("intent", "product_search"),
                    confidence=float(data.get("confidence", 0.8)),
                    enhanced_query=data.get("enhanced_query", original_query),
                    alpha_value=float(data.get("alpha_value", 0.5)),
                    entities=data.get("entities", []),
                    attributes=data.get("attributes", []),
                    reasoning=data.get("reasoning", "")
                )
        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")
        
        return self._get_fallback_analysis(original_query)
    
    def _get_fallback_analysis(self, query: str) -> LLMAnalysis:
        """Simple fallback when LLM fails"""
        query_lower = query.lower()
        
        # Basic intent detection
        if any(word in query_lower for word in ["add", "put"]):
            intent = "add_to_order"
        elif any(word in query_lower for word in ["cart", "order"]) and "show" in query_lower:
            intent = "show_cart"
        elif "confirm" in query_lower or "checkout" in query_lower:
            intent = "confirm_order"
        else:
            intent = "product_search"
        
        # Basic alpha calculation
        # More specific = lower alpha
        specificity_score = 0
        
        # Product words = more specific
        if any(word in query_lower for word in ["milk", "bread", "eggs", "cheese"]):
            specificity_score += 2
            
        # Attributes = more specific  
        if any(word in query_lower for word in ["organic", "gluten-free", "vegan"]):
            specificity_score += 1
            
        # Brand names = very specific
        if any(word in query_lower for word in ["oatly", "horizon", "pacific"]):
            specificity_score += 3
        
        # Convert to alpha (higher specificity = lower alpha)
        alpha = max(0.2, 0.8 - (specificity_score * 0.2))
        
        return LLMAnalysis(
            intent=intent,
            confidence=0.7,
            enhanced_query=query,
            alpha_value=alpha,
            entities=[],
            attributes=[],
            reasoning="Fallback analysis"
        )

# Import asyncio for retry logic
import asyncio