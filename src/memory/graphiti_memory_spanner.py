"""
Graphiti Memory Implementation with Spanner Backend

This is the production version of GraphitiMemory that uses
Google Cloud Spanner instead of Neo4j for graph storage.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass, asdict
import re
from enum import Enum

from src.integrations.spanner_graph_client import SpannerGraphClient
from src.models.state import SearchState

logger = logging.getLogger(__name__)


# Reuse the existing entity and relationship classes
from src.memory.graphiti_memory import (
    EntityType, RelationshipType, Entity, Relationship
)
from src.memory.gemini_production_extractor import GeminiProductionExtractor


class GraphitiMemorySpanner:
    """
    Main Graphiti memory implementation using Spanner
    
    This is a drop-in replacement for the Neo4j version,
    providing the same interface but backed by Spanner.
    """
    
    def __init__(self, user_id: str, session_id: str):
        self.user_id = user_id
        self.session_id = session_id
        self.extractor = GeminiProductionExtractor()
        self._spanner_client = None
        self._initialized = False
        
        # Import memory manager to avoid circular dependency
        from src.memory.memory_manager import memory_manager
        self._memory_manager = memory_manager
        
        # Entity and relationship caches
        self._entity_cache: Dict[str, Entity] = {}
        self._relationship_cache: List[Relationship] = []
        
    async def initialize(self):
        """Initialize Spanner connection"""
        if self._initialized:
            return
            
        try:
            # Create Spanner client
            self._spanner_client = SpannerGraphClient()
            await self._spanner_client.initialize()
            
            # Ensure user exists in graph
            await self._ensure_user_exists()
            
            self._initialized = True
            logger.info(f"GraphitiMemorySpanner initialized for user {self.user_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Spanner: {e}")
            raise
    
    async def _ensure_user_exists(self):
        """Ensure user node exists in Spanner"""
        user_data = {
            "user_id": self.user_id,
            "email": f"{self.user_id}@leafloaf.com",
            "name": f"User {self.user_id}",
            "preferences": {},
            "shopping_pattern": "unknown"
        }
        
        try:
            await self._spanner_client.add_user(user_data)
            logger.debug(f"User {self.user_id} ensured in Spanner")
        except Exception as e:
            # User might already exist, which is fine
            logger.debug(f"User creation result: {e}")
    
    async def process_message(
        self, 
        message: str, 
        role: str = "human",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a message and extract entities/relationships"""
        if not self._initialized:
            await self.initialize()
            
        metadata = metadata or {}
        
        # Extract entities and relationships using Gemini
        extraction_result = await self.extractor.extract_entities_and_relationships(message, metadata)
        
        # Map entity types from extractor to our internal types
        type_mapping = {
            "product": EntityType.PRODUCT,
            "brand": EntityType.BRAND,
            "category": EntityType.CATEGORY,
            "attribute": EntityType.PREFERENCE,  # Map attribute to preference
            "dietary_restriction": EntityType.CONSTRAINT,
            "preference": EntityType.PREFERENCE,
            "event": EntityType.EVENT,
            "time_period": EntityType.TIME_PERIOD,
            "quantity": EntityType.CONSTRAINT,  # Map quantity to constraint
            "location": EntityType.LOCATION
        }
        
        # Convert to our internal format
        entities = []
        for ext_entity in extraction_result.get("entities", []):
            try:
                # Get the entity type string
                entity_type_str = ext_entity.type.value if hasattr(ext_entity.type, 'value') else str(ext_entity.type)
                
                # Map to our internal type
                internal_type = type_mapping.get(entity_type_str.lower(), EntityType.PRODUCT)
                
                entity = Entity(
                    type=internal_type,
                    value=ext_entity.name,
                    properties=ext_entity.properties
                )
                entities.append(entity)
            except Exception as e:
                logger.warning(f"Failed to map entity {ext_entity}: {e}")
        
        # Map relationship types
        rel_type_mapping = {
            "prefers": RelationshipType.PREFERS,
            "avoids": RelationshipType.AVOIDS,
            "purchased": RelationshipType.PLACED,
            "reorders": RelationshipType.REORDERS,
            "mentioned_with": RelationshipType.BOUGHT_WITH,
            "belongs_to": RelationshipType.CONTAINS,
            "has_attribute": RelationshipType.PREFERS
        }
        
        relationships = []
        for ext_rel in extraction_result.get("relationships", []):
            try:
                # Find source and target entities
                source_entity = next((e for e in entities if e.value == ext_rel.source), None)
                target_entity = next((e for e in entities if e.value == ext_rel.target), None)
                
                if source_entity and target_entity:
                    # Get relationship type string
                    rel_type_str = ext_rel.type.value if hasattr(ext_rel.type, 'value') else str(ext_rel.type)
                    
                    # Map to our internal type
                    internal_rel_type = rel_type_mapping.get(rel_type_str.lower(), RelationshipType.CONTAINS)
                    
                    rel = Relationship(
                        from_entity=source_entity,
                        to_entity=target_entity,
                        type=internal_rel_type,
                        properties=ext_rel.properties
                    )
                    relationships.append(rel)
            except Exception as e:
                logger.warning(f"Failed to map relationship {ext_rel}: {e}")
        
        # Store in cache
        for entity in entities:
            cache_key = f"{entity.type.value}:{entity.value}"
            self._entity_cache[cache_key] = entity
        
        self._relationship_cache.extend(relationships)
        
        # Store in Spanner as an episode
        try:
            episode_id = await self._spanner_client.add_episode(
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
            
            logger.debug(f"Stored episode {episode_id} with {len(entities)} entities")
            
        except Exception as e:
            logger.error(f"Failed to persist to Spanner: {e}")
        
        # Store in session memory for immediate access
        # TODO: Fix session memory integration
        # await self._update_session_memory(message, role, entities, relationships)
        
        return {
            "entities": [e.to_dict() for e in entities],
            "relationships": [r.to_dict() for r in relationships],
            "entity_count": len(entities),
            "relationship_count": len(relationships)
        }
    
    async def _update_session_memory(
        self,
        message: str,
        role: str,
        entities: List[Entity],
        relationships: List[Relationship]
    ):
        """Update session memory with extracted information"""
        memory = self._memory_manager.get_memory(self.session_id)
        
        # Add to conversation history
        memory.add_message(role, message)
        
        # Update extracted entities in session
        extracted_data = memory.data.get("extracted_entities", {})
        
        for entity in entities:
            entity_type = entity.type.value
            if entity_type not in extracted_data:
                extracted_data[entity_type] = []
            
            extracted_data[entity_type].append({
                "value": entity.value,
                "properties": entity.properties,
                "timestamp": datetime.now().isoformat()
            })
        
        memory.data["extracted_entities"] = extracted_data
        memory.data["last_extraction"] = datetime.now().isoformat()
    
    async def get_context(self, query: str) -> Dict[str, Any]:
        """Get relevant context for a query using Spanner's GraphRAG"""
        if not self._initialized:
            await self.initialize()
            
        try:
            # Use Spanner's GraphRAG search
            graphrag_result = await self._spanner_client.graphrag_search(
                query=query,
                user_id=self.user_id
            )
            
            # Get reorder patterns
            reorder_patterns = await self._spanner_client.get_reorder_patterns(self.user_id)
            
            # Get session context
            memory = self._memory_manager.get_memory(self.session_id)
            session_context = {
                "recent_messages": memory.get_messages(-5),  # Last 5 messages
                "extracted_entities": memory.data.get("extracted_entities", {}),
                "preferences": memory.data.get("preferences", {})
            }
            
            # Extract entities from current query
            query_entities = self.extractor.extract_entities(query)
            
            return {
                "user_context": graphrag_result.get("graph_context", {}),
                "reorder_patterns": reorder_patterns,
                "session_context": session_context,
                "query_entities": [e.to_dict() for e in query_entities],
                "cached_entities": list(self._entity_cache.keys()),
                "graphrag_answer": graphrag_result.get("answer", ""),
                "confidence": graphrag_result.get("confidence", 0.0),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get context from Spanner: {e}")
            # Return minimal context on error
            return {
                "user_context": {},
                "reorder_patterns": [],
                "session_context": {},
                "query_entities": [],
                "cached_entities": list(self._entity_cache.keys())
            }
    
    async def find_similar_queries(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find similar past queries using Spanner"""
        if not self._initialized:
            await self.initialize()
            
        # Extract entities from current query
        entities = self.extractor.extract_entities(query)
        
        if not entities:
            return []
        
        # This would use Spanner's search capabilities
        # For now, return empty list - to be implemented with actual Spanner queries
        return []
    
    async def get_product_relationships(self, product_name: str) -> Dict[str, Any]:
        """Get products frequently bought together from Spanner"""
        if not self._initialized:
            await self.initialize()
            
        # This would query Spanner's ProductRelationships table
        # For now, return empty dict - to be implemented
        return {
            "product": product_name,
            "bought_with": [],
            "substitutes": [],
            "order_count": 0,
            "last_ordered": None
        }
    
    async def add_order_context(self, order_data: Dict[str, Any]) -> None:
        """Add order information to the graph"""
        if not self._initialized:
            await self.initialize()
            
        try:
            # Transform order data for Spanner compatibility
            spanner_order_data = {
                "order_id": order_data["order_id"],
                "user_id": self.user_id,
                "timestamp": order_data["timestamp"],
                "total_amount": order_data["totals"]["estimated_total"],
                "item_count": order_data["totals"]["item_count"],
                "items": order_data["items"],
                "metadata": order_data.get("metadata", {})
            }
            
            # Add order through Spanner
            logger.info(f"Sending order to Spanner: {spanner_order_data['order_id']}")
            order_id = await self._spanner_client.add_order(spanner_order_data)
            logger.info(f"Successfully added order {order_id} to Spanner")
            
            # Process order as a message for entity extraction
            order_text = self._format_order_as_text(order_data)
            await self.process_message(
                order_text,
                role="system",
                metadata={"order_id": order_id, "event": "order_placed"}
            )
            
            logger.info(f"Added order {order_id} to graph")
            
        except Exception as e:
            logger.error(f"Failed to add order context: {e}")
    
    def _format_order_as_text(self, order_data: Dict[str, Any]) -> str:
        """Format order as natural language for entity extraction"""
        items = order_data.get("items", [])
        text = f"Order {order_data.get('order_id', 'unknown')}:\n"
        
        for item in items:
            text += f"- {item.get('quantity', 1)} {item.get('name', 'Unknown')} at ₹{item.get('price', 0)}\n"
        
        text += f"Total: ₹{order_data.get('totals', {}).get('estimated_total', 0)}"
        return text
    
    async def process_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process an order and update the knowledge graph"""
        try:
            # Add order to Spanner and extract entities
            await self.add_order_context(order_data)
            
            # Extract key information for personalization
            items = order_data.get("items", [])
            products = []
            brands = []
            categories = []
            
            for item in items:
                products.append(item.get("name", ""))
                if "brand" in item:
                    brands.append(item["brand"])
                if "category" in item:
                    categories.append(item["category"])
            
            # Update user patterns
            await self._update_reorder_patterns(order_data)
            
            return {
                "success": True,
                "order_id": order_data.get("order_id"),
                "processed_items": len(items),
                "entities_extracted": {
                    "products": products,
                    "brands": brands,
                    "categories": categories
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to process order: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _update_reorder_patterns(self, order_data: Dict[str, Any]) -> None:
        """Update reorder patterns in Spanner"""
        try:
            # This would update the ReorderPatterns table
            # For now, just log
            logger.info(f"Updating reorder patterns for user {self.user_id}")
            
            # In production, this would:
            # 1. Calculate days since last order for each item
            # 2. Update average reorder cycle
            # 3. Predict next order date
            # 4. Store in ReorderPatterns table
            
        except Exception as e:
            logger.error(f"Failed to update reorder patterns: {e}")
    
    async def close(self):
        """Clean up resources"""
        logger.info(f"Closing GraphitiMemorySpanner for user {self.user_id}")
        self._entity_cache.clear()
        self._relationship_cache.clear()
        # Spanner client handles its own cleanup
    
    # Pattern storage and retrieval methods
    
    async def get_user_patterns(self, pattern_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get learned patterns for the user from Graphiti"""
        try:
            # Build query based on pattern types
            edge_types = []
            if not pattern_types:
                # Get all pattern types
                edge_types = [
                    "PREFERS_BRAND", "PREFERS_CATEGORY", 
                    "BOUGHT_WITH", "REORDERS_EVERY",
                    "HAS_SHOPPING_PATTERN", "ACTIVE_SESSION"
                ]
            else:
                edge_types = pattern_types
            
            # Query Graphiti edges
            patterns = await self._spanner_client.query_patterns(
                user_id=self.user_id,
                edge_types=edge_types,
                min_confidence=0.5
            )
            
            # Organize by pattern type
            organized_patterns = {
                "preferences": [],
                "associations": [],
                "reorder": [],
                "behavior": [],
                "session": []
            }
            
            for pattern in patterns:
                edge_type = pattern.get("edge_type", "")
                
                if "PREFERS" in edge_type:
                    organized_patterns["preferences"].append(pattern)
                elif "BOUGHT_WITH" in edge_type:
                    organized_patterns["associations"].append(pattern)
                elif "REORDERS" in edge_type:
                    organized_patterns["reorder"].append(pattern)
                elif "SHOPPING_PATTERN" in edge_type:
                    organized_patterns["behavior"].append(pattern)
                elif "SESSION" in edge_type:
                    organized_patterns["session"].append(pattern)
            
            return organized_patterns
            
        except Exception as e:
            logger.error(f"Failed to get user patterns: {e}")
            return {}
    
    async def get_product_patterns(self, product_sku: str) -> Dict[str, Any]:
        """Get patterns related to a specific product"""
        try:
            patterns = await self._spanner_client.query_product_patterns(
                product_sku=f"product:{product_sku}",
                min_confidence=0.5
            )
            
            return {
                "associations": [p for p in patterns if p["edge_type"] == "BOUGHT_WITH"],
                "user_preferences": [p for p in patterns if "PREFERS" in p["edge_type"]],
                "reorder_patterns": [p for p in patterns if "REORDERS" in p["edge_type"]]
            }
            
        except Exception as e:
            logger.error(f"Failed to get product patterns: {e}")
            return {}
    
    async def store_pattern_feedback(self, pattern_id: str, feedback: Dict[str, Any]):
        """Store feedback about pattern effectiveness"""
        try:
            # Update pattern confidence based on feedback
            if feedback.get("effective", False):
                # Increase confidence
                await self._spanner_client.adjust_edge_confidence(
                    edge_id=pattern_id,
                    adjustment=0.05  # 5% increase
                )
            else:
                # Decrease confidence
                await self._spanner_client.adjust_edge_confidence(
                    edge_id=pattern_id,
                    adjustment=-0.05  # 5% decrease
                )
            
            # Store detailed feedback
            await self._spanner_client.add_pattern_feedback(
                edge_id=pattern_id,
                feedback=feedback
            )
            
            logger.debug(f"Stored feedback for pattern {pattern_id}")
            
        except Exception as e:
            logger.error(f"Failed to store pattern feedback: {e}")