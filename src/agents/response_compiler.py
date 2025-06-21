from typing import Dict, Any, List
from src.agents.base import BaseAgent
from src.models.state import SearchState
import json

class ResponseCompilerAgent(BaseAgent):
    """Agent that compiles final response from search results"""
    
    def __init__(self):
        super().__init__("response_compiler")
        
    async def _run(self, state: SearchState) -> SearchState:
        """Compile final response from all agent outputs"""
        self.logger.info(f"Response Compiler received state with {len(state.get('search_results', []))} products")    
        # Get search results
        products = state.get("search_results", [])
        search_metadata = state.get("search_metadata", {})
        
        # Get execution metadata
        agent_timings = state.get("agent_timings", {})
        reasoning_steps = state.get("reasoning", [])
        
        # Build final response
        final_response = {
            "success": len(products) > 0,
            "query": state["query"],
            "products": self._format_products(products),
            "metadata": {
                "total_count": len(products),
                "categories": search_metadata.get("categories", []),
                "brands": search_metadata.get("brands", []),
                "search_config": search_metadata.get("search_config", {})
            },
            "execution": {
                "total_time_ms": sum(agent_timings.values()),
                "agent_timings": agent_timings,
                "reasoning_steps": reasoning_steps,
                "agents_run": [agent for agent, status in state["agent_status"].items() 
                             if status == "completed"]
            },
            "langsmith_trace_id": state.get("trace_id")
        }
        
        # Add helpful message
        if len(products) == 0:
            final_response["message"] = "No products found. Try broadening your search."
        elif len(products) == 1:
            final_response["message"] = "Found 1 product matching your search."
        else:
            final_response["message"] = f"Found {len(products)} products matching your search."
        
        state["final_response"] = final_response
        
        # Log summary
        self.logger.info(
            "Response compiled",
            products_found=len(products),
            total_time_ms=final_response["execution"]["total_time_ms"]
        )
        
        return state
    
    def _format_products(self, products: List[Dict]) -> List[Dict]:
        """Format products for response"""
        formatted_products = []
        
        for product in products[:20]:  # Limit to 20 products
            formatted_product = {
                "id": product.get("productId", ""),
                "name": product.get("name", ""),
                "description": product.get("description", ""),
                "brand": product.get("brand", ""),
                "category": product.get("category", ""),
                "size": product.get("size", ""),
                "unit": product.get("unit", "")
            }
            
            # Remove empty fields
            formatted_product = {k: v for k, v in formatted_product.items() if v}
            formatted_products.append(formatted_product)
        
        return formatted_products
    
    async def _fallback(self, state: SearchState, error: Exception) -> SearchState:
        """Fallback response compilation"""
        state["final_response"] = {
            "success": False,
            "error": f"Failed to compile response: {str(error)}",
            "query": state.get("query", ""),
            "products": [],
            "metadata": {},
            "execution": {
                "error": str(error),
                "agent_timings": state.get("agent_timings", {})
            }
        }
        return state