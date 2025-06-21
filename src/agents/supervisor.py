from typing import Dict, Any, List, Optional
from src.agents.base import BaseAgent
from src.models.state import SearchState, Message
from src.tools.tool_executor import tool_executor
import json

class SupervisorReactAgent(BaseAgent):
    """React Supervisor agent that reasons about queries and decides on actions"""
    
    def __init__(self):
        super().__init__("supervisor")
        self.tool_executor = tool_executor
        self.max_iterations = 3
        
    async def _run(self, state: SearchState) -> SearchState:
        """React loop: Reason, Act, Observe"""
        query = state["query"]
        iterations = 0
        
        # Initial reasoning
        state["messages"].append({
            "role": "assistant",
            "content": f"Analyzing query: '{query}'",
            "tool_calls": None,
            "tool_call_id": None
        })
        
        while iterations < self.max_iterations and state.get("should_continue", True):
            iterations += 1
            
            # REASON: Analyze what we need to do
            reasoning = self._reason(state)
            state["reasoning"].append(reasoning)
            
            # Decide next action
            next_action = self._decide_action(state, reasoning)
            state["next_action"] = next_action
            
            if next_action == "search":
                # ACT: Create tool call for product search
                tool_call = self._create_search_tool_call(query)
                state["pending_tool_calls"].append(tool_call)
                
                # Add assistant message with tool call
                state["messages"].append({
                    "role": "assistant",
                    "content": f"Searching for products matching: {query}",
                    "tool_calls": [tool_call],
                    "tool_call_id": None
                })
                
                # Execute tool
                results = await self.tool_executor.execute_tool_calls([tool_call])
                
                # OBSERVE: Add tool results to messages
                for result in results:
                    state["messages"].append({
                        "role": "tool",
                        "content": json.dumps(result["result"]),
                        "tool_calls": None,
                        "tool_call_id": result["tool_call_id"]
                    })
                    state["completed_tool_calls"].append(result)
                
                # Check if we have good results
                if self._has_good_results(results):
                    state["should_continue"] = False
                    state["search_results"] = results[0]["result"].get("products", [])
                    
            elif next_action == "clarify":
                # Need more information from user
                state["messages"].append({
                    "role": "assistant", 
                    "content": "I need more information to help you better. Could you be more specific about what you're looking for?",
                    "tool_calls": None,
                    "tool_call_id": None
                })
                state["should_continue"] = False
                
            else:  # done
                state["should_continue"] = False
        
        return state
    
    def _reason(self, state: SearchState) -> str:
        """Reasoning step - analyze current state"""
        query = state["query"].lower()
        has_results = len(state.get("search_results", [])) > 0
        
        if not has_results:
            if self._is_specific_query(query):
                return "Query is specific, should search for exact products"
            elif self._is_browse_query(query):
                return "Query is exploratory, should search broadly"
            else:
                return "Query is unclear, might need clarification"
        else:
            return "Already have search results, should compile response"
    
    def _decide_action(self, state: SearchState, reasoning: str) -> str:
        """Decide what action to take based on reasoning"""
        if "should search" in reasoning:
            return "search"
        elif "need clarification" in reasoning:
            return "clarify"
        else:
            return "done"
    
    def _is_specific_query(self, query: str) -> bool:
        """Check if query is asking for specific products"""
        specific_indicators = ["organic", "fresh", "pound", "lb", "oz", "brand"]
        return any(indicator in query for indicator in specific_indicators)
    
    def _is_browse_query(self, query: str) -> bool:
        """Check if query is exploratory"""
        browse_indicators = ["dinner", "meal", "healthy", "snacks", "ideas"]
        return any(indicator in query for indicator in browse_indicators)
    
    def _create_search_tool_call(self, query: str) -> Dict[str, Any]:
        """Create a tool call for product search"""
        return {
            "id": f"call_{self.name}_{len(state.get('pending_tool_calls', []))}",
            "name": "product_search",
            "args": {
                "query": query,
                "limit": 10
            }
        }
    
    def _has_good_results(self, results: List[Dict]) -> bool:
        """Check if we have good search results"""
        if not results:
            return False
        
        result = results[0]
        if result.get("error"):
            return False
            
        products = result.get("result", {}).get("products", [])
        return len(products) > 0