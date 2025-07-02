"""
In-memory graph implementation for testing

This provides a lightweight graph memory implementation
that doesn't require external dependencies.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from src.memory.memory_interfaces import GraphMemoryProtocol
from src.memory.graphiti_memory import EntityExtractor, Entity, Relationship

logger = logging.getLogger(__name__)


class InMemoryGraphMemory(GraphMemoryProtocol):
    """
    In-memory implementation of graph memory for testing
    
    This provides full functionality without external dependencies,
    making it ideal for unit tests and local development.
    """
    
    def __init__(self, user_id: str, session_id: str):
        self.user_id = user_id
        self.session_id = session_id
        self.extractor = EntityExtractor()
        
        # In-memory storage
        self.users: Dict[str, Dict[str, Any]] = {}
        self.products: Dict[str, Dict[str, Any]] = {}
        self.orders: Dict[str, Dict[str, Any]] = {}
        self.episodes: List[Dict[str, Any]] = []
        self.relationships: List[Dict[str, Any]] = []
        
        # Caches
        self._entity_cache: Dict[str, Entity] = {}
        self._relationship_cache: List[Relationship] = []
        
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize in-memory storage"""
        if not self._initialized:
            # Create user
            self.users[self.user_id] = {
                "user_id": self.user_id,
                "email": f"{self.user_id}@leafloaf.com",
                "name": f"User {self.user_id}",
                "created_at": datetime.now().isoformat(),
                "preferences": {},
                "shopping_pattern": "regular"
            }
            
            self._initialized = True
            logger.info(f"InMemoryGraphMemory initialized for user {self.user_id}")
    
    async def process_message(
        self, 
        message: str, 
        role: str = "human",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a message and extract entities/relationships"""
        metadata = metadata or {}
        
        # Extract entities and relationships
        entities = self.extractor.extract_entities(message, metadata)
        relationships = self.extractor.extract_relationships(entities, message, metadata)
        
        # Cache entities
        for entity in entities:
            cache_key = f"{entity.type.value}:{entity.value}"
            self._entity_cache[cache_key] = entity
        
        self._relationship_cache.extend(relationships)
        
        # Store episode
        episode = {
            "episode_id": f"ep_{len(self.episodes)}",
            "user_id": self.user_id,
            "session_id": self.session_id,
            "content": message,
            "role": role,
            "entities": [e.to_dict() for e in entities],
            "relationships": [r.to_dict() for r in relationships],
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata
        }
        self.episodes.append(episode)
        
        return {
            "entities": [e.to_dict() for e in entities],
            "relationships": [r.to_dict() for r in relationships],
            "entity_count": len(entities),
            "relationship_count": len(relationships)
        }
    
    async def get_context(self, query: str) -> Dict[str, Any]:
        """Get relevant context for a query"""
        # Extract entities from query
        query_entities = self.extractor.extract_entities(query)
        
        # Find relevant episodes
        relevant_episodes = []
        for episode in self.episodes[-10:]:  # Last 10 episodes
            if any(
                entity["value"].lower() in episode["content"].lower()
                for entity in episode["entities"]
            ):
                relevant_episodes.append(episode)
        
        # Get reorder patterns
        reorder_patterns = await self._get_reorder_patterns()
        
        # Get user patterns
        user_patterns = await self.get_user_patterns(self.user_id)
        
        return {
            "user_context": self.users.get(self.user_id, {}),
            "reorder_patterns": reorder_patterns,
            "session_context": {
                "recent_episodes": relevant_episodes[-5:],
                "query_entities": [e.to_dict() for e in query_entities]
            },
            "query_entities": [e.to_dict() for e in query_entities],
            "cached_entities": list(self._entity_cache.keys()),
            "user_patterns": user_patterns
        }
    
    async def get_user_patterns(self, user_id: str) -> Dict[str, Any]:
        """Get user behavior patterns"""
        # Analyze orders to find patterns
        user_orders = [
            order for order in self.orders.values()
            if order.get("user_id") == user_id
        ]
        
        # Calculate patterns
        patterns = {
            "total_orders": len(user_orders),
            "shopping_frequency": "weekly" if len(user_orders) > 4 else "monthly",
            "average_order_value": 0.0,
            "favorite_products": [],
            "preferred_categories": []
        }
        
        if user_orders:
            # Calculate average order value
            total_value = sum(order.get("total_amount", 0) for order in user_orders)
            patterns["average_order_value"] = total_value / len(user_orders)
            
            # Find frequently ordered products
            product_counts = {}
            for order in user_orders:
                for item in order.get("items", []):
                    sku = item.get("sku", "")
                    if sku:
                        product_counts[sku] = product_counts.get(sku, 0) + 1
            
            # Top 5 products
            if product_counts:
                top_products = sorted(
                    product_counts.items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )[:5]
                patterns["favorite_products"] = [
                    {"sku": sku, "count": count}
                    for sku, count in top_products
                ]
        
        return patterns
    
    async def add_order(self, order_data: Dict[str, Any]) -> str:
        """Add an order to memory"""
        order_id = order_data.get("order_id", f"order_{len(self.orders)}")
        order_data["order_id"] = order_id
        order_data["user_id"] = self.user_id
        order_data["timestamp"] = order_data.get("timestamp", datetime.now().isoformat())
        
        # Store order
        self.orders[order_id] = order_data
        
        # Update product relationships
        items = order_data.get("items", [])
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                rel = {
                    "product1": items[i]["sku"],
                    "product2": items[j]["sku"],
                    "relationship": "bought_together",
                    "order_id": order_id
                }
                self.relationships.append(rel)
        
        # Process as message for entity extraction
        order_text = f"Order {order_id}: "
        for item in items:
            order_text += f"{item['quantity']} {item.get('name', 'item')}, "
        
        await self.process_message(
            order_text,
            role="system",
            metadata={"order_id": order_id, "event": "order_placed"}
        )
        
        return order_id
    
    async def _get_reorder_patterns(self) -> List[Dict[str, Any]]:
        """Get reorder patterns from order history"""
        patterns = []
        
        # Count product occurrences across orders
        product_orders = {}
        for order in self.orders.values():
            if order.get("user_id") == self.user_id:
                for item in order.get("items", []):
                    sku = item.get("sku", "")
                    if sku:
                        if sku not in product_orders:
                            product_orders[sku] = []
                        product_orders[sku].append({
                            "order_id": order["order_id"],
                            "timestamp": order.get("timestamp", ""),
                            "quantity": item.get("quantity", 0)
                        })
        
        # Find products ordered multiple times
        for sku, orders in product_orders.items():
            if len(orders) >= 2:
                patterns.append({
                    "sku": sku,
                    "product_name": f"Product {sku}",  # Would be from product DB
                    "order_count": len(orders),
                    "last_ordered": max(o["timestamp"] for o in orders),
                    "average_quantity": sum(o["quantity"] for o in orders) / len(orders)
                })
        
        # Sort by order count
        patterns.sort(key=lambda x: x["order_count"], reverse=True)
        
        return patterns
    
    async def close(self) -> None:
        """Clean up resources"""
        logger.info(f"Closing InMemoryGraphMemory for user {self.user_id}")
        self._entity_cache.clear()
        self._relationship_cache.clear()
        # Keep data in memory for potential reuse