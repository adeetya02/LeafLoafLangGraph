"""
Spanner Graph Client for LeafLoaf - GCP Native Solution

This provides a GraphRAG implementation using:
- Spanner Graph (GCP's native graph database)
- Vertex AI (for LLM operations)
- LangChain (for orchestration)

Benefits:
- Fully GCP native (no external dependencies)
- Integrated with Vertex AI
- Lower cost than Neo4j
- Enterprise-grade scalability
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from google.cloud import spanner
from google.cloud.spanner_v1 import param_types
import vertexai
from vertexai.language_models import TextEmbeddingModel
from vertexai.generative_models import GenerativeModel
from langchain_google_vertexai import VertexAI, VertexAIEmbeddings
from langchain_google_spanner import SpannerGraphStore, SpannerGraphTextToGQLRetriever
# from langchain.chains import GraphCypherQAChain  # Not needed with new approach

logger = logging.getLogger(__name__)


class SpannerGraphClient:
    """
    GCP-native GraphRAG implementation using Spanner Graph + Vertex AI
    
    This replaces Neo4j/Graphiti with a fully integrated GCP solution
    that's more cost-effective and has better Vertex AI integration.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        
        # GCP Configuration
        self.project_id = config.get("project_id") or os.getenv("GCP_PROJECT_ID", "leafloafai")
        self.instance_id = config.get("instance_id") or os.getenv("SPANNER_INSTANCE_ID", "leafloaf-graph")
        self.database_id = config.get("database_id") or os.getenv("SPANNER_DATABASE_ID", "leafloaf-graphrag")
        self.location = config.get("location") or os.getenv("GCP_LOCATION", "us-central1")
        
        # Initialize Vertex AI
        vertexai.init(project=self.project_id, location=self.location)
        
        # Initialize models
        self.llm = VertexAI(
            model_name="gemini-1.5-pro",
            max_output_tokens=2048,
            temperature=0.1,
            project=self.project_id,
            location=self.location
        )
        
        self.embeddings = VertexAIEmbeddings(
            model_name="text-embedding-004",
            project=self.project_id,
            location=self.location
        )
        
        # Spanner client
        self.spanner_client = spanner.Client(project=self.project_id)
        self.instance = self.spanner_client.instance(self.instance_id)
        self.database = self.instance.database(self.database_id)
        
        # Graph components
        self.graph = None
        self.graph_qa_chain = None
        
        self._initialized = False
    
    async def initialize(self):
        """Initialize Spanner Graph database and create schema"""
        try:
            # Create or get database
            if not self.database.exists():
                await self._create_database()
            
            # Initialize graph interface with correct import
            self.graph = SpannerGraphStore(
                instance_id=self.instance_id,
                database_id=self.database_id,
                graph_name="leafloaf_product_graph"  # Name for our graph
            )
            
            # Create GraphRAG retriever
            self.graph_qa_chain = SpannerGraphTextToGQLRetriever(
                graph_store=self.graph,
                llm=self.llm,
                verbose=True
            )
            
            # Create indexes for performance
            await self._create_indexes()
            
            self._initialized = True
            logger.info("Spanner Graph initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Spanner Graph: {e}")
            raise
    
    async def _create_database(self):
        """Create Spanner database with graph schema"""
        # Define schema with graph tables
        ddl_statements = [
            # User nodes
            """CREATE TABLE Users (
                user_id STRING(36) NOT NULL,
                email STRING(255),
                name STRING(255),
                created_at TIMESTAMP NOT NULL OPTIONS (allow_commit_timestamp=true),
                preferences JSON,
                shopping_pattern STRING(50),
            ) PRIMARY KEY (user_id)""",
            
            # Product nodes
            """CREATE TABLE Products (
                sku STRING(50) NOT NULL,
                name STRING(255) NOT NULL,
                category STRING(100),
                subcategory STRING(100),
                brand STRING(100),
                price FLOAT64,
                unit STRING(50),
                description STRING(MAX),
                tags ARRAY<STRING(50)>,
                embedding ARRAY<FLOAT64>,
                updated_at TIMESTAMP OPTIONS (allow_commit_timestamp=true),
            ) PRIMARY KEY (sku)""",
            
            # Order nodes
            """CREATE TABLE Orders (
                order_id STRING(50) NOT NULL,
                user_id STRING(36) NOT NULL,
                order_timestamp TIMESTAMP NOT NULL,
                total_amount FLOAT64,
                item_count INT64,
                order_type STRING(50),
                metadata JSON,
                CONSTRAINT FK_Orders_Users FOREIGN KEY (user_id) REFERENCES Users (user_id),
            ) PRIMARY KEY (order_id)""",
            
            # Order-Product relationships (edges)
            """CREATE TABLE OrderItems (
                order_id STRING(50) NOT NULL,
                sku STRING(50) NOT NULL,
                quantity INT64,
                price FLOAT64,
                total FLOAT64,
                CONSTRAINT FK_OrderItems_Orders FOREIGN KEY (order_id) REFERENCES Orders (order_id),
                CONSTRAINT FK_OrderItems_Products FOREIGN KEY (sku) REFERENCES Products (sku),
            ) PRIMARY KEY (order_id, sku)""",
            
            # Product relationships (bought together)
            """CREATE TABLE ProductRelationships (
                product1_sku STRING(50) NOT NULL,
                product2_sku STRING(50) NOT NULL,
                relationship_type STRING(50),
                confidence FLOAT64,
                co_occurrence_count INT64,
                last_updated TIMESTAMP OPTIONS (allow_commit_timestamp=true),
                CONSTRAINT FK_PR_Product1 FOREIGN KEY (product1_sku) REFERENCES Products (sku),
                CONSTRAINT FK_PR_Product2 FOREIGN KEY (product2_sku) REFERENCES Products (sku),
            ) PRIMARY KEY (product1_sku, product2_sku)""",
            
            # Episodes (for GraphRAG context)
            """CREATE TABLE Episodes (
                episode_id STRING(36) NOT NULL,
                user_id STRING(36) NOT NULL,
                episode_type STRING(50),
                content STRING(MAX),
                entities JSON,
                relationships JSON,
                created_at TIMESTAMP NOT NULL OPTIONS (allow_commit_timestamp=true),
                metadata JSON,
                CONSTRAINT FK_Episodes_Users FOREIGN KEY (user_id) REFERENCES Users (user_id),
            ) PRIMARY KEY (episode_id)""",
            
            # Create graph view using GQL
            """CREATE OR REPLACE PROPERTY GRAPH UserShoppingGraph
            NODE TABLES (
                Users KEY (user_id),
                Products KEY (sku),
                Orders KEY (order_id)
            )
            EDGE TABLES (
                OrderItems KEY (order_id, sku) 
                    SOURCE Users REFERENCES Orders(order_id)
                    DESTINATION Products REFERENCES Products(sku),
                ProductRelationships KEY (product1_sku, product2_sku)
                    SOURCE Products REFERENCES Products(product1_sku)
                    DESTINATION Products REFERENCES Products(product2_sku)
            )"""
        ]
        
        operation = self.database.create(ddl_statements)
        await operation  # Wait for database creation
        logger.info("Created Spanner Graph database")
    
    async def _create_indexes(self):
        """Create indexes for optimal graph performance"""
        index_statements = [
            "CREATE INDEX idx_orders_user ON Orders(user_id)",
            "CREATE INDEX idx_orders_timestamp ON Orders(order_timestamp DESC)",
            "CREATE INDEX idx_products_category ON Products(category)",
            "CREATE INDEX idx_episodes_user ON Episodes(user_id)",
            "CREATE INDEX idx_episodes_type ON Episodes(episode_type)",
            "CREATE NULL_FILTERED INDEX idx_product_embedding ON Products(embedding)"
        ]
        
        with self.database.batch() as batch:
            for statement in index_statements:
                try:
                    batch.execute_update(statement)
                except Exception as e:
                    logger.debug(f"Index might already exist: {e}")
    
    async def add_user(self, user_data: Dict[str, Any]) -> str:
        """Add a user node to the graph"""
        with self.database.batch() as batch:
            batch.insert(
                table="Users",
                columns=["user_id", "email", "name", "created_at", "preferences", "shopping_pattern"],
                values=[(
                    user_data["user_id"],
                    user_data.get("email"),
                    user_data.get("name"),
                    spanner.COMMIT_TIMESTAMP,
                    json.dumps(user_data.get("preferences", {})),
                    user_data.get("shopping_pattern")
                )]
            )
        
        return user_data["user_id"]
    
    async def add_product(self, product_data: Dict[str, Any]) -> str:
        """Add a product node with embedding"""
        # Generate embedding for semantic search
        embedding = await self._generate_embedding(
            f"{product_data['name']} {product_data.get('brand', '')} {product_data.get('description', '')}"
        )
        
        with self.database.batch() as batch:
            batch.insert_or_update(
                table="Products",
                columns=["sku", "name", "category", "subcategory", "brand", "price", 
                        "unit", "description", "tags", "embedding", "updated_at"],
                values=[(
                    product_data["sku"],
                    product_data["name"],
                    product_data.get("category"),
                    product_data.get("subcategory"),
                    product_data.get("brand"),
                    product_data.get("price"),
                    product_data.get("unit"),
                    product_data.get("description"),
                    product_data.get("tags", []),
                    embedding,
                    spanner.COMMIT_TIMESTAMP
                )]
            )
        
        return product_data["sku"]
    
    async def add_order(self, order_data: Dict[str, Any]) -> str:
        """Add an order with items to the graph"""
        def _insert_order(transaction):
            # Insert order
            transaction.insert(
                table="Orders",
                columns=["order_id", "user_id", "order_timestamp", "total_amount", 
                        "item_count", "order_type", "metadata"],
                values=[(
                    order_data["order_id"],
                    order_data["user_id"],
                    datetime.fromisoformat(order_data["timestamp"].replace('Z', '+00:00')),
                    order_data["total_amount"],
                    order_data["item_count"],
                    order_data.get("order_type", "regular"),
                    json.dumps(order_data.get("metadata", {}))
                )]
            )
            
            # Insert order items
            for idx, item in enumerate(order_data.get("items", [])):
                item_total = item.get("quantity", 1) * item.get("price", 0.0)
                transaction.insert(
                    table="OrderItems",
                    columns=["order_id", "user_id", "sku", "quantity", "price", "total"],
                    values=[(
                        order_data["order_id"],
                        order_data["user_id"],
                        item.get("sku", f"UNKNOWN_{idx}"),
                        item.get("quantity", 1),
                        item.get("price", 0.0),
                        item_total
                    )]
                )
            
            # Update product relationships
            # TODO: Enable this after products are populated
            # self._update_product_relationships(transaction, order_data["items"])
        
        try:
            logger.info(f"Running Spanner transaction for order {order_data['order_id']}")
            self.database.run_in_transaction(_insert_order)
            logger.info(f"Spanner transaction completed for order {order_data['order_id']}")
        except Exception as e:
            logger.error(f"Spanner transaction failed: {e}")
            raise
        
        # Add as episode for GraphRAG
        await self.add_episode(
            user_id=order_data["user_id"],
            content=self._format_order_as_text(order_data),
            episode_type="order_placed",
            metadata={
                "order_id": order_data["order_id"],
                "total": order_data["total_amount"]
            }
        )
        
        return order_data["order_id"]
    
    def _update_product_relationships(self, transaction, items: List[Dict]):
        """Update product co-occurrence relationships"""
        # For each pair of products in the order
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                sku1, sku2 = sorted([items[i]["sku"], items[j]["sku"]])
                
                # Check if relationship exists
                result = transaction.execute_sql(
                    """SELECT co_occurrence_count FROM ProductRelationships 
                       WHERE product1_sku = @sku1 AND product2_sku = @sku2""",
                    params={"sku1": sku1, "sku2": sku2},
                    param_types={"sku1": param_types.STRING, "sku2": param_types.STRING}
                )
                
                row = list(result)
                if row:
                    # Update count
                    new_count = row[0][0] + 1
                    transaction.update(
                        table="ProductRelationships",
                        columns=["product1_sku", "product2_sku", "co_occurrence_count", "last_updated"],
                        values=[(sku1, sku2, new_count, spanner.COMMIT_TIMESTAMP)]
                    )
                else:
                    # Insert new relationship
                    transaction.insert(
                        table="ProductRelationships",
                        columns=["product1_sku", "product2_sku", "relationship_type", 
                                "confidence", "co_occurrence_count", "last_updated"],
                        values=[(sku1, sku2, "BOUGHT_WITH", 0.5, 1, spanner.COMMIT_TIMESTAMP)]
                    )
    
    async def add_episode(
        self,
        user_id: str,
        content: str,
        episode_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add an episode for GraphRAG context"""
        import uuid
        
        episode_id = str(uuid.uuid4())
        
        # Extract entities and relationships using Vertex AI
        entities, relationships = await self._extract_entities_relationships(content)
        
        with self.database.batch() as batch:
            batch.insert(
                table="Episodes",
                columns=["episode_id", "user_id", "episode_type", "content", 
                        "entities", "relationships", "created_at", "metadata"],
                values=[(
                    episode_id,
                    user_id,
                    episode_type,
                    content,
                    json.dumps(entities),
                    json.dumps(relationships),
                    spanner.COMMIT_TIMESTAMP,
                    json.dumps(metadata or {})
                )]
            )
        
        return episode_id
    
    async def graphrag_search(
        self,
        query: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Perform GraphRAG search using Spanner Graph + Vertex AI
        
        This combines:
        1. Graph traversal for relationships
        2. Vector similarity for semantic search
        3. LLM reasoning for answer generation
        """
        if not self._initialized:
            await self.initialize()
        
        # Use GQL for graph queries
        graph_query = f"""
        GRAPH UserShoppingGraph
        MATCH (u:Users {{user_id: '{user_id}'}})-[:PLACED]->(o:Orders)-[:CONTAINS]->(p:Products)
        WHERE o.order_timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
        RETURN p.name, p.sku, COUNT(o) as order_count
        ORDER BY order_count DESC
        LIMIT 10
        """
        
        # TODO: Execute GraphRAG chain when imports are fixed
        # result = await self.graph_qa_chain.arun(
        #     query=query,
        #     context={
        
        # For now, return empty result
        result = {
            "answer": "GraphRAG is temporarily disabled",
            "graph_context": {},
            "confidence": 0.0
        }
        return result
        
        # Original code continues below (commented out)
        """
                "user_id": user_id,
                "graph_query": graph_query
            }
        )
        
        return {
            "answer": result,
            "graph_context": self._get_graph_context(user_id),
            "confidence": 0.85
        }
        """
    
    async def get_reorder_patterns(self, user_id: str) -> List[Dict[str, Any]]:
        """Get reorder patterns using GQL"""
        query = """
        GRAPH UserShoppingGraph
        MATCH (u:Users {user_id: @user_id})-[:PLACED]->(o:Orders)-[c:CONTAINS]->(p:Products)
        WITH p, ARRAY_AGG(o.order_timestamp ORDER BY o.order_timestamp) as order_times
        WHERE ARRAY_LENGTH(order_times) >= 2
        RETURN 
            p.sku as sku,
            p.name as product_name,
            ARRAY_LENGTH(order_times) as order_count,
            order_times[ORDINAL(ARRAY_LENGTH(order_times))] as last_ordered
        ORDER BY order_count DESC
        """
        
        with self.database.snapshot() as snapshot:
            results = snapshot.execute_sql(
                query,
                params={"user_id": user_id},
                param_types={"user_id": param_types.STRING}
            )
            
            patterns = []
            for row in results:
                patterns.append({
                    "sku": row[0],
                    "product_name": row[1],
                    "order_count": row[2],
                    "last_ordered": row[3]
                })
            
            return patterns
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Vertex AI"""
        embeddings = self.embeddings.embed_documents([text])
        return embeddings[0] if embeddings else []
    
    async def _extract_entities_relationships(
        self, 
        text: str
    ) -> Tuple[Dict, Dict]:
        """Extract entities and relationships using Gemini"""
        prompt = f"""
Extract entities and relationships from this grocery shopping text:

{text}

Return JSON with:
- entities: list of {{type, name, properties}}
- relationships: list of {{source, target, type}}
"""
        
        response = await self.llm.agenerate([prompt])
        
        try:
            import json
            result = json.loads(response.generations[0][0].text)
            return result.get("entities", {}), result.get("relationships", {})
        except:
            return {}, {}
    
    def _format_order_as_text(self, order_data: Dict[str, Any]) -> str:
        """Format order as natural language"""
        items = order_data.get("items", [])
        text = f"Order {order_data['order_id']}:\n"
        
        for item in items:
            text += f"- {item['quantity']} {item.get('name', 'Unknown')} at ₹{item['price']}\n"
        
        text += f"Total: ₹{order_data['total_amount']}"
        return text
    
    def _get_graph_context(self, user_id: str) -> Dict[str, Any]:
        """Get graph context for a user"""
        # This would execute various graph queries
        # Simplified for example
        return {
            "total_orders": 0,
            "favorite_products": [],
            "shopping_pattern": "regular"
        }


# Cost comparison
"""
COST COMPARISON: Spanner Graph vs Neo4j on GCP

Spanner Graph (Pay-as-you-go):
- Nodes: $0.10/hour (~$72/month for 1 node)
- Storage: $0.30/GB/month
- Estimated for LeafLoaf: ~$100-150/month

Neo4j on GCP:
- VM: $80-120/month
- Managed AuraDB: $150-200/month
- Plus LLM costs for entity extraction

ADVANTAGES of Spanner Graph:
1. Native Vertex AI integration (no external LLM costs)
2. Built-in GraphRAG with LangChain
3. SQL + GQL in same database
4. Auto-scaling and managed
5. Integrated monitoring
6. IAM and VPC native
7. Can use committed use discounts (20-30% off)

TOTAL SAVINGS: ~30-50% compared to Neo4j solution
"""