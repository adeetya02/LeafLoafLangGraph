"""
Memory Registry for managing memory instances

This provides a better alternative to global singletons,
allowing for multiple named instances and easier testing.
"""

import logging
from typing import Dict, Optional, Any
from threading import RLock

from src.memory.memory_interfaces import MemoryManagerInterface, MemoryBackend
from src.memory.improved_memory_manager import ImprovedMemoryManager, ManagedMemoryManager
from src.memory.graphiti_memory import GraphitiMemory
from src.memory.graphiti_wrapper import GraphitiMemoryWrapper

logger = logging.getLogger(__name__)


class MemoryRegistry:
    """
    Registry for memory managers
    
    This allows for:
    - Multiple named memory manager instances
    - Easy testing with isolated instances
    - Configuration per instance
    - Graceful cleanup
    """
    
    _managers: Dict[str, MemoryManagerInterface] = {}
    _configs: Dict[str, Dict[str, Any]] = {}
    _lock = RLock()
    
    @classmethod
    def register(
        cls, 
        name: str, 
        manager: Optional[MemoryManagerInterface] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> MemoryManagerInterface:
        """
        Register a memory manager instance
        
        Args:
            name: Name for this instance
            manager: Memory manager instance (created if None)
            config: Configuration for the manager
            
        Returns:
            The registered memory manager
        """
        with cls._lock:
            if manager:
                cls._managers[name] = manager
            else:
                # Create with config
                config = config or {}
                backend = config.get('backend', MemoryBackend.SPANNER)
                
                # Use GraphitiMemoryWrapper for Graphiti functionality
                manager = GraphitiMemoryWrapper(
                    graph_backend=backend,
                    config=config
                )
                cls._managers[name] = manager
            
            if config:
                cls._configs[name] = config
            
            logger.info(f"Registered memory manager '{name}'")
            return cls._managers[name]
    
    @classmethod
    def get(
        cls, 
        name: str = "default",
        create_if_missing: bool = True
    ) -> Optional[MemoryManagerInterface]:
        """
        Get a memory manager by name
        
        Args:
            name: Name of the manager
            create_if_missing: Create if doesn't exist
            
        Returns:
            Memory manager instance or None
        """
        with cls._lock:
            if name not in cls._managers and create_if_missing:
                # Auto-create with default config
                config = cls._configs.get(name, {})
                return cls.register(name, config=config)
            
            return cls._managers.get(name)
    
    @classmethod
    def get_or_create(
        cls,
        name: str = "default",
        config: Optional[Dict[str, Any]] = None
    ) -> MemoryManagerInterface:
        """Get or create a memory manager with config"""
        with cls._lock:
            if name in cls._managers:
                return cls._managers[name]
            
            return cls.register(name, config=config)
    
    @classmethod
    async def cleanup(cls, name: Optional[str] = None):
        """
        Cleanup memory managers
        
        Args:
            name: Specific manager to cleanup, or None for all
        """
        with cls._lock:
            if name:
                # Cleanup specific manager
                if name in cls._managers:
                    try:
                        await cls._managers[name].cleanup()
                        del cls._managers[name]
                        logger.info(f"Cleaned up memory manager '{name}'")
                    except Exception as e:
                        logger.error(f"Error cleaning up '{name}': {e}")
            else:
                # Cleanup all managers
                for name, manager in list(cls._managers.items()):
                    try:
                        await manager.cleanup()
                        logger.info(f"Cleaned up memory manager '{name}'")
                    except Exception as e:
                        logger.error(f"Error cleaning up '{name}': {e}")
                
                cls._managers.clear()
                cls._configs.clear()
    
    @classmethod
    def clear(cls):
        """Clear all managers (for testing) - sync version"""
        with cls._lock:
            cls._managers.clear()
            cls._configs.clear()
            logger.info("Cleared memory registry")
    
    @classmethod
    def list_managers(cls) -> Dict[str, Dict[str, Any]]:
        """List all registered managers with their stats"""
        with cls._lock:
            result = {}
            for name, manager in cls._managers.items():
                stats = {}
                if hasattr(manager, 'get_stats'):
                    stats = manager.get_stats()
                
                result[name] = {
                    "type": type(manager).__name__,
                    "config": cls._configs.get(name, {}),
                    "stats": stats
                }
            
            return result


# Convenience functions for backward compatibility
def get_memory_manager(name: str = "default") -> MemoryManagerInterface:
    """Get the default or named memory manager"""
    return MemoryRegistry.get(name)


def create_memory_manager(
    backend: str = MemoryBackend.SPANNER,
    config: Optional[Dict[str, Any]] = None
) -> ManagedMemoryManager:
    """
    Create a managed memory manager for use with async context
    
    Example:
        async with create_memory_manager() as memory:
            await memory.process_message_with_graph(...)
    """
    config = config or {}
    config['backend'] = backend
    
    manager = ManagedMemoryManager(
        graph_backend=backend,
        config=config
    )
    
    return manager