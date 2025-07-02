"""
Neo4j Configuration and Connection Management for Graphiti Integration

Production-grade implementation with:
- Connection pooling
- Health checks
- Auto-reconnect
- Query optimization
- Transaction management
"""

import os
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import asyncio
from contextlib import asynccontextmanager
from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from neo4j.exceptions import ServiceUnavailable, SessionExpired
import backoff

logger = logging.getLogger(__name__)


class Neo4jConfig:
    """Neo4j configuration with environment support"""
    
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.username = os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "leafloaf123")
        self.database = os.getenv("NEO4J_DATABASE", "neo4j")
        
        # Connection pool settings
        self.max_connection_lifetime = 3600  # 1 hour
        self.max_connection_pool_size = 50
        self.connection_acquisition_timeout = 60
        
        # Performance settings
        self.fetch_size = 1000
        self.batch_size = 500
        
        # Retry settings
        self.max_retry_time = 30
        self.max_retries = 3


class Neo4jConnection:
    """Managed Neo4j connection with pooling and health checks"""
    
    def __init__(self, config: Neo4jConfig):
        self.config = config
        self._driver: Optional[AsyncDriver] = None
        self._health_check_interval = 30  # seconds
        self._last_health_check = datetime.now()
        self._connection_lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize connection with retry logic"""
        async with self._connection_lock:
            if not self._driver:
                await self._create_driver()
                await self._setup_indexes()
    
    @backoff.on_exception(
        backoff.expo,
        (ServiceUnavailable, ConnectionError),
        max_time=30
    )
    async def _create_driver(self):
        """Create Neo4j driver with retry"""
        try:
            self._driver = AsyncGraphDatabase.driver(
                self.config.uri,
                auth=(self.config.username, self.config.password),
                max_connection_lifetime=self.config.max_connection_lifetime,
                max_connection_pool_size=self.config.max_connection_pool_size,
                connection_acquisition_timeout=self.config.connection_acquisition_timeout,
                fetch_size=self.config.fetch_size
            )
            
            # Verify connectivity
            await self._driver.verify_connectivity()
            logger.info("Neo4j connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    async def _setup_indexes(self):
        """Create indexes for optimal performance"""
        indexes = [
            # User indexes
            "CREATE INDEX user_id IF NOT EXISTS FOR (u:User) ON (u.user_id)",
            "CREATE INDEX user_email IF NOT EXISTS FOR (u:User) ON (u.email)",
            
            # Product indexes
            "CREATE INDEX product_sku IF NOT EXISTS FOR (p:Product) ON (p.sku)",
            "CREATE INDEX product_name IF NOT EXISTS FOR (p:Product) ON (p.name)",
            "CREATE INDEX product_category IF NOT EXISTS FOR (p:Product) ON (p.category)",
            
            # Order indexes
            "CREATE INDEX order_id IF NOT EXISTS FOR (o:Order) ON (o.order_id)",
            "CREATE INDEX order_timestamp IF NOT EXISTS FOR (o:Order) ON (o.timestamp)",
            
            # Event indexes
            "CREATE INDEX event_timestamp IF NOT EXISTS FOR (e:Event) ON (e.timestamp)",
            "CREATE INDEX event_type IF NOT EXISTS FOR (e:Event) ON (e.event_type)",
            
            # Full-text search indexes
            "CREATE FULLTEXT INDEX product_search IF NOT EXISTS FOR (p:Product) ON EACH [p.name, p.description, p.brand]",
            
            # Composite indexes for common queries
            "CREATE INDEX user_order_composite IF NOT EXISTS FOR (u:User) ON (u.user_id, u.last_order_date)",
            "CREATE INDEX product_price_composite IF NOT EXISTS FOR (p:Product) ON (p.category, p.price)"
        ]
        
        async with self.session() as session:
            for index_query in indexes:
                try:
                    await session.run(index_query)
                    logger.info(f"Index created/verified: {index_query.split(' ')[2]}")
                except Exception as e:
                    logger.warning(f"Index creation warning: {e}")
    
    @asynccontextmanager
    async def session(self):
        """Get a Neo4j session with automatic cleanup"""
        if not self._driver:
            await self.initialize()
        
        session = self._driver.session(database=self.config.database)
        try:
            yield session
        finally:
            await session.close()
    
    async def health_check(self) -> bool:
        """Perform health check on connection"""
        try:
            async with self.session() as session:
                result = await session.run("RETURN 1 as health")
                record = await result.single()
                return record["health"] == 1
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def close(self):
        """Close the driver connection"""
        if self._driver:
            await self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed")
    
    async def execute_query(
        self, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute a read query with retry logic"""
        parameters = parameters or {}
        
        @backoff.on_exception(
            backoff.expo,
            (ServiceUnavailable, SessionExpired),
            max_tries=self.config.max_retries
        )
        async def _execute():
            async with self.session() as session:
                result = await session.run(query, parameters)
                return [dict(record) async for record in result]
        
        return await _execute()
    
    async def execute_write(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a write query with transaction"""
        parameters = parameters or {}
        
        async def _write_transaction(tx, query, parameters):
            result = await tx.run(query, parameters)
            summary = result.consume()
            return {
                "nodes_created": (await summary).counters.nodes_created,
                "relationships_created": (await summary).counters.relationships_created,
                "properties_set": (await summary).counters.properties_set
            }
        
        async with self.session() as session:
            return await session.execute_write(
                _write_transaction, query, parameters
            )
    
    async def batch_write(
        self,
        queries: List[Tuple[str, Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Execute multiple write queries in a single transaction"""
        async def _batch_transaction(tx):
            results = []
            for query, params in queries:
                result = await tx.run(query, params)
                summary = result.consume()
                results.append({
                    "query": query[:50] + "...",
                    "nodes_created": (await summary).counters.nodes_created,
                    "relationships_created": (await summary).counters.relationships_created
                })
            return results
        
        async with self.session() as session:
            return await session.execute_write(_batch_transaction)


class GraphitiNeo4j:
    """High-level Neo4j interface for Graphiti operations"""
    
    def __init__(self):
        self.config = Neo4jConfig()
        self.connection = Neo4jConnection(self.config)
        
    async def initialize(self):
        """Initialize the connection"""
        await self.connection.initialize()
    
    async def create_user(self, user_data: Dict[str, Any]) -> str:
        """Create a user node"""
        query = """
        CREATE (u:User {
            user_id: $user_id,
            email: $email,
            name: $name,
            created_at: datetime(),
            preferences: $preferences,
            shopping_pattern: $shopping_pattern
        })
        RETURN u.user_id as user_id
        """
        
        result = await self.connection.execute_write(query, user_data)
        return user_data["user_id"]
    
    async def create_product(self, product_data: Dict[str, Any]) -> str:
        """Create a product node with rich attributes"""
        query = """
        MERGE (p:Product {sku: $sku})
        SET p += {
            name: $name,
            category: $category,
            subcategory: $subcategory,
            brand: $brand,
            price: $price,
            unit: $unit,
            description: $description,
            tags: $tags,
            updated_at: datetime()
        }
        RETURN p.sku as sku
        """
        
        result = await self.connection.execute_write(query, product_data)
        return product_data["sku"]
    
    async def create_order(self, order_data: Dict[str, Any]) -> str:
        """Create an order with relationships to user and products"""
        # Create order node
        create_order_query = """
        CREATE (o:Order {
            order_id: $order_id,
            user_id: $user_id,
            timestamp: datetime($timestamp),
            total_amount: $total_amount,
            item_count: $item_count,
            order_type: $order_type,
            metadata: $metadata
        })
        
        WITH o
        MATCH (u:User {user_id: $user_id})
        CREATE (u)-[:PLACED]->(o)
        
        RETURN o.order_id as order_id
        """
        
        # Link products to order
        link_products_query = """
        MATCH (o:Order {order_id: $order_id})
        MATCH (p:Product {sku: $sku})
        CREATE (o)-[c:CONTAINS {
            quantity: $quantity,
            price: $price,
            total: $total
        }]->(p)
        """
        
        # Execute in transaction
        queries = [(create_order_query, order_data)]
        
        for item in order_data.get("items", []):
            queries.append((link_products_query, {
                "order_id": order_data["order_id"],
                "sku": item["sku"],
                "quantity": item["quantity"],
                "price": item["price"],
                "total": item["total"]
            }))
        
        results = await self.connection.batch_write(queries)
        return order_data["order_id"]
    
    async def create_relationship(
        self,
        from_node: Tuple[str, str, str],  # (label, property, value)
        to_node: Tuple[str, str, str],
        relationship: str,
        properties: Optional[Dict[str, Any]] = None
    ):
        """Create a relationship between two nodes"""
        properties = properties or {}
        
        query = f"""
        MATCH (a:{from_node[0]} {{{from_node[1]}: ${from_node[1]}}})
        MATCH (b:{to_node[0]} {{{to_node[1]}: ${to_node[1]}}})
        CREATE (a)-[r:{relationship} $properties]->(b)
        RETURN id(r) as relationship_id
        """
        
        params = {
            from_node[1]: from_node[2],
            to_node[1]: to_node[2],
            "properties": properties
        }
        
        return await self.connection.execute_write(query, params)
    
    async def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user context from graph"""
        query = """
        MATCH (u:User {user_id: $user_id})
        
        // Get recent orders
        OPTIONAL MATCH (u)-[:PLACED]->(o:Order)
        WHERE o.timestamp > datetime() - duration('P90D')
        
        // Get frequently ordered products
        OPTIONAL MATCH (o)-[c:CONTAINS]->(p:Product)
        
        // Get product relationships
        OPTIONAL MATCH (p)-[:BOUGHT_WITH]-(related:Product)
        
        RETURN u as user,
               collect(DISTINCT o) as recent_orders,
               collect(DISTINCT {
                   product: p,
                   order_count: count(DISTINCT o),
                   total_quantity: sum(c.quantity)
               }) as frequent_products,
               collect(DISTINCT related) as related_products
        """
        
        result = await self.connection.execute_query(query, {"user_id": user_id})
        return result[0] if result else {}
    
    async def find_reorder_patterns(self, user_id: str) -> List[Dict[str, Any]]:
        """Find reorder patterns for a user"""
        query = """
        MATCH (u:User {user_id: $user_id})-[:PLACED]->(o:Order)-[c:CONTAINS]->(p:Product)
        WITH p, collect(o.timestamp) as order_times
        WHERE size(order_times) > 1
        
        // Calculate average days between orders
        WITH p, order_times,
             [i in range(0, size(order_times)-1) | 
                duration.inDays(order_times[i], order_times[i+1]).days] as intervals
        
        RETURN p.sku as sku,
               p.name as product_name,
               size(order_times) as order_count,
               avg(intervals) as avg_days_between_orders,
               min(intervals) as min_days,
               max(intervals) as max_days,
               order_times[-1] as last_ordered
        ORDER BY order_count DESC
        """
        
        return await self.connection.execute_query(query, {"user_id": user_id})
    
    async def close(self):
        """Close the connection"""
        await self.connection.close()


# Singleton instance
_graphiti_neo4j: Optional[GraphitiNeo4j] = None


async def get_graphiti_neo4j() -> GraphitiNeo4j:
    """Get or create the singleton Graphiti Neo4j instance"""
    global _graphiti_neo4j
    
    if _graphiti_neo4j is None:
        _graphiti_neo4j = GraphitiNeo4j()
        await _graphiti_neo4j.initialize()
    
    return _graphiti_neo4j