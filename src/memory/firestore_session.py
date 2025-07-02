"""
Firestore-based session memory for budget deployment
Free tier: 50K reads, 20K writes per day
"""
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import structlog
from google.cloud import firestore
from google.api_core import exceptions

logger = structlog.get_logger()

class FirestoreSessionMemory:
    """Session memory using Firestore (free tier friendly)"""
    
    def __init__(self, ttl_hours: int = 24):
        try:
            self.db = firestore.Client()
            self.sessions = self.db.collection('sessions')
            self.ttl_hours = ttl_hours
            logger.info("Firestore session memory initialized")
        except Exception as e:
            logger.warning(f"Firestore init failed, using in-memory: {e}")
            self.db = None
            self.fallback_memory = {}
    
    async def get_conversation(self, session_id: str) -> List[Dict]:
        """Get conversation history"""
        if not self.db:
            return self.fallback_memory.get(session_id, {}).get('messages', [])
            
        try:
            doc = self.sessions.document(session_id).get()
            if doc.exists:
                data = doc.to_dict()
                # Check TTL
                if self._is_expired(data.get('updated_at')):
                    return []
                return data.get('messages', [])
            return []
        except Exception as e:
            logger.error(f"Firestore read error: {e}")
            return []
    
    async def add_to_conversation(self, session_id: str, role: str, content: str):
        """Add message to conversation"""
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        }
        
        if not self.db:
            if session_id not in self.fallback_memory:
                self.fallback_memory[session_id] = {'messages': []}
            self.fallback_memory[session_id]['messages'].append(message)
            return
            
        try:
            doc_ref = self.sessions.document(session_id)
            doc_ref.set({
                'messages': firestore.ArrayUnion([message]),
                'updated_at': firestore.SERVER_TIMESTAMP,
                'created_at': firestore.SERVER_TIMESTAMP
            }, merge=True)
        except Exception as e:
            logger.error(f"Firestore write error: {e}")
    
    async def get_user_context(self, session_id: str) -> Optional[Dict]:
        """Get user context from recent messages"""
        messages = await self.get_conversation(session_id)
        if not messages:
            return None
            
        # Get last 5 messages for context
        recent = messages[-5:]
        
        return {
            'message_count': len(messages),
            'recent_messages': recent,
            'session_start': messages[0]['timestamp'] if messages else None
        }
    
    async def get_preferences(self, session_id: str) -> List[str]:
        """Get user preferences"""
        if not self.db:
            return self.fallback_memory.get(session_id, {}).get('preferences', [])
            
        try:
            doc = self.sessions.document(session_id).get()
            if doc.exists:
                return doc.to_dict().get('preferences', [])
            return []
        except:
            return []
    
    async def add_preference(self, session_id: str, preference: str):
        """Add user preference"""
        if not self.db:
            if session_id not in self.fallback_memory:
                self.fallback_memory[session_id] = {'preferences': []}
            if preference not in self.fallback_memory[session_id]['preferences']:
                self.fallback_memory[session_id]['preferences'].append(preference)
            return
            
        try:
            doc_ref = self.sessions.document(session_id)
            doc_ref.set({
                'preferences': firestore.ArrayUnion([preference]),
                'updated_at': firestore.SERVER_TIMESTAMP
            }, merge=True)
        except Exception as e:
            logger.error(f"Firestore preference error: {e}")
    
    async def cleanup_expired(self):
        """Clean up expired sessions (run as scheduled job)"""
        if not self.db:
            return
            
        try:
            cutoff = datetime.now() - timedelta(hours=self.ttl_hours)
            
            # Query expired sessions
            expired = self.sessions.where(
                'updated_at', '<', cutoff
            ).stream()
            
            # Batch delete
            batch = self.db.batch()
            count = 0
            
            for doc in expired:
                batch.delete(doc.reference)
                count += 1
                
                if count >= 500:  # Firestore batch limit
                    batch.commit()
                    batch = self.db.batch()
                    count = 0
            
            if count > 0:
                batch.commit()
                
            logger.info(f"Cleaned up {count} expired sessions")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def _is_expired(self, updated_at) -> bool:
        """Check if session is expired"""
        if not updated_at:
            return True
        
        if hasattr(updated_at, 'timestamp'):
            updated = datetime.fromtimestamp(updated_at.timestamp())
        else:
            updated = updated_at
            
        return datetime.now() - updated > timedelta(hours=self.ttl_hours)

# Singleton instance
_instance = None

def get_session_memory() -> FirestoreSessionMemory:
    """Get singleton instance"""
    global _instance
    if _instance is None:
        _instance = FirestoreSessionMemory()
    return _instance