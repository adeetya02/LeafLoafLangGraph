"""
Session memory management with Redis caching and fallback
"""
import os
import redis
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import structlog
from src.config.settings import settings

logger = structlog.get_logger()

class SessionMemory:
    """Enhanced session memory with Redis caching and in-memory fallback"""
    
    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        self.memory_store: Dict[str, Any] = {}
        self.messages: List[Dict] = []
        self.redis_client = None
        
        # Try to connect to Redis if available
        if settings.redis_url:
            try:
                self.redis_client = redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2
                )
                # Test connection
                self.redis_client.ping()
                logger.info("Redis connection established", session_id=session_id)
            except Exception as e:
                logger.warning(f"Redis connection failed, using in-memory: {e}")
                self.redis_client = None
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to the conversation history"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self.messages.append(message)
        
        # Store in Redis if available
        if self.redis_client:
            try:
                key = f"session:{self.session_id}:messages"
                self.redis_client.rpush(key, json.dumps(message))
                self.redis_client.expire(key, settings.redis_ttl_seconds)
            except Exception as e:
                logger.error(f"Redis write failed: {e}")
    
    def get_messages(self, limit: Optional[int] = None) -> List[Dict]:
        """Get conversation history"""
        # Try Redis first
        if self.redis_client:
            try:
                key = f"session:{self.session_id}:messages"
                messages = self.redis_client.lrange(key, 0, -1)
                self.messages = [json.loads(msg) for msg in messages]
            except Exception as e:
                logger.error(f"Redis read failed: {e}")
        
        if limit:
            return self.messages[-limit:]
        return self.messages
    
    def set_data(self, key: str, value: Any):
        """Store arbitrary data in session"""
        self.memory_store[key] = value
        
        # Store in Redis if available
        if self.redis_client:
            try:
                redis_key = f"session:{self.session_id}:data:{key}"
                self.redis_client.set(
                    redis_key, 
                    json.dumps(value),
                    ex=settings.redis_ttl_seconds
                )
            except Exception as e:
                logger.error(f"Redis write failed: {e}")
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Retrieve data from session"""
        # Try Redis first
        if self.redis_client:
            try:
                redis_key = f"session:{self.session_id}:data:{key}"
                value = self.redis_client.get(redis_key)
                if value:
                    self.memory_store[key] = json.loads(value)
            except Exception as e:
                logger.error(f"Redis read failed: {e}")
        
        return self.memory_store.get(key, default)
    
    def clear(self):
        """Clear session memory"""
        self.messages = []
        self.memory_store = {}
        
        # Clear Redis if available
        if self.redis_client:
            try:
                pattern = f"session:{self.session_id}:*"
                for key in self.redis_client.scan_iter(match=pattern):
                    self.redis_client.delete(key)
            except Exception as e:
                logger.error(f"Redis clear failed: {e}")
    
    def get_summary(self) -> Dict:
        """Get session summary"""
        return {
            "session_id": self.session_id,
            "message_count": len(self.messages),
            "data_keys": list(self.memory_store.keys()),
            "redis_available": self.redis_client is not None
        }