"""
Wrapper for GraphitiMemory to work with MemoryRegistry
"""

import logging
from typing import Dict, Any, Optional, List
from src.memory.graphiti_memory import GraphitiMemory
from src.memory.graphiti_memory_spanner import GraphitiMemorySpanner
from src.memory.memory_interfaces import MemoryBackend

logger = logging.getLogger(__name__)


class GraphitiMemoryWrapper:
    """
    Wrapper that creates GraphitiMemory instances per user/session
    and provides the expected interface for the API
    """
    
    def __init__(self, graph_backend: MemoryBackend = MemoryBackend.SPANNER, config: Optional[Dict[str, Any]] = None):
        self.graph_backend = graph_backend
        self.config = config or {}
        self._instances: Dict[str, Any] = {}  # Can be either GraphitiMemory or GraphitiMemorySpanner
        
    async def _get_instance(self, user_id: str, session_id: str):
        """Get or create a GraphitiMemory instance for user/session"""
        key = f"{user_id}:{session_id}"
        
        if key not in self._instances:
            # Use Spanner version if backend is SPANNER
            if self.graph_backend == MemoryBackend.SPANNER:
                instance = GraphitiMemorySpanner(user_id=user_id, session_id=session_id)
            else:
                instance = GraphitiMemory(user_id=user_id, session_id=session_id)
                
            await instance.initialize()
            self._instances[key] = instance
            
        return self._instances[key]
    
    async def process_message(
        self, 
        message: str, 
        role: str = "user",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a message and extract entities/relationships"""
        metadata = metadata or {}
        user_id = metadata.get("user_id", "default")
        session_id = metadata.get("session_id", "default")
        
        instance = await self._get_instance(user_id, session_id)
        return await instance.process_message(message, role, metadata)
    
    async def get_context(self, query: str, **kwargs) -> Dict[str, Any]:
        """Get context for a query"""
        # Extract user_id and session_id from kwargs or use defaults
        user_id = kwargs.get("user_id", "default")
        session_id = kwargs.get("session_id", "default")
        
        instance = await self._get_instance(user_id, session_id)
        return await instance.get_context(query)
    
    async def cleanup(self):
        """Cleanup all instances"""
        for instance in self._instances.values():
            if hasattr(instance, 'close'):
                await instance.close()
        self._instances.clear()
        
    async def process_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process an order and update the knowledge graph"""
        user_id = order_data.get("user_id", "anonymous")
        session_id = order_data.get("session_id", "default")
        
        instance = await self._get_instance(user_id, session_id)
        
        # If the instance has a process_order method, use it
        if hasattr(instance, 'process_order'):
            return await instance.process_order(order_data)
        else:
            # Fallback: process as a message
            order_message = f"Order confirmed with {len(order_data.get('items', []))} items"
            return await instance.process_message(
                message=order_message,
                role="system",
                metadata={"order_data": order_data}
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get stats for monitoring"""
        return {
            "instances": len(self._instances),
            "backend": str(self.graph_backend)
        }
    
    # New convenience class for agent memory patterns
    async def get_or_create_memory(self, user_id: str, session_id: Optional[str] = None):
        """Get or create memory instance"""
        session_id = session_id or "default"
        return await self._get_instance(user_id, session_id)
    
    async def get_user_context(self, user_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get user context from Graphiti memory"""
        memory_manager = await self.get_or_create_memory(user_id, session_id)
        if not memory_manager:
            return {}
            
        context = await memory_manager.get_context("")
        return context
    
    # Agent-specific memory queries
    async def get_routing_patterns(self, user_id: str, query: str) -> Dict[str, Any]:
        """Get routing patterns for supervisor decisions"""
        memory_manager = await self.get_or_create_memory(user_id)
        if not memory_manager:
            return {}
        
        # Get patterns like "grab X" -> order_agent
        context = await memory_manager.get_context(query)
        
        routing_patterns = {
            "common_phrases": {},  # phrase -> agent mapping
            "success_rates": {},   # agent -> success rate
            "time_patterns": {}    # time of day -> agent preference
        }
        
        # Extract routing-specific patterns from context
        if context.get("user_context", {}).get("interaction_history"):
            # Analyze past routings
            # For now, simple pattern matching
            if any(word in query.lower() for word in ["grab", "throw", "toss"]):
                routing_patterns["common_phrases"]["casual_order"] = "order_agent"
                
        return routing_patterns
    
    async def get_search_patterns(self, user_id: str, query: str) -> Dict[str, Any]:
        """Get search refinement patterns"""
        memory_manager = await self.get_or_create_memory(user_id)
        if not memory_manager:
            return {}
            
        context = await memory_manager.get_context(query)
        
        search_patterns = {
            "refinements": {},      # query -> refined query
            "click_patterns": {},   # query -> clicked products
            "ignored_items": [],    # items user never clicks
            "preferred_categories": {}
        }
        
        # Extract search patterns
        if "milk" in query.lower() and context.get("preferences"):
            # Check if user has dairy preferences
            prefs = context.get("preferences", {})
            if "dairy-free" in prefs.get("dietary", []):
                search_patterns["refinements"]["milk"] = "oat milk"
                
        return search_patterns
    
    async def get_order_patterns(self, user_id: str, product_name: str) -> Dict[str, Any]:
        """Get ordering patterns for a product"""
        memory_manager = await self.get_or_create_memory(user_id)
        if not memory_manager:
            return {}
            
        context = await memory_manager.get_context(product_name)
        
        order_patterns = {
            "usual_quantity": 1,
            "purchase_frequency": None,
            "complementary_items": [],
            "last_ordered": None
        }
        
        # Extract from reorder patterns if available
        reorder_patterns = context.get("reorder_patterns", [])
        for pattern in reorder_patterns:
            if pattern.get("product_name", "").lower() == product_name.lower():
                order_patterns["usual_quantity"] = pattern.get("avg_quantity", 1)
                order_patterns["purchase_frequency"] = pattern.get("avg_days_between_orders")
                order_patterns["last_ordered"] = pattern.get("last_ordered")
                break
                
        return order_patterns
    
    async def get_communication_style(self, user_id: str) -> Dict[str, Any]:
        """Get user's preferred communication style"""
        # For now, return defaults
        # In future, learn from interactions
        return {
            "style": "concise",  # concise, detailed, casual, formal
            "format": "list",    # list, paragraph, bullets
            "emoji_preference": False
        }
    
    # Pattern query methods for agents
    
    async def get_learned_preferences(self, user_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get all learned preferences from Graphiti patterns"""
        memory_manager = await self.get_or_create_memory(user_id, session_id)
        if not memory_manager:
            return {}
        
        # Get patterns if the memory manager supports it
        if hasattr(memory_manager, 'get_user_patterns'):
            patterns = await memory_manager.get_user_patterns()
            
            # Extract preferences
            preferences = {
                "brands": [],
                "categories": [],
                "dietary": [],
                "price_sensitivity": {},
                "shopping_behavior": {}
            }
            
            # Process preference patterns
            for pref in patterns.get("preferences", []):
                target = pref.get("target_node_id", "")
                confidence = pref.get("confidence", 0)
                properties = pref.get("properties", {})
                
                if target.startswith("brand:"):
                    preferences["brands"].append({
                        "name": target.replace("brand:", ""),
                        "confidence": confidence,
                        "strength": properties.get("strength", "moderate")
                    })
                elif target.startswith("category:"):
                    preferences["categories"].append({
                        "name": target.replace("category:", ""),
                        "confidence": confidence,
                        "interactions": properties.get("interactions", 0)
                    })
            
            # Process behavior patterns
            for behavior in patterns.get("behavior", []):
                properties = behavior.get("properties", {})
                preferences["shopping_behavior"] = {
                    "frequency": properties.get("frequency", "unknown"),
                    "preferred_day": properties.get("preferred_day", ""),
                    "avg_basket_size": properties.get("avg_basket_size", 0),
                    "avg_basket_value": properties.get("avg_basket_value", 0)
                }
            
            return preferences
        
        return {}
    
    async def get_reorder_predictions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get products due for reorder based on patterns"""
        memory_manager = await self.get_or_create_memory(user_id)
        if not memory_manager:
            return []
        
        if hasattr(memory_manager, 'get_user_patterns'):
            patterns = await memory_manager.get_user_patterns(["REORDERS_EVERY"])
            
            reorder_items = []
            for pattern in patterns.get("reorder", []):
                properties = pattern.get("properties", {})
                if properties.get("due_for_reorder", False):
                    reorder_items.append({
                        "sku": pattern.get("target_node_id", "").replace("product:", ""),
                        "name": properties.get("product_name", ""),
                        "days_since_last": properties.get("days_since_last", 0),
                        "usual_quantity": properties.get("usual_quantity", 1),
                        "confidence": pattern.get("confidence", 0),
                        "pattern_id": pattern.get("edge_id", "")
                    })
            
            # Sort by confidence
            reorder_items.sort(key=lambda x: x["confidence"], reverse=True)
            return reorder_items
        
        return []
    
    async def get_product_associations(self, product_sku: str) -> Dict[str, Any]:
        """Get products associated with a given product"""
        # Try to get from any user's patterns (product associations are global)
        try:
            if self._instances:
                # Use first available instance
                instance = next(iter(self._instances.values()))
                if hasattr(instance, 'get_product_patterns'):
                    patterns = await instance.get_product_patterns(product_sku)
                    
                    associations = {
                        "complementary": [],
                        "substitutes": [],
                        "frequently_bought_together": []
                    }
                    
                    for assoc in patterns.get("associations", []):
                        target = assoc.get("target_node_id", "").replace("product:", "")
                        properties = assoc.get("properties", {})
                        
                        item = {
                            "sku": target,
                            "name": properties.get("name_b", ""),
                            "confidence": assoc.get("confidence", 0),
                            "co_occurrences": properties.get("co_occurrences", 0)
                        }
                        
                        assoc_type = properties.get("association_type", "related")
                        if assoc_type == "complementary":
                            associations["complementary"].append(item)
                        else:
                            associations["frequently_bought_together"].append(item)
                    
                    return associations
        except Exception as e:
            logger.error(f"Failed to get product associations: {e}")
        
        return {"complementary": [], "substitutes": [], "frequently_bought_together": []}