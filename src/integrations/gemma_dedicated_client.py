"""
Gemma client for dedicated Vertex AI endpoint
Optimized for <50ms latency
"""

import os
import json
import time
import asyncio
from typing import Dict, Optional, Any
import httpx
from google.auth.transport.requests import Request
import google.auth
import structlog

logger = structlog.get_logger()

class GemmaDedicatedClient:
    """Client for Gemma dedicated endpoint with direct HTTPS access"""
    
    def __init__(self):
        # Load credentials
        self.credentials, self.project = google.auth.default()
        
        # Endpoint configuration
        self.endpoint_id = "6438719201535328256"
        self.project_number = "32905605817"
        self.location = "us-central1"
        
        # Build endpoint URL
        self.endpoint_host = f"{self.endpoint_id}.{self.location}-{self.project_number}.prediction.vertexai.goog"
        self.endpoint_url = f"https://{self.endpoint_host}/v1/projects/{self.project_number}/locations/{self.location}/endpoints/{self.endpoint_id}:predict"
        
        # HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=5.0,
                read=10.0,
                write=10.0,
                pool=5.0
            ),
            limits=httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10,
                keepalive_expiry=30.0
            ),
        )
        
        logger.info(f"GemmaDedicatedClient initialized for endpoint: {self.endpoint_host}")
    
    async def analyze_query(self, query: str, user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Analyze query for intent and alpha value"""
        
        # Build prompt
        prompt = self._build_prompt(query, user_context)
        
        # Ensure token is fresh
        if hasattr(self.credentials, 'refresh'):
            self.credentials.refresh(Request())
        
        # Prepare request
        headers = {
            "Authorization": f"Bearer {self.credentials.token}",
            "Content-Type": "application/json",
        }
        
        data = {
            "instances": [{
                "prompt": prompt,
            }],
            "parameters": {
                "temperature": 0.3,
                "maxOutputTokens": 100,
                "topK": 10,
                "topP": 0.9,
                "candidateCount": 1
            }
        }
        
        try:
            start = time.time()
            response = await self.client.post(
                self.endpoint_url,
                json=data,
                headers=headers
            )
            latency = (time.time() - start) * 1000
            
            if response.status_code == 200:
                result = response.json()
                
                # Parse response
                predictions = result.get("predictions", [])
                if predictions:
                    text = predictions[0].get("content", "") or predictions[0].get("text", "")
                    
                    # Extract JSON from response
                    analysis = self._parse_response(text)
                    
                    logger.info(f"Gemma analysis completed in {latency:.0f}ms")
                    
                    return {
                        "intent": analysis.get("intent", "product_search"),
                        "confidence": analysis.get("confidence", 0.8),
                        "metadata": {
                            "search_alpha": analysis.get("alpha", 0.5),
                            "latency_ms": latency,
                            "endpoint": "dedicated"
                        }
                    }
                else:
                    logger.warning(f"Empty predictions from Gemma")
                    return self._fallback_response(query)
                    
            else:
                logger.error(f"Gemma endpoint error: {response.status_code} - {response.text}")
                return self._fallback_response(query)
                
        except asyncio.TimeoutError:
            logger.warning("Gemma timeout")
            return self._fallback_response(query)
        except Exception as e:
            logger.error(f"Gemma error: {e}")
            return self._fallback_response(query)
    
    def _build_prompt(self, query: str, user_context: Optional[Dict] = None) -> str:
        """Build optimized prompt for intent analysis"""
        
        context_str = ""
        if user_context and "recent_products" in user_context:
            products = user_context["recent_products"][:3]
            context_str = f"\nRecent searches: {', '.join(p.get('name', '') for p in products)}"
        
        return f"""Analyze this grocery query and respond with JSON only:
Query: "{query}"{context_str}

Determine:
1. intent: product_search, add_to_order, list_order, remove_from_order, or promotion_query
2. confidence: 0-1
3. alpha: 0-1 (0=keyword focused, 1=semantic focused)

Examples:
- "milk" -> {{"intent": "product_search", "confidence": 0.9, "alpha": 0.3}}
- "organic vegetables" -> {{"intent": "product_search", "confidence": 0.9, "alpha": 0.7}}
- "add 2 packets" -> {{"intent": "add_to_order", "confidence": 0.8, "alpha": 0.5}}

JSON Response:"""
    
    def _parse_response(self, text: str) -> Dict[str, Any]:
        """Parse JSON from LLM response"""
        try:
            # Try to extract JSON
            import re
            json_match = re.search(r'\{[^}]+\}', text)
            if json_match:
                return json.loads(json_match.group())
            else:
                # Try direct parse
                return json.loads(text.strip())
        except:
            logger.warning(f"Failed to parse Gemma response: {text}")
            return {}
    
    def _fallback_response(self, query: str) -> Dict[str, Any]:
        """Quick fallback response based on patterns"""
        query_lower = query.lower()
        
        # Quick pattern matching
        if any(word in query_lower for word in ["add", "put", "throw"]):
            return {
                "intent": "add_to_order",
                "confidence": 0.7,
                "metadata": {"search_alpha": 0.5, "latency_ms": 0, "endpoint": "fallback"}
            }
        elif any(word in query_lower for word in ["cart", "basket", "order"]):
            return {
                "intent": "list_order", 
                "confidence": 0.7,
                "metadata": {"search_alpha": 0.5, "latency_ms": 0, "endpoint": "fallback"}
            }
        elif any(word in query_lower for word in ["promo", "deal", "discount", "offer"]):
            return {
                "intent": "promotion_query",
                "confidence": 0.8,
                "metadata": {"search_alpha": 0.5, "latency_ms": 0, "endpoint": "fallback"}
            }
        else:
            # Default to search with semantic alpha
            return {
                "intent": "product_search",
                "confidence": 0.6,
                "metadata": {"search_alpha": 0.7, "latency_ms": 0, "endpoint": "fallback"}
            }
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()