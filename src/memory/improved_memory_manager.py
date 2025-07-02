"""
Improved memory manager with thread safety and dependency injection

This replaces the old singleton pattern with a more robust implementation
that supports testing, multiple backends, and proper resource management.
"""

import threading
import logging
from typing import Dict, Optional, Any, Callable
from weakref import WeakValueDictionary

from src.memory.memory_interfaces import (
    MemoryManagerInterface,
    GraphMemoryProtocol,
    SessionMemoryProtocol,
    MemoryBackend
)
from src.memory.session_memory import SessionMemory

logger = logging.getLogger(__name__)


class ImprovedMemoryManager(MemoryManagerInterface):
    """
    Thread-safe memory manager with dependency injection
    
    Features:
    - Thread-safe singleton pattern
    - Dependency injection for testing
    - Support for multiple graph backends
    - Proper async resource management
    - Weak references to prevent memory leaks
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """Thread-safe singleton creation"""
        if not cls._instance:
            with cls._lock:
                # Double-check locking pattern
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(
        self,
        session_memory_factory: Optional[Callable] = None,
        graph_memory_factory: Optional[Callable] = None,
        graph_backend: str = MemoryBackend.SPANNER,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize memory manager
        
        Args:
            session_memory_factory: Factory for creating session memory
            graph_memory_factory: Factory for creating graph memory
            graph_backend: Backend to use for graph memory (spanner/neo4j)
            config: Additional configuration
        """
        # Only initialize once
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._session_memory_factory = session_memory_factory or self._create_session_memory
        self._graph_memory_factory = graph_memory_factory or self._create_graph_memory
        self._graph_backend = graph_backend
        self._config = config or {}
        
        # Use WeakValueDictionary to prevent memory leaks
        self._session_memories: WeakValueDictionary = WeakValueDictionary()
        self._graph_memories: Dict[str, GraphMemoryProtocol] = {}
        
        # Lock for thread-safe operations
        self._operation_lock = threading.RLock()
        
        self._initialized = True
        
        logger.info(f"MemoryManager initialized with backend: {graph_backend}")
    
    def _create_session_memory(self, session_id: str) -> SessionMemoryProtocol:
        """Default factory for session memory"""
        return SessionMemory()
    
    async def _create_graph_memory(
        self, 
        user_id: str, 
        session_id: str
    ) -> GraphMemoryProtocol:
        """
        Default factory for graph memory
        
        Creates appropriate backend based on configuration
        """
        if self._graph_backend == MemoryBackend.SPANNER:
            # Use the new Graphiti implementation with Spanner
            from src.memory.graphiti_memory_spanner import GraphitiMemorySpanner
            
            memory = GraphitiMemorySpanner(user_id, session_id)
            await memory.initialize()
            return memory
            
        elif self._graph_backend == MemoryBackend.NEO4J:
            # Fallback to existing implementation
            from src.memory.graphiti_memory import GraphitiMemory
            memory = GraphitiMemory(user_id, session_id)
            await memory.initialize()
            return memory
            
        else:
            # In-memory implementation for testing
            from src.memory.in_memory_graph import InMemoryGraphMemory
            memory = InMemoryGraphMemory(user_id, session_id)
            await memory.initialize()
            return memory
    
    async def get_session_memory(self, session_id: str) -> SessionMemoryProtocol:
        """Get or create session memory"""
        with self._operation_lock:
            if session_id not in self._session_memories:
                memory = self._session_memory_factory(session_id)
                self._session_memories[session_id] = memory
            return self._session_memories[session_id]
    
    async def get_graph_memory(
        self, 
        user_id: str, 
        session_id: str
    ) -> Optional[GraphMemoryProtocol]:
        """Get or create graph memory for a user"""
        try:
            with self._operation_lock:
                # Use user_id as key for persistent memory across sessions
                if user_id not in self._graph_memories:
                    logger.info(f"Creating new graph memory for user {user_id}")
                    memory = await self._graph_memory_factory(user_id, session_id)
                    self._graph_memories[user_id] = memory
                else:
                    # Update session ID for existing memory
                    memory = self._graph_memories[user_id]
                    if hasattr(memory, 'session_id'):
                        memory.session_id = session_id
                
                return memory
                
        except Exception as e:
            logger.error(f"Failed to get graph memory: {e}")
            return None
    
    async def process_message_with_graph(
        self,
        user_id: str,
        session_id: str,
        message: str,
        role: str = "human",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a message through graph memory if available"""
        graph_memory = await self.get_graph_memory(user_id, session_id)
        
        if graph_memory:
            try:
                return await graph_memory.process_message(message, role, metadata)
            except Exception as e:
                logger.error(f"Graph processing failed: {e}")
        
        # Return empty result if graph memory unavailable
        return {
            "entities": [],
            "relationships": [],
            "entity_count": 0,
            "relationship_count": 0
        }
    
    async def get_graph_context(
        self,
        user_id: str,
        session_id: str,
        query: str
    ) -> Dict[str, Any]:
        """Get graph context for a query"""
        graph_memory = await self.get_graph_memory(user_id, session_id)
        
        if graph_memory:
            try:
                return await graph_memory.get_context(query)
            except Exception as e:
                logger.error(f"Failed to get graph context: {e}")
        
        # Return empty context if unavailable
        return {
            "user_context": {},
            "reorder_patterns": [],
            "session_context": {},
            "query_entities": [],
            "cached_entities": []
        }
    
    async def cleanup(self) -> None:
        """Clean up all resources"""
        logger.info("Cleaning up memory manager resources")
        
        # Clean up graph memories
        for user_id, memory in list(self._graph_memories.items()):
            try:
                await memory.close()
            except Exception as e:
                logger.error(f"Error closing graph memory for user {user_id}: {e}")
        
        self._graph_memories.clear()
        self._session_memories.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory manager statistics"""
        return {
            "session_memories": len(self._session_memories),
            "graph_memories": len(self._graph_memories),
            "backend": self._graph_backend,
            "initialized": self._initialized
        }


class ManagedMemoryManager(ImprovedMemoryManager):
    """Memory manager with async context manager support"""
    
    # Override __new__ to return the correct type
    def __new__(cls, *args, **kwargs):
        """Create a new instance without singleton behavior"""
        # Don't use the parent's singleton pattern
        instance = object.__new__(cls)
        return instance
    
    async def __aenter__(self):
        """Async context manager entry"""
        logger.info("Entering managed memory context")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        logger.info("Exiting managed memory context")
        await self.cleanup()
        return False  # Don't suppress exceptions