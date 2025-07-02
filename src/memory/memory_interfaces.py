"""
Memory interfaces and protocols for LeafLoaf

This module defines the interfaces for memory management,
enabling better testing and multiple backend support.
"""

from typing import Dict, Optional, Any, List, Protocol
from abc import ABC, abstractmethod
from datetime import datetime


class GraphMemoryProtocol(Protocol):
    """Protocol for graph memory implementations (Spanner, Neo4j, etc.)"""
    
    async def initialize(self) -> None:
        """Initialize the graph memory backend"""
        ...
    
    async def process_message(
        self, 
        message: str, 
        role: str = "human",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a message and extract entities/relationships"""
        ...
    
    async def get_context(self, query: str) -> Dict[str, Any]:
        """Get relevant context for a query"""
        ...
    
    async def get_user_patterns(self, user_id: str) -> Dict[str, Any]:
        """Get user behavior patterns"""
        ...
    
    async def add_order(self, order_data: Dict[str, Any]) -> str:
        """Add an order to the graph"""
        ...
    
    async def close(self) -> None:
        """Close connections and cleanup"""
        ...


class SessionMemoryProtocol(Protocol):
    """Protocol for session memory implementations"""
    
    def get_memory(self, session_id: str) -> Any:
        """Get memory for a session"""
        ...
    
    def add_message(self, session_id: str, role: str, content: str) -> None:
        """Add a message to session history"""
        ...
    
    def get_messages(self, session_id: str, limit: int = -1) -> List[Dict[str, Any]]:
        """Get message history for a session"""
        ...
    
    def clear_session(self, session_id: str) -> None:
        """Clear session memory"""
        ...


class MemoryManagerInterface(ABC):
    """Abstract interface for memory management"""
    
    @abstractmethod
    async def get_session_memory(self, session_id: str) -> SessionMemoryProtocol:
        """Get session memory instance"""
        pass
    
    @abstractmethod
    async def get_graph_memory(
        self, 
        user_id: str, 
        session_id: str
    ) -> Optional[GraphMemoryProtocol]:
        """Get graph memory instance for a user"""
        pass
    
    @abstractmethod
    async def process_message_with_graph(
        self,
        user_id: str,
        session_id: str,
        message: str,
        role: str = "human",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a message through graph memory"""
        pass
    
    @abstractmethod
    async def get_graph_context(
        self,
        user_id: str,
        session_id: str,
        query: str
    ) -> Dict[str, Any]:
        """Get graph context for a query"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup all resources"""
        pass


class MemoryBackend:
    """Enum for supported memory backends"""
    SPANNER = "spanner"
    NEO4J = "neo4j"
    IN_MEMORY = "in_memory"