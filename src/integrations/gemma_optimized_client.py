"""
Optimized Gemma client for production use
Using dedicated endpoint: 1487855836171599872
Direct HTTPS access for best performance
"""

import os
import json
import time
import asyncio
import re
from typing import Dict, Optional, Any
import httpx
from google.auth.transport.requests import Request
import google.auth
import structlog

logger = structlog.get_logger()

class GemmaOptimizedClient:
    """Optimized client using dedicated Gemma endpoint via direct HTTPS"""
    
    def __init__(self):
        self.project_id = os.getenv("GCP_PROJECT_ID", "leafloafai")
        self.project_number = "32905605817"
        self.location = os.getenv("GCP_LOCATION", "us-central1")
        self.endpoint_id = "1487855836171599872"
        self.endpoint_domain = "1487855836171599872.us-central1-32905605817.prediction.vertexai.goog"
        
        # Build URL
        self.url = f"https://{self.endpoint_domain}/v1/projects/{self.project_number}/locations/{self.location}/endpoints/{self.endpoint_id}:predict"
        
        # Get credentials - with fallback for local development
        self.use_auth = False
        try:
            # Check if we're in GCP environment
            if os.getenv("GCP_PROJECT_ID") and os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                self.credentials, _ = google.auth.default()
                self.use_auth = True
            elif os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token"):
                # Running in GKE/Cloud Run
                self.credentials, _ = google.auth.default()
                self.use_auth = True
            else:
                raise Exception("Not in GCP environment")
        except Exception as e:
            logger.warning(f"Google auth not available (local dev?): {e}")
            self.credentials = None
            self.use_auth = False
            # Use HuggingFace for local testing
            self.hf_api_key = os.getenv("HUGGINGFACE_API_KEY")
            self.hf_model_id = "HuggingFaceH4/zephyr-7b-beta"
        
        # Token cache
        self._token = None
        self._token_expiry = None
        
        # Create HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        
        logger.info(f"GemmaOptimizedClient initialized - auth: {self.use_auth}")
    
    async def analyze_query(self, query: str, user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Analyze query using dedicated endpoint or HuggingFace fallback"""
        
        # If no auth (local dev), use HuggingFace
        if not self.use_auth:
            return await self._analyze_with_huggingface(query, user_context)
        
        # Get valid token (cached or refreshed)
        token = await self._get_valid_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        
        # Optimized prompt for Gemma - more explicit examples
        prompt = f"""User: You are a grocery shopping assistant. Analyze user queries and classify their intent.

Examples:
"I need milk" -> {{"intent": "product_search", "confidence": 0.9, "alpha": 0.5}}
"add milk to cart" -> {{"intent": "add_to_order", "confidence": 0.95, "alpha": 0.5}}
"change milk quantity to 3" -> {{"intent": "update_order", "confidence": 0.95, "alpha": 0.5}}
"remove milk" -> {{"intent": "remove_from_order", "confidence": 0.9, "alpha": 0.5}}
"checkout" -> {{"intent": "confirm_order", "confidence": 0.95, "alpha": 0.5}}
"show my cart" -> {{"intent": "list_order", "confidence": 0.95, "alpha": 0.5}}

Now analyze: "{query}"
Assistant: """
        
        payload = {
            "instances": [{
                "prompt": prompt,
            }],
            "parameters": {
                "temperature": 0.1,  # Very low for consistency
                "maxOutputTokens": 50,  # Just need JSON
                "topK": 5,
                "topP": 0.9,
                "candidateCount": 1
            }
        }
        
        try:
            start = time.time()
            
            response = await self.client.post(
                self.url,
                json=payload,
                headers=headers
            )
            
            latency = (time.time() - start) * 1000
            
            if response.status_code == 200:
                result = response.json()
                
                # Parse response
                analysis = self._parse_gemma_response(result)
                
                logger.info(f"Gemma analysis completed in {latency:.0f}ms", 
                          intent=analysis.get("intent"),
                          alpha=analysis.get("alpha"))
                
                return {
                    "intent": analysis.get("intent", "product_search"),
                    "confidence": analysis.get("confidence", 0.8),
                    "metadata": {
                        "search_alpha": analysis.get("alpha", 0.5),
                        "latency_ms": latency,
                        "endpoint": self.endpoint_id,
                        "method": "direct_https"
                    }
                }
            else:
                logger.warning(f"API error: {response.status_code}")
                return self._fallback_response(query)
                
        except asyncio.TimeoutError:
            logger.warning("Gemma timeout")
            return self._fallback_response(query)
        except Exception as e:
            logger.error(f"Gemma error: {e}")
            return self._fallback_response(query)
    
    def _parse_gemma_response(self, result: Dict) -> Dict[str, Any]:
        """Parse Gemma response and extract JSON"""
        try:
            predictions = result.get("predictions", [])
            if predictions:
                response_text = predictions[0]
                
                # The model returns "Prompt:\n<prompt>\nOutput:\n<output>"
                # We need to extract the output part
                if "Output:" in response_text:
                    output_part = response_text.split("Output:")[-1].strip()
                else:
                    output_part = response_text
                
                # Try to find JSON in the output
                json_match = re.search(r'\{[^}]+\}', output_part)
                if json_match:
                    try:
                        parsed = json.loads(json_match.group())
                        # Map query to appropriate values based on content
                        return self._enhance_parsed_response(parsed, output_part)
                    except:
                        pass
                
                # If no JSON found, analyze the query ourselves
                return self._analyze_query_fallback(output_part)
                
        except Exception as e:
            logger.warning(f"Failed to parse Gemma response: {e}")
        
        return {"intent": "product_search", "confidence": 0.7, "alpha": 0.5}
    
    def _enhance_parsed_response(self, parsed: Dict, raw_text: str) -> Dict[str, Any]:
        """Enhance parsed response with proper intent and alpha values"""
        
        # If the model just echoed our example, analyze properly
        raw_lower = raw_text.lower()
        
        # Determine actual intent
        if any(word in raw_lower for word in ["change", "update", "modify", "make it", "double", "triple"]) and any(word in raw_lower for word in ["quantity", "amount", "number"]):
            parsed["intent"] = "update_order"
        elif any(word in raw_lower for word in ["remove", "delete", "take out"]):
            parsed["intent"] = "remove_from_order"
        elif any(word in raw_lower for word in ["add", "put", "throw"]):
            parsed["intent"] = "add_to_order"
        elif any(word in raw_lower for word in ["confirm", "checkout", "place order", "complete"]):
            parsed["intent"] = "confirm_order"
        elif any(word in raw_lower for word in ["show cart", "view cart", "what's in", "list order"]):
            parsed["intent"] = "list_order"
        elif any(word in raw_lower for word in ["deal", "discount", "offer", "promo"]):
            parsed["intent"] = "promotion_query"
        elif parsed.get("intent") not in ["product_search", "add_to_order", "update_order", "remove_from_order", "confirm_order", "list_order", "promotion_query"]:
            parsed["intent"] = "product_search"
        
        # Ensure we have all fields
        return {
            "intent": parsed.get("intent", "product_search"),
            "confidence": parsed.get("confidence", 0.8),
            "alpha": parsed.get("alpha", 0.5)
        }
    
    def _analyze_query_fallback(self, text: str) -> Dict[str, Any]:
        """Analyze query when model doesn't return proper JSON"""
        text_lower = text.lower()
        
        # Determine intent from text
        if any(word in text_lower for word in ["change", "update", "modify", "double", "triple"]) and any(word in text_lower for word in ["quantity", "amount", "number"]):
            intent = "update_order"
            confidence = 0.95
        elif any(word in text_lower for word in ["remove", "delete", "take out"]):
            intent = "remove_from_order"
            confidence = 0.9
        elif any(word in text_lower for word in ["add", "adding"]):
            intent = "add_to_order"
            confidence = 0.9
        elif any(word in text_lower for word in ["confirm", "checkout", "place order", "complete"]):
            intent = "confirm_order"
            confidence = 0.9
        elif any(word in text_lower for word in ["show cart", "view cart", "what's in", "list order"]):
            intent = "list_order"
            confidence = 0.9
        elif any(word in text_lower for word in ["deal", "promo", "discount"]):
            intent = "promotion_query"
            confidence = 0.9
        else:
            intent = "product_search"
            confidence = 0.8
        
        # Estimate alpha based on query complexity
        if any(word in text_lower for word in ["organic", "healthy", "fresh", "natural"]):
            alpha = 0.7
        elif any(word in text_lower for word in ["amul", "tata", "nestle", "britannia"]):
            alpha = 0.3
        else:
            alpha = 0.5
        
        return {
            "intent": intent,
            "confidence": confidence,
            "alpha": alpha
        }
    
    def _fallback_response(self, query: str) -> Dict[str, Any]:
        """Quick pattern-based fallback"""
        query_lower = query.lower()
        
        # Determine intent
        if any(word in query_lower for word in ["add", "put", "throw"]):
            intent = "add_to_order"
        elif any(word in query_lower for word in ["cart", "basket", "order", "checkout"]):
            intent = "list_order"
        elif any(word in query_lower for word in ["promo", "deal", "discount", "offer"]):
            intent = "promotion_query"
        else:
            intent = "product_search"
        
        # Estimate alpha based on query
        word_count = len(query_lower.split())
        has_brand = any(brand in query_lower for brand in ["amul", "tata", "fortune", "nestle", "britannia"])
        
        if has_brand or word_count <= 2:
            alpha = 0.3  # Keyword focused
        elif word_count >= 5 or any(word in query_lower for word in ["organic", "healthy", "fresh"]):
            alpha = 0.7  # Semantic focused
        else:
            alpha = 0.5  # Balanced
        
        return {
            "intent": intent,
            "confidence": 0.6,
            "metadata": {
                "search_alpha": alpha,
                "latency_ms": 0,
                "endpoint": "fallback"
            }
        }
    
    async def _analyze_with_huggingface(self, query: str, user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Use HuggingFace for local development"""
        logger.info(f"HuggingFace: API key available: {bool(self.hf_api_key)}")
        if not self.hf_api_key:
            logger.warning("No HuggingFace API key, using fallback")
            return self._fallback_response(query)
        
        try:
            headers = {"Authorization": f"Bearer {self.hf_api_key}"}
            
            # Same prompt as Gemma with examples
            prompt = f"""<|system|>
You are a grocery shopping assistant. Analyze user queries and classify their intent.
<|user|>
Examples:
"I need milk" -> {{"intent": "product_search", "confidence": 0.9, "alpha": 0.5}}
"add milk to cart" -> {{"intent": "add_to_order", "confidence": 0.95, "alpha": 0.5}}
"change milk quantity to 3" -> {{"intent": "update_order", "confidence": 0.95, "alpha": 0.5}}
"remove milk" -> {{"intent": "remove_from_order", "confidence": 0.9, "alpha": 0.5}}
"checkout" -> {{"intent": "confirm_order", "confidence": 0.95, "alpha": 0.5}}
"show my cart" -> {{"intent": "list_order", "confidence": 0.95, "alpha": 0.5}}

Now analyze: "{query}"
<|assistant|>"""
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "temperature": 0.1,
                    "max_new_tokens": 50,
                    "return_full_text": False
                }
            }
            
            logger.info(f"Calling HuggingFace API with model: {self.hf_model_id}")
            response = await self.client.post(
                f"https://api-inference.huggingface.co/models/{self.hf_model_id}",
                json=payload,
                headers=headers
            )
            logger.info(f"HuggingFace response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result[0]["generated_text"] if isinstance(result, list) else result.get("generated_text", "")
                
                # Try to extract JSON
                json_match = re.search(r'\{[^}]+\}', generated_text)
                if json_match:
                    try:
                        parsed = json.loads(json_match.group())
                        return {
                            "intent": parsed.get("intent", "product_search"),
                            "confidence": parsed.get("confidence", 0.8),
                            "metadata": {
                                "search_alpha": parsed.get("alpha", 0.5),
                                "method": "huggingface"
                            }
                        }
                    except:
                        pass
                
                # If no valid JSON, use fallback
                return self._fallback_response(query)
            else:
                logger.warning(f"HuggingFace API error: {response.status_code}")
                return self._fallback_response(query)
                
        except Exception as e:
            logger.error(f"HuggingFace error: {e}")
            return self._fallback_response(query)

    async def _get_valid_token(self) -> str:
        """Get a valid auth token, using cache when possible"""
        if not self.use_auth:
            return ""
            
        current_time = time.time()
        
        # Check if we have a cached token that's still valid
        if self._token and self._token_expiry and current_time < self._token_expiry:
            return self._token
        
        # Token expired or doesn't exist - refresh it
        logger.info("Refreshing auth token")
        refresh_start = time.time()
        
        if hasattr(self.credentials, 'refresh'):
            self.credentials.refresh(Request())
        
        refresh_time = (time.time() - refresh_start) * 1000
        logger.info(f"Token refreshed in {refresh_time:.0f}ms")
        
        # Cache the token
        self._token = self.credentials.token
        
        # Google tokens typically valid for 3600 seconds (1 hour)
        # We'll cache for 50 minutes to be safe
        self._token_expiry = current_time + 3000  # 50 minutes
        
        return self._token
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# Singleton instance for connection reuse
_optimized_client = None

def get_optimized_client() -> GemmaOptimizedClient:
    """Get singleton client instance"""
    global _optimized_client
    if _optimized_client is None:
        _optimized_client = GemmaOptimizedClient()
    return _optimized_client