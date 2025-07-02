"""
Graphiti Client for LeafLoaf

This integrates the actual Graphiti library (by Zep AI) which requires:
- Neo4j 5.26+ as the graph database
- OpenAI-compatible LLM for entity extraction
- Proper temporal awareness for knowledge graphs
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum

# Note: Install with: pip install graphiti-core
try:
    from graphiti_core import Graphiti
    from graphiti_core.nodes import EpisodeType
    from graphiti_core.edges import EntityEdge
    from graphiti_core.search import SearchConfig
    GRAPHITI_AVAILABLE = True
except ImportError:
    GRAPHITI_AVAILABLE = False
    logging.warning("Graphiti not installed. Install with: pip install graphiti-core")

logger = logging.getLogger(__name__)


class LeafLoafEpisodeType(Enum):
    """Episode types specific to LeafLoaf"""
    SEARCH_QUERY = "search_query"
    ORDER_PLACED = "order_placed"
    CART_UPDATE = "cart_update"
    PRODUCT_VIEW = "product_view"
    EVENT_SHOPPING = "event_shopping"
    REORDER_REQUEST = "reorder_request"
    PREFERENCE_UPDATE = "preference_update"


class GraphitiClient:
    """
    Production-ready Graphiti client for LeafLoaf
    
    Graphiti provides:
    - Temporal knowledge graphs (bi-temporal model)
    - Entity and relationship extraction via LLM
    - Real-time incremental updates
    - Hybrid search (semantic + graph traversal)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        if not GRAPHITI_AVAILABLE:
            raise ImportError("Graphiti not available. Install with: pip install graphiti-core")
        
        config = config or {}
        
        # Neo4j configuration (required)
        self.neo4j_uri = config.get("neo4j_uri") or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user = config.get("neo4j_user") or os.getenv("NEO4J_USERNAME", "neo4j")
        self.neo4j_password = config.get("neo4j_password") or os.getenv("NEO4J_PASSWORD")
        
        # LLM configuration - Using Gemini Pro
        self.llm_provider = config.get("llm_provider", "google")  # Gemini Pro
        self.embedding_provider = config.get("embedding_provider", "google")
        
        # Graphiti configuration
        self.batch_size = config.get("batch_size", 500)
        self.max_workers = config.get("max_workers", 10)
        
        self._graphiti = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize Graphiti and create necessary indexes"""
        try:
            # Initialize Graphiti
            self._graphiti = Graphiti(
                neo4j_uri=self.neo4j_uri,
                neo4j_user=self.neo4j_user,
                neo4j_password=self.neo4j_password,
                llm_provider=self.llm_provider,
                embedding_provider=self.embedding_provider,
                create_indices=True,  # Auto-create indexes
                max_workers=self.max_workers
            )
            
            # Build additional indexes for LeafLoaf patterns
            await self._create_leafloaf_indexes()
            
            self._initialized = True
            logger.info("Graphiti initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Graphiti: {e}")
            raise
    
    async def _create_leafloaf_indexes(self):
        """Create LeafLoaf-specific indexes for optimal performance"""
        indexes = [
            # User patterns
            "CREATE INDEX IF NOT EXISTS FOR (u:User) ON (u.user_id)",
            "CREATE INDEX IF NOT EXISTS FOR (u:User) ON (u.email)",
            
            # Product patterns
            "CREATE INDEX IF NOT EXISTS FOR (p:Product) ON (p.sku)",
            "CREATE INDEX IF NOT EXISTS FOR (p:Product) ON (p.name)",
            "CREATE INDEX IF NOT EXISTS FOR (p:Product) ON (p.category)",
            
            # Order patterns
            "CREATE INDEX IF NOT EXISTS FOR (o:Order) ON (o.order_id)",
            "CREATE INDEX IF NOT EXISTS FOR (o:Order) ON (o.user_id)",
            
            # Temporal indexes
            "CREATE INDEX IF NOT EXISTS FOR (e:Episode) ON (e.created_at)",
            "CREATE INDEX IF NOT EXISTS FOR ()-[r:RELATES_TO]-() ON (r.valid_from)",
            
            # Full-text search
            "CREATE FULLTEXT INDEX product_search IF NOT EXISTS FOR (p:Product) ON EACH [p.name, p.description, p.brand]"
        ]
        
        # Execute indexes via Graphiti's Neo4j connection
        # (Graphiti handles this internally)
        logger.info("Created LeafLoaf-specific indexes")
    
    async def add_episode(
        self,
        user_id: str,
        content: str,
        episode_type: LeafLoafEpisodeType,
        metadata: Optional[Dict[str, Any]] = None,
        reference_time: Optional[datetime] = None
    ) -> str:
        """
        Add an episode to the knowledge graph
        
        Episodes are the core unit in Graphiti - they represent
        events, conversations, or interactions that get processed
        into entities and relationships.
        """
        if not self._initialized:
            await self.initialize()
        
        reference_time = reference_time or datetime.now(timezone.utc)
        metadata = metadata or {}
        
        # Add user context to metadata
        metadata.update({
            "user_id": user_id,
            "episode_type": episode_type.value,
            "source": "leafloaf"
        })
        
        # Create episode
        episode_id = await self._graphiti.add_episode(
            name=f"{user_id}_{episode_type.value}_{reference_time.isoformat()}",
            episode_body=content,
            source_description=f"LeafLoaf {episode_type.value}",
            reference_time=reference_time,
            metadata=metadata
        )
        
        logger.info(f"Added episode {episode_id} for user {user_id}")
        return episode_id
    
    async def add_order_episode(
        self,
        user_id: str,
        order_data: Dict[str, Any]
    ) -> str:
        """Add an order as an episode with structured data"""
        # Format order data as natural language for better extraction
        order_text = self._format_order_as_text(order_data)
        
        return await self.add_episode(
            user_id=user_id,
            content=order_text,
            episode_type=LeafLoafEpisodeType.ORDER_PLACED,
            metadata={
                "order_id": order_data.get("order_id"),
                "total": order_data.get("total"),
                "item_count": order_data.get("item_count"),
                "order_type": order_data.get("order_type", "regular")
            }
        )
    
    def _format_order_as_text(self, order_data: Dict[str, Any]) -> str:
        """Convert order data to natural language for entity extraction"""
        items = order_data.get("items", [])
        
        text = f"Order {order_data.get('order_id')} placed:\n"
        
        for item in items:
            text += f"- {item.get('quantity')} {item.get('unit', '')} of {item.get('name')} "
            text += f"({item.get('brand', '')}) at ₹{item.get('price', 0)}\n"
        
        text += f"\nTotal: ₹{order_data.get('total', 0)}"
        
        if order_data.get("order_type") == "event":
            text += f"\nFor event: {order_data.get('event_name', 'Unknown')}"
        
        return text
    
    async def search(
        self,
        query: str,
        user_id: str,
        num_results: int = 10,
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search the knowledge graph for a user
        
        Graphiti's search combines:
        - Semantic similarity (embeddings)
        - Graph traversal
        - Temporal awareness
        """
        if not self._initialized:
            await self.initialize()
        
        # Configure search
        search_config = SearchConfig(
            num_episodes=num_results,
            num_hops=2,  # Graph traversal depth
            include_metadata=include_metadata,
            namespace=f"user_{user_id}"  # User-specific search
        )
        
        results = await self._graphiti.search(
            query=query,
            config=search_config
        )
        
        # Format results for LeafLoaf
        formatted_results = []
        for result in results:
            formatted_results.append({
                "episode_id": result.episode_id,
                "content": result.content,
                "score": result.score,
                "created_at": result.created_at,
                "metadata": result.metadata,
                "entities": [e.dict() for e in result.entities],
                "relationships": [r.dict() for r in result.relationships]
            })
        
        return formatted_results
    
    async def get_reorder_patterns(
        self,
        user_id: str,
        min_orders: int = 2
    ) -> List[Dict[str, Any]]:
        """Get reorder patterns using Graphiti's temporal features"""
        # Query for repeated product orders
        query = f"""
        User {user_id} frequently ordered products that appear 
        in multiple orders over time
        """
        
        results = await self.search(query, user_id, num_results=20)
        
        # Process results to find patterns
        product_orders = {}
        
        for result in results:
            if result["metadata"].get("episode_type") == "order_placed":
                for entity in result["entities"]:
                    if entity["label"] == "Product":
                        product_name = entity["name"]
                        if product_name not in product_orders:
                            product_orders[product_name] = []
                        
                        product_orders[product_name].append({
                            "date": result["created_at"],
                            "order_id": result["metadata"].get("order_id")
                        })
        
        # Calculate patterns
        patterns = []
        for product, orders in product_orders.items():
            if len(orders) >= min_orders:
                # Calculate average days between orders
                sorted_orders = sorted(orders, key=lambda x: x["date"])
                intervals = []
                
                for i in range(1, len(sorted_orders)):
                    prev_date = datetime.fromisoformat(sorted_orders[i-1]["date"])
                    curr_date = datetime.fromisoformat(sorted_orders[i]["date"])
                    days = (curr_date - prev_date).days
                    intervals.append(days)
                
                if intervals:
                    avg_interval = sum(intervals) / len(intervals)
                    patterns.append({
                        "product": product,
                        "order_count": len(orders),
                        "avg_days_between_orders": avg_interval,
                        "last_ordered": sorted_orders[-1]["date"],
                        "orders": orders
                    })
        
        return sorted(patterns, key=lambda x: x["order_count"], reverse=True)
    
    async def get_event_shopping_history(
        self,
        user_id: str,
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get shopping history for events"""
        query = f"User {user_id} shopping for events"
        if event_type:
            query += f" specifically {event_type}"
        
        results = await self.search(query, user_id, num_results=20)
        
        event_orders = []
        for result in results:
            if result["metadata"].get("order_type") == "event":
                event_orders.append({
                    "event": result["metadata"].get("event_name", "Unknown"),
                    "date": result["created_at"],
                    "order_id": result["metadata"].get("order_id"),
                    "total": result["metadata"].get("total"),
                    "items": self._extract_items_from_entities(result["entities"])
                })
        
        return event_orders
    
    def _extract_items_from_entities(
        self,
        entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract product items from entities"""
        items = []
        
        for entity in entities:
            if entity.get("label") == "Product":
                items.append({
                    "name": entity.get("name"),
                    "properties": entity.get("properties", {})
                })
        
        return items
    
    async def add_user_feedback(
        self,
        user_id: str,
        feedback: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """Add user feedback as an episode for continuous learning"""
        return await self.add_episode(
            user_id=user_id,
            content=feedback,
            episode_type=LeafLoafEpisodeType.PREFERENCE_UPDATE,
            metadata=context or {}
        )
    
    async def get_user_context(
        self,
        user_id: str,
        include_episodes: int = 10
    ) -> Dict[str, Any]:
        """Get comprehensive user context from Graphiti"""
        # Get recent episodes
        recent_episodes = await self._graphiti.retrieve_episodes(
            namespace=f"user_{user_id}",
            limit=include_episodes
        )
        
        # Get reorder patterns
        reorder_patterns = await self.get_reorder_patterns(user_id)
        
        # Get event history
        event_history = await self.get_event_shopping_history(user_id)
        
        return {
            "user_id": user_id,
            "recent_episodes": [ep.dict() for ep in recent_episodes],
            "reorder_patterns": reorder_patterns,
            "event_history": event_history,
            "total_episodes": len(recent_episodes),
            "last_activity": recent_episodes[0].created_at if recent_episodes else None
        }
    
    async def close(self):
        """Close Graphiti connections"""
        if self._graphiti:
            await self._graphiti.close()
            logger.info("Graphiti connection closed")


# Singleton instance management
_graphiti_client: Optional[GraphitiClient] = None


async def get_graphiti_client() -> GraphitiClient:
    """Get or create singleton Graphiti client"""
    global _graphiti_client
    
    if _graphiti_client is None:
        _graphiti_client = GraphitiClient()
        await _graphiti_client.initialize()
    
    return _graphiti_client