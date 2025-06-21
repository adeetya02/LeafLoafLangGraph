from typing import Dict, Any, List, Optional
from src.agents.base import BaseAgent
from src.models.state import SearchState, Message
from src.tools.tool_executor import tool_executor
import asyncio
import json

class ProductSearchReactAgent(BaseAgent):
    """Autonomous Product Search agent that can call multiple tools in parallel"""
    
    def __init__(self):
        super().__init__("product_search")
        self.tool_executor = tool_executor
        self.max_iterations = 3
        
    async def _run(self, state: SearchState) -> SearchState:
        """Autonomous search with ability to call multiple tools"""
        self.logger.info(f"ProductSearch received state: should_search={state.get('should_search')}, next_action={state.get('next_action')}")
        
        # Log what routing we got
        routing = state.get("routing_decision")
        self.logger.info(f"Product Search - routing_decision: '{routing}'")
        # Check if we should run- the supervisor sets routing decision
        if routing != "product_search":
            self.logger.info(f"Not routed to product search (routing={routing}), skipping")
            return state
        
        # Log what we're about to search
        search_params = state.get("search_params", {})
        query = search_params.get("original_query", state["query"])
        self.logger.info(f"Executing search for: {query}")
        
        search_params = state.get("search_params", {})
        query = search_params.get("original_query", state["query"])
        intent = state.get("intent", "general_search")
        iterations = 0
        
        state["messages"].append({
            "role": "assistant",
            "content": f"Starting product search for: {query}",
            "tool_calls": None,
            "tool_call_id": None
        })
        
        while iterations < self.max_iterations:
            iterations += 1
            
            # REASON: What tools should we call?
            tool_plan = self._plan_tool_calls(state, query, intent, iterations)
            state["reasoning"].append(f"Search iteration {iterations}: {tool_plan['reasoning']}")
            
            if not tool_plan["tool_calls"]:
                break
            
            # ACT: Execute tools in parallel
            state["messages"].append({
                "role": "assistant",
                "content": tool_plan["reasoning"],
                "tool_calls": tool_plan["tool_calls"],
                "tool_call_id": None
            })
            
            # Execute all tool calls in parallel
            results = await self._execute_parallel_tools(tool_plan["tool_calls"])
            
            # OBSERVE: Process results
            for result in results:
                state["messages"].append({
                    "role": "tool",
                    "content": json.dumps(result["result"]),
                    "tool_calls": None,
                    "tool_call_id": result["tool_call_id"]
                })
                state["completed_tool_calls"].append(result)
            
            # Analyze results and decide if we need more iterations
            analysis = self._analyze_results(results, query, intent)
            state["reasoning"].append(analysis["reasoning"])
            
            if analysis["sufficient"]:
                # Process and store final results
                state["search_results"] = self._merge_results(results)
                self.logger.info(f"Set search_results in state: {len(state['search_results'])} products")
                state["search_metadata"] = {
                    "iterations": iterations,
                    "tools_called": len(state["completed_tool_calls"]),
                    "final_count": len(state["search_results"])
                }
                break
            
            # Need another iteration with different strategy
            state["search_strategy"] = analysis["next_strategy"]
        self.logger.info(f"Product Search returning state with {len(state.get('search_results', []))} products")
        return state
    
    def _plan_tool_calls(self, state: SearchState, query: str, intent: str, iteration: int) -> Dict:
        """Plan which tools to call based on current state"""
        tool_calls = []
        existing_results = state.get("search_results", [])
    
        if iteration == 1:
            # First iteration - cast a wide net
            if intent == "specific_product":
                # Get alpha from state (calculated in main.py)
                alpha = state.get("alpha_value", 0.5)
                
                tool_calls = [{
                    "id": f"call_search_{iteration}",
                    "name": "product_search",
                    "args": {
                        "query": query, 
                        "limit": 20,
                        "alpha": alpha
                    }
                }]
                reasoning = f"Performing single search with alpha={alpha}"
                
            elif intent == "brand_search":
                brand = self._extract_brand(query)
                tool_calls = [{
                    "id": f"call_brand_products_{iteration}",
                    "name": "product_search",
                    "args": {"query": brand, "limit": 20}
                }]
                reasoning = f"Searching for all products from brand: {brand}"
                
            else:  # general search
                tool_calls = [{
                    "id": f"call_general_search_{iteration}",
                    "name": "product_search",
                    "args": {"query": query, "limit": 15}
                }]
                reasoning = "Performing general product search"
                
        elif iteration == 2:
            # Second iteration - refine or expand
            if len(existing_results) < 3:
                # Too few results - broaden search
                broad_query = self._broaden_query(query)
                tool_calls = [{
                    "id": f"call_broad_search_{iteration}",
                    "name": "product_search",
                    "args": {"query": broad_query, "limit": 10}
                }]
                reasoning = f"Too few results, broadening search to: {broad_query}"
                
            elif len(existing_results) > 20:
                # Too many results - get details on top items
                top_products = existing_results[:5]
                tool_calls = [
                    {
                        "id": f"call_details_{i}_{iteration}",
                        "name": "get_product_details",
                        "args": {"product_id": product.get("productId", "")}
                    }
                    for i, product in enumerate(top_products)
                    if product.get("productId")
                ]
                reasoning = "Getting detailed information for top 5 products"
        
        return {
            "tool_calls": tool_calls,
            "reasoning": reasoning
        }
    # There is an indentation error here. The $PLACEHOLDER$ is outside the class.
    # You should remove the blank line before 'async def _execute_parallel_tools...' so that all methods are inside the ProductSearchReactAgent class.
    # No 'return' statement is outside a function, so that error should not occur in this file.
    # If you still see "return can be used only within a function", check for stray 'return' statements outside functions elsewhere in your codebase.    
    async def _execute_parallel_tools(self, tool_calls: List[Dict]) -> List[Dict]:
        """Execute multiple tool calls in parallel"""
        tasks = []
        for tool_call in tool_calls:
            task = self.tool_executor.execute_tool_call(tool_call)
            tasks.append(task)
        
        # Execute all tools in parallel
        results = await asyncio.gather(*tasks)
        return results
    
    def _analyze_results(self, results: List[Dict], query: str, intent: str) -> Dict:
        """Analyze tool results and decide next steps"""
        total_products = 0
        successful_calls = 0
        
        for result in results:
            if result.get("result", {}).get("success"):
                successful_calls += 1
                products = result["result"].get("products", [])
                total_products += len(products)
        
        # Determine if we have sufficient results
        sufficient = False
        next_strategy = None
        
        if intent == "specific_product" and total_products >= 1:
            sufficient = True
            reasoning = f"Found {total_products} specific products - sufficient for user needs"
        elif intent == "brand_search" and total_products >= 5:
            sufficient = True
            reasoning = f"Found {total_products} products from requested brand"
        elif total_products >= 10:
            sufficient = True
            reasoning = f"Found {total_products} products - good variety for user"
        elif total_products == 0:
            reasoning = "No products found - need to try different search strategy"
            next_strategy = "broaden"
        else:
            reasoning = f"Only found {total_products} products - should search more broadly"
            next_strategy = "broaden"
            
        return {
            "sufficient": sufficient,
            "reasoning": reasoning,
            "next_strategy": next_strategy,
            "total_products": total_products
        }
    
    def _merge_results(self, results: List[Dict]) -> List[Dict]:
        """Merge results from multiple tool calls, removing duplicates"""
        all_products = []
        seen_ids = set()
        self.logger.info(f"Merging {len(results)} tool results")
        for result in results:
            if result.get("result", {}).get("success"):
                products = result["result"].get("products", [])
                for product in products:
                    product_id = product.get("sku", "")
                    if product_id and product_id not in seen_ids:
                        seen_ids.add(product_id)
                        all_products.append(product)
        
        return all_products
    
    def _extract_category(self, query: str) -> str:
        """Extract category from query"""
        categories = ["vegetables", "fruits", "dairy", "meat", "seafood", "bakery"]
        query_lower = query.lower()
        for category in categories:
            if category in query_lower:
                return category
        return query  # fallback to original
    
    def _extract_brand(self, query: str) -> str:
        """Extract brand from query"""
        # Remove Baldor - it's the supplier, not a product brand
        # In production, we'd have a list of actual product brands
        # For now, just return the query
        query_lower = query.lower()
        
        # Remove common non-brand words
        non_brand_words = ["organic", "fresh", "the", "a", "an"]
        words = query_lower.split()
        potential_brand = [w for w in words if w not in non_brand_words]
        
        return " ".join(potential_brand) if potential_brand else query
    
    def _broaden_query(self, query: str) -> str:
        """Broaden a query by removing specific terms"""
        # Remove specific terms to broaden
        broad_terms = query.lower()
        specific_words = ["organic", "fresh", "1lb", "pound", "specific"]
        for word in specific_words:
            broad_terms = broad_terms.replace(word, "").strip()
        return broad_terms if broad_terms else query