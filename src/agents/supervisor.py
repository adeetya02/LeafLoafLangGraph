from typing import Dict, Any, List, Optional
from src.agents.base import BaseAgent
from src.models.state import SearchState, Message

class SupervisorReactAgent(BaseAgent):
    """Autonomous Supervisor that routes to other agents without calling tools"""
    
    def __init__(self):
        super().__init__("supervisor")
        self.max_iterations = 2
        
    async def _run(self, state: SearchState) -> SearchState:
        """Analyze intent and route to appropriate agents"""
        query = state["query"]
        
        # Add initial analysis message
        state["messages"].append({
            "role": "assistant",
            "content": f"Analyzing request: '{query}'",
            "tool_calls": None,
            "tool_call_id": None
        })
        
        # REASON: Analyze the query intent
        intent = self._analyze_intent(query)
        confidence = self._calculate_confidence(query, intent)
        
        state["reasoning"].append(
            f"Supervisor: Classified as '{intent}' with {confidence:.2f} confidence"
        )
        
        # DECIDE: Which agent should handle this?
        routing_decision = self._decide_routing(intent, confidence)
        
        # Update state with decisions
        state["intent"] = intent
        state["confidence"] = confidence
        state["routing_decision"] = routing_decision
        state["next_action"] = routing_decision  # Tell next agent what to do
        
        # Add routing message
        state["messages"].append({
            "role": "assistant",
            "content": f"Routing to {routing_decision} agent for: {intent}",
            "tool_calls": None,
            "tool_call_id": None
        })
        
        # Set flags for downstream agents
        if routing_decision == "product_search":
            state["should_search"] = True
            state["search_params"] = self._create_search_params(query, intent)
        elif routing_decision == "help":
            state["should_help"] = True
        elif routing_decision == "clarify":
            state["needs_clarification"] = True
            
        self.logger.info(
            "Routing decision made",
            intent=intent,
            confidence=confidence,
            routing=routing_decision
        )
        
        return state
    
    def _analyze_intent(self, query: str) -> str:
        """Analyze query intent without using tools"""
        query_lower = query.lower()
        
        # Check for food/product queries first
        food_terms = ["potato", "tomato", "pepper", "milk", "bread", "fruit", "vegetable"]
        if any(term in query_lower for term in food_terms):
            return "specific_product"
        # Product-specific queries
        if any(word in query_lower for word in ["organic", "fresh", "price", "cost", "$"]):
            return "specific_product"
        
        # Brand queries
        if any(word in query_lower for word in ["brand", "from"]):
            return "brand_search"
        
        # Category browsing
        if any(word in query_lower for word in ["vegetables", "fruits", "dairy", "meat"]):
            return "category_browse"
        
        # Meal planning
        if any(word in query_lower for word in ["dinner", "lunch", "meal", "recipe", "cook"]):
            return "meal_planning"
        
        # General browsing
        if any(word in query_lower for word in ["healthy", "snacks", "ideas", "suggestions"]):
            return "discovery"
        
        # Help requests
        if any(word in query_lower for word in ["help", "how", "what can"]):
            return "help_request"
        
        # Unclear
        if len(query_lower.split()) < 2:
            return "unclear"
            
        return "general_search"
    
    def _calculate_confidence(self, query: str, intent: str) -> float:
        """Calculate confidence in the intent classification"""
        base_confidence = 0.6
        
        # Longer, more specific queries get higher confidence
        word_count = len(query.split())
        if word_count > 4:
            base_confidence += 0.2
        elif word_count > 2:
            base_confidence += 0.1
            
        # Specific intents get higher confidence
        if intent in ["specific_product", "brand_search"]:
            base_confidence += 0.2
        elif intent == "unclear":
            base_confidence -= 0.2
            
        return min(max(base_confidence, 0.2), 0.95)
    
    def _decide_routing(self, intent: str, confidence: float) -> str:
        """Decide which agent should handle the request"""
        
        # Low confidence - need clarification
        if confidence < 0.4:
            return "clarify"
        
        # Route based on intent
        routing_map = {
            "specific_product": "product_search",
            "brand_search": "product_search",
            "category_browse": "product_search",
            "meal_planning": "product_search",  # For now, will add meal agent later
            "discovery": "product_search",
            "general_search": "product_search",
            "help_request": "help",
            "unclear": "clarify"
        }
        
        return routing_map.get(intent, "product_search")
    
    def _create_search_params(self, query: str, intent: str) -> Dict[str, Any]:
        """Create parameters for the search agent"""
        params = {
            "original_query": query,
            "intent": intent,
            "search_type": "broad"  # default
        }
        
        # Adjust search type based on intent
        if intent in ["specific_product", "brand_search"]:
            params["search_type"] = "specific"
            params["limit"] = 5
        elif intent in ["category_browse", "discovery"]:
            params["search_type"] = "broad"
            params["limit"] = 20
        else:
            params["limit"] = 10
            
        return params