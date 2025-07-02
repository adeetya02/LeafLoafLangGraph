"""
Production-ready Gemma client using deployed Gemma 2 9B endpoint
Optimized for production use with real-time flow tracking
"""

import os
import json
import time
import asyncio
from typing import Dict, Optional, Any, Callable
from datetime import datetime
from google.cloud import aiplatform
import google.auth
import structlog

logger = structlog.get_logger()

class GemmaProductionClient:
    """Production client using deployed Gemma 2 9B endpoint"""
    
    def __init__(self, flow_callback: Optional[Callable] = None):
        # Initialize Vertex AI
        self.project_id = os.getenv("GCP_PROJECT_ID", "leafloafai")
        self.location = os.getenv("GCP_LOCATION", "us-central1")
        self.endpoint_id = "1487855836171599872"  # Gemma 2 9B endpoint
        self.flow_callback = flow_callback
        
        # Initialize Vertex AI
        aiplatform.init(project=self.project_id, location=self.location)
        
        # Get endpoint
        self.endpoint = aiplatform.Endpoint(self.endpoint_id)
        
        logger.info(f"GemmaProductionClient initialized with Gemma 2 9B endpoint: {self.endpoint_id}")
    
    async def analyze_query(self, query: str, user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Analyze query for intent and alpha value"""
        
        # Build optimized prompt
        prompt = self._build_fast_prompt(query, user_context)
        
        try:
            start = time.time()
            
            # Generate response
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.model.generate_content(
                    prompt,
                    generation_config=self.generation_config
                )
            )
            
            latency = (time.time() - start) * 1000
            
            if response and response.text:
                # Parse response
                analysis = self._parse_response(response.text)
                
                logger.info(f"Gemini analysis completed in {latency:.0f}ms")
                
                return {
                    "intent": analysis.get("intent", "product_search"),
                    "confidence": analysis.get("confidence", 0.8),
                    "metadata": {
                        "search_alpha": analysis.get("alpha", 0.5),
                        "latency_ms": latency,
                        "model": "gemini-1.5-flash"
                    }
                }
            else:
                logger.warning("Empty response from Gemini")
                return self._fallback_response(query)
                
        except asyncio.TimeoutError:
            logger.warning("Gemini timeout")
            return self._fallback_response(query)
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return self._fallback_response(query)
    
    def _build_fast_prompt(self, query: str, user_context: Optional[Dict] = None) -> str:
        """Build ultra-concise prompt for speed"""
        
        # No context for speed - just analyze the query
        return f"""Grocery query: "{query}"

Return JSON only:
{{"intent": "...", "alpha": 0.X, "context": {{}}}}

intent: search|order|reorder|browse|recommendation
alpha: 0=keyword, 1=semantic

Examples:
"milk" -> {{"intent": "search", "alpha": 0.4, "context": {{}}}}
"add milk to cart" -> {{"intent": "order", "alpha": 0.5, "context": {{"action": "add"}}}}
"my usual items" -> {{"intent": "reorder", "alpha": 0.7, "context": {{"usual": true}}}}

JSON:"""
    
    def _parse_response(self, text: str) -> Dict[str, Any]:
        """Parse JSON from response"""
        try:
            # Extract JSON
            import re
            
            # Try to find JSON in response
            json_match = re.search(r'\{[^}]+\}', text)
            if json_match:
                return json.loads(json_match.group())
            
            # Try direct parse
            cleaned = text.strip()
            if cleaned.startswith('{'):
                return json.loads(cleaned)
                
        except Exception as e:
            logger.warning(f"Failed to parse response: {text}, error: {e}")
        
        return {}
    
    def _fallback_response(self, query: str) -> Dict[str, Any]:
        """Quick pattern-based fallback"""
        query_lower = query.lower()
        
        # Quick patterns
        if any(word in query_lower for word in ["add", "put", "throw"]):
            return {
                "intent": "add_to_order",
                "confidence": 0.7,
                "metadata": {"search_alpha": 0.5, "latency_ms": 0, "model": "fallback"}
            }
        elif any(word in query_lower for word in ["cart", "basket", "order", "checkout"]):
            return {
                "intent": "list_order",
                "confidence": 0.7,
                "metadata": {"search_alpha": 0.5, "latency_ms": 0, "model": "fallback"}
            }
        elif any(word in query_lower for word in ["promo", "deal", "discount", "offer"]):
            return {
                "intent": "promotion_query",
                "confidence": 0.8,
                "metadata": {"search_alpha": 0.5, "latency_ms": 0, "model": "fallback"}
            }
        else:
            # Default to search
            # Estimate alpha based on query complexity
            word_count = len(query_lower.split())
            has_brand = any(brand in query_lower for brand in ["amul", "tata", "fortune", "nestle"])
            
            if has_brand or word_count <= 2:
                alpha = 0.3  # Keyword focused
            elif word_count >= 5 or "organic" in query_lower or "healthy" in query_lower:
                alpha = 0.7  # Semantic focused
            else:
                alpha = 0.5  # Balanced
            
            return {
                "intent": "product_search",
                "confidence": 0.6,
                "metadata": {"search_alpha": alpha, "latency_ms": 0, "model": "fallback"}
            }


# Singleton instance for connection reuse
_production_client = None

def get_production_client() -> GemmaProductionClient:
    """Get singleton client instance"""
    global _production_client
    if _production_client is None:
        _production_client = GemmaProductionClient()
    return _production_client