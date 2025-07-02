"""
Production Graphiti Memory with Vertex AI and Spanner

This is the REAL production implementation that uses:
- Vertex AI for embeddings and entity extraction
- Spanner for graph storage
- Proper async patterns
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import uuid
import json

from graphiti_core import Graphiti
from graphiti_core.adapters import SpannerAdapter
from graphiti_core.llm_client import LLMClient
from graphiti_core.embedder import EmbedderClient

from langchain_google_vertexai import VertexAI, VertexAIEmbeddings
from google.cloud import spanner

logger = logging.getLogger(__name__)


class VertexAILLMClient(LLMClient):
    """Vertex AI implementation for Graphiti's LLM interface"""
    
    def __init__(self, model_name: str = "gemini-1.5-flash"):
        self.llm = VertexAI(
            model_name=model_name,
            temperature=0,
            max_output_tokens=2048,
            project="leafloafai",
            location="us-central1"
        )
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """Generate response from Vertex AI"""
        # Convert messages to prompt
        prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        
        # Use async invoke
        response = await self.llm.ainvoke(prompt)
        return response


class VertexAIEmbedderClient(EmbedderClient):
    """Vertex AI implementation for Graphiti's embedder interface"""
    
    def __init__(self, model_name: str = "text-embedding-004"):
        self.embedder = VertexAIEmbeddings(
            model_name=model_name,
            project="leafloafai",
            location="us-central1"
        )
    
    async def create(self, text: str) -> List[float]:
        """Create embeddings using Vertex AI"""
        embeddings = await self.embedder.aembed_query(text)
        return embeddings


class GraphitiVertexAI:
    """
    Production Graphiti implementation with Vertex AI and Spanner
    """
    
    def __init__(self, user_id: str, session_id: str):
        self.user_id = user_id
        self.session_id = session_id
        self.namespace = f"{user_id}:{session_id}"
        self._graphiti = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize Graphiti with Vertex AI and Spanner"""
        if self._initialized:
            return
            
        try:
            # Initialize Spanner adapter
            spanner_client = spanner.Client(project="leafloafai")
            instance = spanner_client.instance("leafloaf-graphiti")
            database = instance.database("graphiti-memory")
            
            adapter = SpannerAdapter(
                database=database,
                namespace=self.namespace
            )
            
            # Initialize Vertex AI clients
            llm_client = VertexAILLMClient()
            embedder_client = VertexAIEmbedderClient()
            
            # Create Graphiti instance
            self._graphiti = Graphiti(
                adapter=adapter,
                llm_client=llm_client,
                embedder_client=embedder_client,
                config={
                    "entity_extraction": {
                        "enabled": True,
                        "confidence_threshold": 0.7
                    },
                    "relationship_extraction": {
                        "enabled": True,
                        "confidence_threshold": 0.6
                    },
                    "summarization": {
                        "enabled": True,
                        "max_summary_length": 200
                    }
                }
            )
            
            await self._graphiti.initialize()
            self._initialized = True
            logger.info(f"Initialized Graphiti for {self.namespace} with Vertex AI")
            
        except Exception as e:
            logger.error(f"Failed to initialize Graphiti: {e}")
            raise
    
    async def process_message(
        self,
        message: str,
        role: str = "user",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a message and extract entities/relationships"""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Add episode to Graphiti
            episode_id = str(uuid.uuid4())
            episode_metadata = {
                "user_id": self.user_id,
                "session_id": self.session_id,
                "role": role,
                "timestamp": datetime.utcnow().isoformat(),
                **(metadata or {})
            }
            
            # Process with Graphiti
            result = await self._graphiti.add_episode(
                content=message,
                episode_id=episode_id,
                metadata=episode_metadata
            )
            
            # Extract entities and relationships from result
            entities = []
            relationships = []
            
            if hasattr(result, 'entities'):
                for entity in result.entities:
                    entities.append({
                        "id": entity.id,
                        "name": entity.name,
                        "type": entity.type,
                        "properties": entity.properties
                    })
            
            if hasattr(result, 'relationships'):
                for rel in result.relationships:
                    relationships.append({
                        "source": rel.source_id,
                        "target": rel.target_id,
                        "type": rel.type,
                        "properties": rel.properties
                    })
            
            logger.info(f"Processed message: {len(entities)} entities, {len(relationships)} relationships")
            
            return {
                "entities": entities,
                "relationships": relationships,
                "episode_id": episode_id,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            return {
                "entities": [],
                "relationships": [],
                "error": str(e),
                "success": False
            }
    
    async def get_context(
        self,
        query: str,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """Get relevant context for a query"""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Search Graphiti for relevant context
            results = await self._graphiti.search(
                query=query,
                namespace=self.namespace,
                max_results=max_results
            )
            
            # Format results
            context = {
                "user_context": {
                    "user_id": self.user_id,
                    "session_id": self.session_id,
                    "preferences": [],
                    "recent_orders": []
                },
                "query_entities": [],
                "reorder_patterns": []
            }
            
            # Extract relevant information from search results
            if results:
                for result in results:
                    if result.type == "preference":
                        context["user_context"]["preferences"].append(result.content)
                    elif result.type == "order":
                        context["user_context"]["recent_orders"].append(result.content)
                    elif result.type == "entity":
                        context["query_entities"].append({
                            "name": result.name,
                            "type": result.entity_type,
                            "relevance": result.score
                        })
                    elif result.type == "pattern":
                        context["reorder_patterns"].append({
                            "product": result.product,
                            "frequency": result.frequency,
                            "last_ordered": result.last_ordered
                        })
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to get context: {e}")
            return {
                "user_context": {"user_id": self.user_id, "session_id": self.session_id},
                "query_entities": [],
                "reorder_patterns": []
            }
    
    async def close(self):
        """Clean up resources"""
        if self._graphiti:
            await self._graphiti.close()
            self._initialized = False