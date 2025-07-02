"""
Migration utilities for transitioning to the improved memory manager

This module provides backward compatibility while migrating
to the new thread-safe, testable memory management system.
"""

import logging
import os
from typing import Optional, Dict, Any

from src.memory.memory_registry import MemoryRegistry
from src.memory.memory_interfaces import MemoryBackend
from src.memory.improved_memory_manager import ImprovedMemoryManager

logger = logging.getLogger(__name__)


class LegacyMemoryManagerAdapter:
    """
    Adapter that provides the old MemoryManager interface
    while using the new improved implementation underneath
    """
    
    def __init__(self):
        # Determine backend from environment
        backend = MemoryBackend.SPANNER
        if os.getenv("USE_NEO4J", "false").lower() == "true":
            backend = MemoryBackend.NEO4J
        
        # Get or create the default manager
        self._manager = MemoryRegistry.get_or_create(
            "default",
            config={"backend": backend}
        )
        
        logger.info(f"Legacy adapter using backend: {backend}")
    
    @property
    def session_memory(self):
        """Get the shared session memory instance (legacy interface)"""
        # Return a compatibility wrapper
        return LegacySessionMemoryWrapper(self._manager)
    
    def get_memory(self, session_id: str):
        """Get session memory for backward compatibility"""
        # This returns the actual session memory synchronously
        # Note: This is a simplified approach for compatibility
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            # If we're already in an async context, we can't use run_until_complete
            # Return a simple wrapper instead
            return LegacySessionMemoryWrapper(self._manager, session_id)
        else:
            return loop.run_until_complete(
                self._manager.get_session_memory(session_id)
            )
    
    async def get_graphiti_memory(
        self, 
        user_id: str, 
        session_id: str
    ) -> Optional[Any]:
        """Get or create Graphiti memory for a user (legacy name)"""
        return await self._manager.get_graph_memory(user_id, session_id)
    
    async def process_message_with_graphiti(
        self,
        user_id: str,
        session_id: str,
        message: str,
        role: str = "human",
        metadata: Optional[Dict] = None
    ) -> Dict:
        """Process a message through Graphiti (legacy name)"""
        return await self._manager.process_message_with_graph(
            user_id, session_id, message, role, metadata
        )
    
    async def get_graphiti_context(
        self,
        user_id: str,
        session_id: str,
        query: str
    ) -> Dict:
        """Get Graphiti context for a query (legacy name)"""
        return await self._manager.get_graph_context(
            user_id, session_id, query
        )
    
    async def cleanup(self):
        """Clean up resources"""
        await self._manager.cleanup()


class LegacySessionMemoryWrapper:
    """Wrapper to provide legacy session memory interface"""
    
    def __init__(self, manager: ImprovedMemoryManager, session_id: Optional[str] = None):
        self._manager = manager
        self._session_id = session_id
    
    def get_memory(self, session_id: str):
        """Get memory for a session"""
        import asyncio
        
        async def _get():
            return await self._manager.get_session_memory(session_id)
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Return a proxy object that will handle async calls
                return SessionMemoryProxy(self._manager, session_id)
            else:
                return loop.run_until_complete(_get())
        except:
            # Fallback
            return SessionMemoryProxy(self._manager, session_id)
    
    async def get_user_context(self, session_id: str) -> Optional[Dict]:
        """Get user context from session"""
        memory = await self._manager.get_session_memory(session_id)
        if hasattr(memory, 'get_user_context'):
            return memory.get_user_context()
        return None
    
    async def get_recent_search_results(self, session_id: str) -> list:
        """Get recent search results"""
        memory = await self._manager.get_session_memory(session_id)
        if hasattr(memory, 'get_recent_search_results'):
            return memory.get_recent_search_results()
        return []
    
    async def add_search_results(self, session_id: str, query: str, results: list):
        """Add search results to memory"""
        memory = await self._manager.get_session_memory(session_id)
        if hasattr(memory, 'add_search_results'):
            memory.add_search_results(query, results)


class SessionMemoryProxy:
    """Proxy for handling async session memory calls in sync context"""
    
    def __init__(self, manager: ImprovedMemoryManager, session_id: str):
        self._manager = manager
        self._session_id = session_id
        self._cache = {}
    
    def __getattr__(self, name):
        """Proxy attribute access"""
        # This is a simplified implementation
        # In production, you'd want more sophisticated async handling
        def method(*args, **kwargs):
            logger.warning(
                f"SessionMemoryProxy: Synchronous call to {name} - "
                "consider updating to async"
            )
            # Return cached or default values for common methods
            if name == "get_messages":
                return self._cache.get("messages", [])
            elif name == "add_message":
                if "messages" not in self._cache:
                    self._cache["messages"] = []
                self._cache["messages"].append({
                    "role": args[0] if args else "user",
                    "content": args[1] if len(args) > 1 else ""
                })
                return None
            else:
                return None
        
        return method


def migrate_to_improved_memory():
    """
    Migrate existing code to use improved memory manager
    
    This function sets up the compatibility layer
    """
    logger.info("Migrating to improved memory manager")
    
    # Register the default manager with appropriate backend
    backend = MemoryBackend.SPANNER
    if os.getenv("USE_NEO4J", "false").lower() == "true":
        backend = MemoryBackend.NEO4J
    
    config = {
        "backend": backend,
        "spanner": {
            "project_id": os.getenv("GCP_PROJECT_ID", "leafloafai"),
            "instance_id": os.getenv("SPANNER_INSTANCE_ID", "leafloaf-graph"),
            "database_id": os.getenv("SPANNER_DATABASE_ID", "leafloaf-graphrag")
        }
    }
    
    MemoryRegistry.register("default", config=config)
    
    logger.info(f"Memory manager migrated with backend: {backend}")


# Create a singleton instance that mimics the old interface
memory_manager = LegacyMemoryManagerAdapter()

# This allows existing code to work:
# from src.memory.migrate_memory_manager import memory_manager