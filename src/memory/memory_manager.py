"""
Singleton memory manager to ensure all agents share the same session memory instance
Enhanced with Graphiti for intelligent memory and pattern recognition
"""

import logging
from typing import Dict, Optional, Any
from src.memory.session_memory import SessionMemory
# from src.memory.graphiti_memory import GraphitiMemory  # Import when needed to avoid circular

logger = logging.getLogger(__name__)


class MemoryManager:
    """Singleton memory manager with Graphiti integration"""
    _instance = None
    _session_memory = None
    _graphiti_memories: Dict[str, Any] = {}  # Type will be GraphitiMemory
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MemoryManager, cls).__new__(cls)
            cls._session_memory = SessionMemory()
            cls._graphiti_memories = {}
        return cls._instance
    
    @property
    def session_memory(self):
        """Get the shared session memory instance"""
        return self._session_memory
    
    def get_memory(self, session_id: str):
        """Get session memory for backward compatibility"""
        return self._session_memory.get_memory(session_id)
    
    async def get_graphiti_memory(
        self, 
        user_id: str, 
        session_id: str
    ) -> Optional[Any]:  # Will return GraphitiMemory
        """Get or create Graphiti memory for a user"""
        try:
            # Import here to avoid circular dependency
            from src.memory.graphiti_memory import GraphitiMemory
            
            # Use user_id as key for persistent memory across sessions
            if user_id not in self._graphiti_memories:
                logger.info(f"Creating new Graphiti memory for user {user_id}")
                memory = GraphitiMemory(user_id, session_id)
                await memory.initialize()
                self._graphiti_memories[user_id] = memory
            else:
                # Update session ID for existing memory
                self._graphiti_memories[user_id].session_id = session_id
                
            return self._graphiti_memories[user_id]
            
        except Exception as e:
            logger.error(f"Failed to initialize Graphiti memory: {e}")
            # Graceful fallback - return None if Graphiti unavailable
            return None
    
    async def process_message_with_graphiti(
        self,
        user_id: str,
        session_id: str,
        message: str,
        role: str = "human",
        metadata: Optional[Dict] = None
    ) -> Dict:
        """Process a message through Graphiti if available"""
        graphiti = await self.get_graphiti_memory(user_id, session_id)
        
        if graphiti:
            try:
                return await graphiti.process_message(message, role, metadata)
            except Exception as e:
                logger.error(f"Graphiti processing failed: {e}")
        
        # Return empty result if Graphiti unavailable
        return {
            "entities": [],
            "relationships": [],
            "entity_count": 0,
            "relationship_count": 0
        }
    
    async def get_graphiti_context(
        self,
        user_id: str,
        session_id: str,
        query: str
    ) -> Dict:
        """Get Graphiti context for a query"""
        graphiti = await self.get_graphiti_memory(user_id, session_id)
        
        if graphiti:
            try:
                return await graphiti.get_context(query)
            except Exception as e:
                logger.error(f"Failed to get Graphiti context: {e}")
        
        # Return empty context if unavailable
        return {
            "user_context": {},
            "reorder_patterns": [],
            "session_context": {},
            "query_entities": [],
            "cached_entities": []
        }
    
    async def cleanup(self):
        """Clean up resources"""
        for memory in self._graphiti_memories.values():
            try:
                await memory.close()
            except Exception as e:
                logger.error(f"Error closing Graphiti memory: {e}")
        
        self._graphiti_memories.clear()

# Global memory manager instance
memory_manager = MemoryManager()