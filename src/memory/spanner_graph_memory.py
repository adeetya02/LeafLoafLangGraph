"""
Spanner-based graph memory implementation

This adapts the SpannerGraphClient to work with the GraphMemoryProtocol,
providing a unified interface for graph memory operations.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.memory.memory_interfaces import GraphMemoryProtocol
from src.integrations.spanner_graph_client import SpannerGraphClient
from src.memory.graphiti_memory import EntityExtractor, Entity, Relationship

logger = logging.getLogger(__name__)


class SpannerGraphMemory(GraphMemoryProtocol):
    """
    Graph memory implementation using Spanner
    
    This bridges the GraphitiMemory interface with SpannerGraphClient,
    providing entity extraction and graph operations backed by Spanner.
    """
    
    def __init__(
        self, 
        user_id: str, 
        session_id: str,
        spanner_client: SpannerGraphClient
    ):
        self.user_id = user_id
        self.session_id = session_id
        self.client = spanner_client
        self.extractor = EntityExtractor()
        self._initialized = False
        
        # Cache for performance
        self._entity_cache: Dict[str, Entity] = {}
        self._relationship_cache: List[Relationship] = []
    
    async def initialize(self) -> None:
        """Initialize Spanner connection and ensure user exists"""
        if not self._initialized:
            # Client should already be initialized
            if not self.client._initialized:
                await self.client.initialize()
            
            # Ensure user exists
            await self._ensure_user_exists()
            self._initialized = True
            
            logger.info(f"SpannerGraphMemory initialized for user {self.user_id}")
    
    async def _ensure_user_exists(self) -> None:
        """Ensure user exists in Spanner"""
        user_data = {
            "user_id": self.user_id,
            "email": f"{self.user_id}@leafloaf.com",
            "name": f"User {self.user_id}",
            "shopping_pattern": "regular"
        }
        
        try:
            await self.client.add_user(user_data)
        except Exception as e:
            # User might already exist
            logger.debug(f"User creation: {e}")
    
    async def process_message(
        self, 
        message: str, 
        role: str = "human",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a message and extract entities/relationships"""
        metadata = metadata or {}
        
        # Extract entities and relationships using existing extractor
        entities = self.extractor.extract_entities(message, metadata)
        relationships = self.extractor.extract_relationships(entities, message, metadata)
        
        # Cache entities
        for entity in entities:
            cache_key = f"{entity.type.value}:{entity.value}"
            self._entity_cache[cache_key] = entity
        
        self._relationship_cache.extend(relationships)
        
        # Add as episode to Spanner for GraphRAG
        try:
            episode_id = await self.client.add_episode(
                user_id=self.user_id,
                content=message,
                episode_type=f"{role}_message",
                metadata={
                    "session_id": self.session_id,
                    "entities": [e.to_dict() for e in entities],
                    "relationships": [r.to_dict() for r in relationships],
                    **metadata
                }
            )
            
            logger.debug(f"Added episode {episode_id} with {len(entities)} entities")
            
        except Exception as e:
            logger.error(f"Failed to persist to Spanner: {e}")
        
        return {
            "entities": [e.to_dict() for e in entities],
            "relationships": [r.to_dict() for r in relationships],
            "entity_count": len(entities),
            "relationship_count": len(relationships)
        }
    
    async def get_context(self, query: str) -> Dict[str, Any]:
        """Get relevant context for a query using GraphRAG"""
        try:
            # Use Spanner's GraphRAG search
            graphrag_result = await self.client.graphrag_search(
                query=query,
                user_id=self.user_id
            )
            
            # Get reorder patterns
            reorder_patterns = await self.client.get_reorder_patterns(self.user_id)
            
            # Extract entities from current query
            query_entities = self.extractor.extract_entities(query)
            
            # Get user patterns (additional context)
            user_patterns = await self.get_user_patterns(self.user_id)
            
            return {
                "user_context": graphrag_result.get("graph_context", {}),
                "reorder_patterns": reorder_patterns,
                "session_context": {
                    "query": query,
                    "graphrag_answer": graphrag_result.get("answer", ""),
                    "confidence": graphrag_result.get("confidence", 0.0)
                },
                "query_entities": [e.to_dict() for e in query_entities],
                "cached_entities": list(self._entity_cache.keys()),
                "user_patterns": user_patterns
            }
            
        except Exception as e:
            logger.error(f"Failed to get context from Spanner: {e}")
            return {
                "user_context": {},
                "reorder_patterns": [],
                "session_context": {},
                "query_entities": [],
                "cached_entities": []
            }
    
    async def get_user_patterns(self, user_id: str) -> Dict[str, Any]:
        """Get user behavior patterns from Spanner"""
        try:
            # This would be enhanced with actual Spanner queries
            patterns = {
                "shopping_frequency": "weekly",
                "preferred_categories": [],
                "average_order_value": 0.0,
                "favorite_brands": [],
                "dietary_preferences": []
            }
            
            # Get from Spanner (simplified for now)
            reorder_patterns = await self.client.get_reorder_patterns(user_id)
            
            if reorder_patterns:
                # Extract insights from patterns
                patterns["frequently_ordered"] = [
                    p["product_name"] for p in reorder_patterns[:5]
                ]
                
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to get user patterns: {e}")
            return {}
    
    async def add_order(self, order_data: Dict[str, Any]) -> str:
        """Add an order to the graph"""
        try:
            # Ensure user_id is set
            order_data["user_id"] = self.user_id
            
            # Add order through Spanner client
            order_id = await self.client.add_order(order_data)
            
            # Extract entities from order for future context
            order_text = f"Order {order_id}: "
            for item in order_data.get("items", []):
                order_text += f"{item['quantity']} {item.get('name', 'item')}, "
            
            await self.process_message(
                order_text,
                role="system",
                metadata={"order_id": order_id, "event": "order_placed"}
            )
            
            return order_id
            
        except Exception as e:
            logger.error(f"Failed to add order: {e}")
            raise
    
    async def close(self) -> None:
        """Close connections - Spanner client handles this"""
        logger.info(f"Closing SpannerGraphMemory for user {self.user_id}")
        # Spanner client has its own lifecycle management
        self._entity_cache.clear()
        self._relationship_cache.clear()