"""
Production Gemma 2 9B Client with Technical Transparency
Uses the deployed Gemma 2 9B endpoint for intent/context analysis
"""

import os
import json
import time
import asyncio
import re
from typing import Dict, Optional, Any, List
import httpx
from google.auth.transport.requests import Request
import google.auth
import structlog
from dataclasses import dataclass
from datetime import datetime

logger = structlog.get_logger()

@dataclass
class AgentFlowEvent:
    """Event for real-time agent flow tracking"""
    timestamp: str
    agent: str
    action: str
    details: Dict[str, Any]
    latency_ms: float
    
class GemmaProductionClient:
    """Production client using deployed Gemma 2 9B endpoint with full transparency"""
    
    def __init__(self, flow_callback=None):
        self.project_id = os.getenv("GCP_PROJECT_ID", "leafloafai")
        self.project_number = "32905605817"
        self.location = os.getenv("GCP_LOCATION", "us-central1")
        self.endpoint_id = "1487855836171599872"  # Gemma 2 9B endpoint
        self.endpoint_domain = f"{self.endpoint_id}.{self.location}-{self.project_number}.prediction.vertexai.goog"
        
        # Build URL
        self.url = f"https://{self.endpoint_domain}/v1/projects/{self.project_number}/locations/{self.location}/endpoints/{self.endpoint_id}:predict"
        
        # Flow tracking callback
        self.flow_callback = flow_callback
        
        # Get credentials
        self.use_auth = False
        try:
            if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                self.credentials, _ = google.auth.default()
                self.use_auth = True
            elif os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token"):
                # Running in Cloud Run
                self.credentials, _ = google.auth.default()
                self.use_auth = True
        except Exception as e:
            logger.warning(f"Google auth not available: {e}")
            self.credentials = None
            
        logger.info(f"GemmaProductionClient initialized with Gemma 2 9B endpoint")
        
    async def _emit_flow_event(self, action: str, details: Dict[str, Any], latency_ms: float):
        """Emit agent flow event for real-time tracking"""
        if self.flow_callback:
            event = AgentFlowEvent(
                timestamp=datetime.now().isoformat(),
                agent="Supervisor (Gemma 2 9B)",
                action=action,
                details=details,
                latency_ms=latency_ms
            )
            await self.flow_callback(event)
    
    async def analyze_query(self, query: str, user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Analyze query for intent, context, and search alpha with full transparency"""
        
        start_time = time.time()
        
        # Build optimized prompt for Gemma 2 9B
        prompt = self._build_gemma_prompt(query, user_context)
        
        try:
            # Prepare request
            request_data = {
                "instances": [{
                    "prompt": prompt,
                    "temperature": 0.1,
                    "max_tokens": 150,
                    "top_p": 0.9,
                    "top_k": 10
                }]
            }
            
            # Get auth token if available
            headers = {"Content-Type": "application/json"}
            if self.use_auth and self.credentials:
                self.credentials.refresh(Request())
                headers["Authorization"] = f"Bearer {self.credentials.token}"
            
            # Make request
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.url,
                    json=request_data,
                    headers=headers
                )
                
                latency = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Extract the generated text
                    if "predictions" in result and len(result["predictions"]) > 0:
                        generated_text = result["predictions"][0].get("content", "")
                        
                        # Parse the analysis
                        analysis = self._parse_gemma_response(generated_text)
                        
                        # Emit flow event
                        await self._emit_flow_event(
                            "query_analysis",
                            {
                                "query": query,
                                "intent": analysis["intent"],
                                "confidence": analysis["confidence"],
                                "alpha": analysis["search_alpha"],
                                "model": "Gemma 2 9B",
                                "endpoint": self.endpoint_id
                            },
                            latency
                        )
                        
                        logger.info(f"Gemma 2 9B analysis: intent={analysis['intent']}, alpha={analysis['search_alpha']}, latency={latency:.0f}ms")
                        
                        return {
                            "intent": analysis["intent"],
                            "confidence": analysis["confidence"],
                            "entities": analysis.get("entities", []),
                            "metadata": {
                                "search_alpha": analysis["search_alpha"],
                                "context": analysis.get("context", {}),
                                "latency_ms": latency,
                                "model": "Gemma 2 9B",
                                "endpoint_id": self.endpoint_id
                            }
                        }
                    else:
                        logger.warning("No predictions in Gemma response")
                        return self._fallback_response(query)
                else:
                    logger.error(f"Gemma endpoint returned {response.status_code}")
                    return self._fallback_response(query)
                    
        except Exception as e:
            logger.error(f"Gemma 2 9B error: {e}")
            latency = (time.time() - start_time) * 1000
            
            # Emit error event
            await self._emit_flow_event(
                "query_analysis_error",
                {"query": query, "error": str(e)},
                latency
            )
            
            return self._fallback_response(query)
    
    def _build_gemma_prompt(self, query: str, user_context: Optional[Dict]) -> str:
        """Build optimized prompt for Gemma 2 9B"""
        
        context_str = ""
        if user_context:
            if user_context.get("cart_items"):
                context_str = f"\nCurrent cart: {', '.join(user_context['cart_items'])}"
            if user_context.get("previous_query"):
                context_str += f"\nPrevious query: {user_context['previous_query']}"
        
        prompt = f"""You are a grocery shopping assistant. Analyze this query and provide a JSON response.

Query: "{query}"{context_str}

Analyze and return ONLY valid JSON with:
1. intent: One of [product_search, add_to_order, update_order, remove_from_order, confirm_order, list_order, my_usual, reorder, unclear]
2. confidence: 0.0 to 1.0
3. entities: List of products/items mentioned
4. search_alpha: 0.0 to 1.0 for search strategy
   - 0.0-0.3: Specific product/brand search
   - 0.3-0.5: Product category search
   - 0.5-0.7: General category search
   - 0.7-1.0: Exploratory/idea search

Examples:
- "Oatly oat milk" → intent: "product_search", search_alpha: 0.2
- "add 2 gallons of milk" → intent: "add_to_order", entities: ["milk"], search_alpha: 0.3
- "breakfast ideas" → intent: "product_search", search_alpha: 0.8

JSON Response:"""
        
        return prompt
    
    def _parse_gemma_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Gemma 2 9B response"""
        try:
            # Find JSON in response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                # Ensure all required fields
                return {
                    "intent": result.get("intent", "product_search"),
                    "confidence": float(result.get("confidence", 0.8)),
                    "entities": result.get("entities", []),
                    "search_alpha": float(result.get("search_alpha", 0.5)),
                    "context": result.get("context", {})
                }
        except Exception as e:
            logger.warning(f"Failed to parse Gemma response: {e}")
        
        # Fallback parsing
        return self._extract_from_text(response_text)
    
    def _extract_from_text(self, text: str) -> Dict[str, Any]:
        """Extract information from non-JSON response"""
        intent = "product_search"
        alpha = 0.5
        
        # Simple pattern matching as fallback
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["add", "put", "want"]):
            intent = "add_to_order"
            alpha = 0.3
        elif any(word in text_lower for word in ["remove", "delete", "take out"]):
            intent = "remove_from_order"
            alpha = 0.3
        elif any(word in text_lower for word in ["confirm", "checkout", "done"]):
            intent = "confirm_order"
            alpha = 0.5
        elif "usual" in text_lower:
            intent = "my_usual"
            alpha = 0.4
        
        # Extract alpha if mentioned
        alpha_match = re.search(r'(?:alpha|α).*?(\d+\.?\d*)', text_lower)
        if alpha_match:
            try:
                alpha = float(alpha_match.group(1))
            except:
                pass
        
        return {
            "intent": intent,
            "confidence": 0.7,
            "entities": [],
            "search_alpha": alpha
        }
    
    def _fallback_response(self, query: str) -> Dict[str, Any]:
        """Fallback response when Gemma is unavailable"""
        # Simple keyword-based intent detection
        query_lower = query.lower()
        
        intent = "product_search"
        alpha = 0.5
        
        if any(word in query_lower for word in ["add", "put", "want", "need"]):
            intent = "add_to_order"
            alpha = 0.3
        elif any(word in query_lower for word in ["remove", "delete"]):
            intent = "remove_from_order"
            alpha = 0.3
        elif any(word in query_lower for word in ["my usual", "regular"]):
            intent = "my_usual"
            alpha = 0.4
        elif any(word in query_lower for word in ["confirm", "checkout"]):
            intent = "confirm_order"
            alpha = 0.5
        
        return {
            "intent": intent,
            "confidence": 0.6,
            "entities": [],
            "metadata": {
                "search_alpha": alpha,
                "latency_ms": 5,
                "model": "fallback",
                "reason": "Gemma unavailable"
            }
        }