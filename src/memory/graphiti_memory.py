"""
Graphiti Memory Implementation for LeafLoaf

Production-grade memory system that:
- Extracts entities and relationships from conversations
- Maintains temporal context
- Integrates with Neo4j for persistent storage
- Provides rich context for agents
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass, asdict
import re
from enum import Enum

# from src.integrations.neo4j_config import get_graphiti_neo4j  # Removed - using Spanner now
# from src.memory.memory_manager import MemoryManager  # Avoid circular import
from src.models.state import SearchState

logger = logging.getLogger(__name__)


class EntityType(Enum):
    """Types of entities we extract"""
    USER = "User"
    PRODUCT = "Product"
    BRAND = "Brand"
    CATEGORY = "Category"
    ORDER = "Order"
    EVENT = "Event"
    PREFERENCE = "Preference"
    CONSTRAINT = "Constraint"
    LOCATION = "Location"
    TIME_PERIOD = "TimePeriod"


class RelationshipType(Enum):
    """Types of relationships between entities"""
    PLACED = "PLACED"
    CONTAINS = "CONTAINS"
    BOUGHT_WITH = "BOUGHT_WITH"
    PREFERS = "PREFERS"
    AVOIDS = "AVOIDS"
    SIMILAR_TO = "SIMILAR_TO"
    SUBSTITUTE_FOR = "SUBSTITUTE_FOR"
    REORDERS = "REORDERS"
    SHOPS_FOR = "SHOPS_FOR"
    OCCURRED_AT = "OCCURRED_AT"
    MENTIONED = "MENTIONED"
    SEARCHED_FOR = "SEARCHED_FOR"


@dataclass
class Entity:
    """Represents an extracted entity"""
    type: EntityType
    value: str
    properties: Dict[str, Any]
    confidence: float = 1.0
    source: str = "conversation"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "value": self.value,
            "properties": self.properties,
            "confidence": self.confidence,
            "source": self.source
        }


@dataclass
class Relationship:
    """Represents a relationship between entities"""
    from_entity: Entity
    to_entity: Entity
    type: RelationshipType
    properties: Dict[str, Any]
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "from": self.from_entity.to_dict(),
            "to": self.to_entity.to_dict(),
            "type": self.type.value,
            "properties": self.properties,
            "confidence": self.confidence
        }


class EntityExtractor:
    """Extract entities and relationships from text"""
    
    def __init__(self):
        # Product-related patterns
        self.product_patterns = [
            r'\b(rice|dal|atta|oil|milk|bread|eggs?|butter|cheese|yogurt|fruits?|vegetables?)\b',
            r'\b(basmati|jasmine|brown rice|whole wheat|multigrain)\b',
            r'\b(toor dal|masoor dal|moong dal|chana dal|urad dal)\b',
            r'\b(olive oil|coconut oil|mustard oil|sunflower oil)\b'
        ]
        
        # Brand patterns
        self.brand_patterns = [
            r'\b(Daawat|India Gate|Fortune|Aashirvaad|Amul|Mother Dairy|Britannia|Parle)\b',
            r'\b(Tata|Reliance|BigBasket|Grofers|DMart)\b'
        ]
        
        # Quantity patterns
        self.quantity_patterns = [
            r'(\d+)\s*(kg|g|l|ml|dozen|packets?|bags?|bottles?|cans?|boxes?)\b',
            r'(half|quarter|one|two|three|four|five|six|seven|eight|nine|ten)\s*(kg|kilo|liter|dozen)',
        ]
        
        # Time patterns
        self.time_patterns = [
            r'\b(daily|weekly|monthly|biweekly|fortnightly)\b',
            r'\b(every\s+\w+day|every\s+week|every\s+month)\b',
            r'\b(last\s+time|last\s+week|last\s+month|yesterday|today)\b',
            r'\b(morning|evening|afternoon|night|weekend)\b'
        ]
        
        # Event patterns  
        self.event_patterns = [
            r'\b(party|birthday|anniversary|wedding|celebration|gathering|event)\b',
            r'\b(Diwali|Holi|Eid|Christmas|New Year|festival)\b',
            r'\b(breakfast|lunch|dinner|snacks|tea time)\b'
        ]
        
        # Preference patterns
        self.preference_patterns = [
            r'\b(organic|natural|fresh|premium|budget|cheap|expensive)\b',
            r'\b(healthy|sugar-free|gluten-free|vegan|vegetarian)\b',
            r'\b(favorite|usual|regular|preferred|like|love|want|need)\b',
            r'\b(don\'t like|avoid|allergic|hate|dislike)\b'
        ]
    
    def extract_entities(self, text: str, context: Optional[Dict[str, Any]] = None) -> List[Entity]:
        """Extract entities from text with context"""
        entities = []
        text_lower = text.lower()
        
        # Extract products
        for pattern in self.product_patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                entity = Entity(
                    type=EntityType.PRODUCT,
                    value=match.group(),
                    properties={
                        "mentioned_at": datetime.now().isoformat(),
                        "context": text[:100]
                    }
                )
                entities.append(entity)
        
        # Extract brands
        for pattern in self.brand_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                entity = Entity(
                    type=EntityType.BRAND,
                    value=match.group(),
                    properties={"context": text[:100]}
                )
                entities.append(entity)
        
        # Extract quantities (useful for understanding order patterns)
        for pattern in self.quantity_patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                entity = Entity(
                    type=EntityType.CONSTRAINT,
                    value=match.group(),
                    properties={
                        "constraint_type": "quantity",
                        "context": text[:100]
                    }
                )
                entities.append(entity)
        
        # Extract time periods
        for pattern in self.time_patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                entity = Entity(
                    type=EntityType.TIME_PERIOD,
                    value=match.group(),
                    properties={
                        "period_type": self._classify_time_period(match.group()),
                        "context": text[:100]
                    }
                )
                entities.append(entity)
        
        # Extract events
        for pattern in self.event_patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                entity = Entity(
                    type=EntityType.EVENT,
                    value=match.group(),
                    properties={
                        "event_type": self._classify_event(match.group()),
                        "context": text[:100]
                    }
                )
                entities.append(entity)
        
        # Extract preferences
        for pattern in self.preference_patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                entity = Entity(
                    type=EntityType.PREFERENCE,
                    value=match.group(),
                    properties={
                        "preference_type": self._classify_preference(match.group()),
                        "context": text[:100]
                    }
                )
                entities.append(entity)
        
        return entities
    
    def extract_relationships(
        self, 
        entities: List[Entity], 
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Relationship]:
        """Extract relationships between entities"""
        relationships = []
        text_lower = text.lower()
        
        # Product mentioned with brand
        brands = [e for e in entities if e.type == EntityType.BRAND]
        products = [e for e in entities if e.type == EntityType.PRODUCT]
        
        for brand in brands:
            for product in products:
                # Check if brand and product are mentioned close together
                if self._are_entities_related(brand.value, product.value, text):
                    rel = Relationship(
                        from_entity=product,
                        to_entity=brand,
                        type=RelationshipType.PREFERS,
                        properties={"context": text[:100]}
                    )
                    relationships.append(rel)
        
        # Product with quantity constraints
        constraints = [e for e in entities if e.type == EntityType.CONSTRAINT]
        for product in products:
            for constraint in constraints:
                if self._are_entities_related(product.value, constraint.value, text):
                    rel = Relationship(
                        from_entity=product,
                        to_entity=constraint,
                        type=RelationshipType.MENTIONED,
                        properties={"context": text[:100]}
                    )
                    relationships.append(rel)
        
        # Event with products
        events = [e for e in entities if e.type == EntityType.EVENT]
        for event in events:
            for product in products:
                if self._are_entities_related(event.value, product.value, text):
                    rel = Relationship(
                        from_entity=event,
                        to_entity=product,
                        type=RelationshipType.MENTIONED,
                        properties={
                            "context": text[:100],
                            "event_type": event.properties.get("event_type")
                        }
                    )
                    relationships.append(rel)
        
        # Time patterns with products (for reorder patterns)
        time_periods = [e for e in entities if e.type == EntityType.TIME_PERIOD]
        for time_period in time_periods:
            for product in products:
                if self._are_entities_related(time_period.value, product.value, text):
                    rel = Relationship(
                        from_entity=product,
                        to_entity=time_period,
                        type=RelationshipType.REORDERS,
                        properties={
                            "frequency": time_period.value,
                            "context": text[:100]
                        }
                    )
                    relationships.append(rel)
        
        return relationships
    
    def _are_entities_related(self, entity1: str, entity2: str, text: str, max_distance: int = 50) -> bool:
        """Check if two entities are related based on proximity in text"""
        text_lower = text.lower()
        pos1 = text_lower.find(entity1.lower())
        pos2 = text_lower.find(entity2.lower())
        
        if pos1 == -1 or pos2 == -1:
            return False
        
        return abs(pos1 - pos2) <= max_distance
    
    def _classify_time_period(self, time_text: str) -> str:
        """Classify the type of time period"""
        if any(word in time_text for word in ["daily", "every day"]):
            return "recurring_daily"
        elif any(word in time_text for word in ["weekly", "every week"]):
            return "recurring_weekly"
        elif any(word in time_text for word in ["monthly", "every month"]):
            return "recurring_monthly"
        elif any(word in time_text for word in ["last", "yesterday"]):
            return "past_reference"
        else:
            return "time_of_day"
    
    def _classify_event(self, event_text: str) -> str:
        """Classify the type of event"""
        if any(word in event_text for word in ["party", "birthday", "anniversary", "wedding"]):
            return "celebration"
        elif any(word in event_text for word in ["Diwali", "Holi", "Eid", "Christmas", "festival"]):
            return "festival"
        elif any(word in event_text for word in ["breakfast", "lunch", "dinner"]):
            return "meal"
        else:
            return "general_event"
    
    def _classify_preference(self, pref_text: str) -> str:
        """Classify the type of preference"""
        if any(word in pref_text for word in ["organic", "natural", "healthy", "sugar-free"]):
            return "health_preference"
        elif any(word in pref_text for word in ["budget", "cheap", "expensive", "premium"]):
            return "price_preference"
        elif any(word in pref_text for word in ["favorite", "usual", "regular"]):
            return "brand_preference"
        elif any(word in pref_text for word in ["don't", "avoid", "allergic", "hate"]):
            return "avoidance"
        else:
            return "general_preference"


class GraphitiMemory:
    """Main Graphiti memory implementation"""
    
    def __init__(self, user_id: str, session_id: str):
        self.user_id = user_id
        self.session_id = session_id
        self.extractor = EntityExtractor()
        self._neo4j = None
        from src.memory.memory_manager import memory_manager
        self._memory_manager = memory_manager
        self._entity_cache: Dict[str, Entity] = {}
        self._relationship_cache: List[Relationship] = []
        
    async def initialize(self):
        """Initialize Neo4j connection"""
        self._neo4j = await get_graphiti_neo4j()
        
        # Ensure user exists in graph
        await self._ensure_user_exists()
    
    async def _ensure_user_exists(self):
        """Ensure user node exists in graph"""
        user_data = {
            "user_id": self.user_id,
            "email": f"{self.user_id}@leafloaf.com",  # Placeholder
            "name": f"User {self.user_id}",
            "preferences": {},
            "shopping_pattern": "unknown"
        }
        
        # Check if user exists
        query = "MATCH (u:User {user_id: $user_id}) RETURN u"
        result = await self._neo4j.connection.execute_query(
            query, {"user_id": self.user_id}
        )
        
        if not result:
            await self._neo4j.create_user(user_data)
    
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
        
        # Store in cache
        for entity in entities:
            cache_key = f"{entity.type.value}:{entity.value}"
            self._entity_cache[cache_key] = entity
        
        self._relationship_cache.extend(relationships)
        
        # Store in Neo4j (async, non-blocking)
        asyncio.create_task(self._persist_to_graph(entities, relationships, message))
        
        # Store in session memory
        await self._update_session_memory(message, role, entities, relationships)
        
        return {
            "entities": [e.to_dict() for e in entities],
            "relationships": [r.to_dict() for r in relationships],
            "entity_count": len(entities),
            "relationship_count": len(relationships)
        }
    
    async def _persist_to_graph(
        self,
        entities: List[Entity],
        relationships: List[Relationship],
        message: str
    ):
        """Persist entities and relationships to Neo4j"""
        try:
            # Create message node
            message_query = """
            CREATE (m:Message {
                session_id: $session_id,
                user_id: $user_id,
                content: $content,
                timestamp: datetime(),
                entity_count: $entity_count,
                relationship_count: $relationship_count
            })
            
            WITH m
            MATCH (u:User {user_id: $user_id})
            CREATE (u)-[:SENT]->(m)
            
            RETURN id(m) as message_id
            """
            
            await self._neo4j.connection.execute_write(message_query, {
                "session_id": self.session_id,
                "user_id": self.user_id,
                "content": message[:500],  # Truncate for storage
                "entity_count": len(entities),
                "relationship_count": len(relationships)
            })
            
            # Store entities
            for entity in entities:
                await self._persist_entity(entity)
            
            # Store relationships
            for relationship in relationships:
                await self._persist_relationship(relationship)
                
        except Exception as e:
            logger.error(f"Error persisting to graph: {e}")
    
    async def _persist_entity(self, entity: Entity):
        """Persist an entity to Neo4j"""
        if entity.type == EntityType.PRODUCT:
            # Create or update product node
            query = """
            MERGE (p:Product {name: $name})
            SET p.last_mentioned = datetime(),
                p.mention_count = COALESCE(p.mention_count, 0) + 1
            
            WITH p
            MATCH (u:User {user_id: $user_id})
            MERGE (u)-[m:MENTIONED]->(p)
            SET m.last_mentioned = datetime(),
                m.count = COALESCE(m.count, 0) + 1
            """
            
            await self._neo4j.connection.execute_write(query, {
                "name": entity.value,
                "user_id": self.user_id
            })
            
        elif entity.type == EntityType.EVENT:
            # Create event node
            query = """
            CREATE (e:Event {
                name: $name,
                type: $event_type,
                user_id: $user_id,
                timestamp: datetime()
            })
            
            WITH e
            MATCH (u:User {user_id: $user_id})
            CREATE (u)-[:PLANNED]->(e)
            """
            
            await self._neo4j.connection.execute_write(query, {
                "name": entity.value,
                "event_type": entity.properties.get("event_type", "general"),
                "user_id": self.user_id
            })
    
    async def _persist_relationship(self, relationship: Relationship):
        """Persist a relationship to Neo4j"""
        # This is simplified - in production, you'd have more sophisticated matching
        pass
    
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
        """Get relevant context for a query"""
        # Get user context from graph
        user_context = await self._neo4j.get_user_context(self.user_id)
        
        # Get reorder patterns
        reorder_patterns = await self._neo4j.find_reorder_patterns(self.user_id)
        
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
            "user_context": user_context,
            "reorder_patterns": reorder_patterns,
            "session_context": session_context,
            "query_entities": [e.to_dict() for e in query_entities],
            "cached_entities": list(self._entity_cache.keys()),
            "timestamp": datetime.now().isoformat()
        }
    
    async def find_similar_queries(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find similar past queries using graph"""
        # Extract entities from current query
        entities = self.extractor.extract_entities(query)
        
        if not entities:
            return []
        
        # Find messages with similar entities
        entity_values = [e.value for e in entities]
        
        query_neo4j = """
        MATCH (u:User {user_id: $user_id})-[:SENT]->(m:Message)
        WHERE any(entity IN $entities WHERE m.content CONTAINS entity)
        RETURN m.content as query,
               m.timestamp as timestamp,
               m.entity_count as entity_count
        ORDER BY m.timestamp DESC
        LIMIT $limit
        """
        
        results = await self._neo4j.connection.execute_query(query_neo4j, {
            "user_id": self.user_id,
            "entities": entity_values,
            "limit": limit
        })
        
        return results
    
    async def get_product_relationships(self, product_name: str) -> Dict[str, Any]:
        """Get products frequently bought together"""
        query = """
        MATCH (p:Product {name: $product_name})
        OPTIONAL MATCH (p)-[:BOUGHT_WITH]-(related:Product)
        OPTIONAL MATCH (p)-[:SUBSTITUTE_FOR]-(substitute:Product)
        OPTIONAL MATCH (p)<-[:CONTAINS]-(o:Order)<-[:PLACED]-(u:User {user_id: $user_id})
        
        RETURN p as product,
               collect(DISTINCT related) as bought_with,
               collect(DISTINCT substitute) as substitutes,
               count(DISTINCT o) as order_count,
               max(o.timestamp) as last_ordered
        """
        
        result = await self._neo4j.connection.execute_query(query, {
            "product_name": product_name,
            "user_id": self.user_id
        })
        
        return result[0] if result else {}
    
    async def close(self):
        """Clean up resources"""
        # Neo4j connection is managed by singleton
        pass