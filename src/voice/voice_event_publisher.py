"""
Voice Event Publisher - Single source of truth via Pub/Sub
All voice events flow through Pub/Sub for consistent processing
"""
import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from google.cloud import pubsub_v1
import structlog
from dataclasses import dataclass, asdict
import os

logger = structlog.get_logger()

@dataclass
class VoiceEvent:
    """Standard voice event format for Pub/Sub"""
    event_type: str  # "voice_turn", "session_start", "session_end", "insight_extracted"
    event_id: str
    timestamp: datetime
    user_id: str
    session_id: str
    
    # Event-specific data
    data: Dict[str, Any]
    
    # Metadata
    source: str = "deepgram"
    version: str = "1.0"
    
    def to_pubsub_message(self) -> Dict[str, Any]:
        """Convert to Pub/Sub message format"""
        return {
            "data": json.dumps({
                "event_type": self.event_type,
                "event_id": self.event_id,
                "timestamp": self.timestamp.isoformat(),
                "user_id": self.user_id,
                "session_id": self.session_id,
                "data": self.data,
                "source": self.source,
                "version": self.version
            }),
            "attributes": {
                "event_type": self.event_type,
                "user_id": self.user_id,
                "session_id": self.session_id,
                "source": self.source
            }
        }

class VoiceEventPublisher:
    """Publishes all voice events to Pub/Sub"""
    
    def __init__(self, project_id: str = None, topic_name: str = "voice-events"):
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID", "leafloafai")
        self.topic_name = topic_name
        self.topic_path = f"projects/{self.project_id}/topics/{self.topic_name}"
        
        # Initialize publisher
        self.publisher = pubsub_v1.PublisherClient()
        
        # Ensure topic exists
        self._ensure_topic_exists()
        
        # Batch settings for performance
        self.batch_settings = pubsub_v1.types.BatchSettings(
            max_messages=100,  # Send when we have 100 messages
            max_bytes=1024 * 1024,  # Or 1MB of data
            max_latency=0.1,  # Or after 100ms
        )
        
    def _ensure_topic_exists(self):
        """Create topic if it doesn't exist"""
        try:
            self.publisher.get_topic(request={"topic": self.topic_path})
            logger.info(f"Topic {self.topic_name} already exists")
        except:
            try:
                self.publisher.create_topic(request={"name": self.topic_path})
                logger.info(f"Created topic {self.topic_name}")
            except Exception as e:
                logger.error(f"Failed to create topic: {e}")
    
    async def publish_voice_turn(
        self,
        user_id: str,
        session_id: str,
        turn_id: str,
        deepgram_response: Dict[str, Any]
    ):
        """Publish a voice turn event with full Deepgram response"""
        
        # Extract key metrics for attributes
        transcript = ""
        sentiment = None
        intent = None
        
        if "channel" in deepgram_response:
            alternatives = deepgram_response["channel"].get("alternatives", [])
            if alternatives:
                alt = alternatives[0]
                transcript = alt.get("transcript", "")
                
                # Get sentiment
                if "sentiment" in alt:
                    sentiment = alt["sentiment"].get("sentiment")
                
                # Get primary intent
                if "intents" in alt and alt["intents"]:
                    intent = alt["intents"][0].get("intent")
        
        event = VoiceEvent(
            event_type="voice_turn",
            event_id=turn_id,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            session_id=session_id,
            data={
                "turn_id": turn_id,
                "deepgram_response": deepgram_response,
                "transcript": transcript,
                "sentiment": sentiment,
                "intent": intent
            }
        )
        
        await self._publish_event(event)
    
    async def publish_session_start(
        self,
        user_id: str,
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Publish session start event"""
        event = VoiceEvent(
            event_type="session_start",
            event_id=f"{session_id}_start",
            timestamp=datetime.utcnow(),
            user_id=user_id,
            session_id=session_id,
            data={
                "metadata": metadata or {},
                "start_time": datetime.utcnow().isoformat()
            }
        )
        
        await self._publish_event(event)
    
    async def publish_session_end(
        self,
        user_id: str,
        session_id: str,
        summary: Optional[Dict[str, Any]] = None
    ):
        """Publish session end event with summary"""
        event = VoiceEvent(
            event_type="session_end",
            event_id=f"{session_id}_end",
            timestamp=datetime.utcnow(),
            user_id=user_id,
            session_id=session_id,
            data={
                "summary": summary or {},
                "end_time": datetime.utcnow().isoformat()
            }
        )
        
        await self._publish_event(event)
    
    async def publish_search_outcome(
        self,
        user_id: str,
        session_id: str,
        search_query: str,
        outcome: Dict[str, Any]
    ):
        """Publish search outcome for ML training"""
        event = VoiceEvent(
            event_type="search_outcome",
            event_id=f"{session_id}_{datetime.utcnow().timestamp()}",
            timestamp=datetime.utcnow(),
            user_id=user_id,
            session_id=session_id,
            data={
                "query": search_query,
                "products_found": outcome.get("products_found", 0),
                "products_shown": outcome.get("products_shown", 0),
                "time_to_find_ms": outcome.get("time_to_find_ms", 0),
                "refinements_needed": outcome.get("refinements_needed", 0),
                "user_satisfied": outcome.get("user_satisfied", False),
                "added_to_cart": outcome.get("added_to_cart", False)
            }
        )
        
        await self._publish_event(event)
    
    async def _publish_event(self, event: VoiceEvent):
        """Publish event to Pub/Sub"""
        try:
            message = event.to_pubsub_message()
            
            # Publish with retry
            future = self.publisher.publish(
                self.topic_path,
                data=message["data"].encode("utf-8"),
                **message["attributes"]
            )
            
            # Log success (fire and forget for low latency)
            asyncio.create_task(self._log_publish_result(future, event.event_id))
            
        except Exception as e:
            logger.error(f"Failed to publish event {event.event_id}: {e}")
    
    async def _log_publish_result(self, future, event_id: str):
        """Log publish result asynchronously"""
        try:
            message_id = await asyncio.get_event_loop().run_in_executor(
                None, future.result
            )
            logger.debug(f"Published event {event_id} with message ID: {message_id}")
        except Exception as e:
            logger.error(f"Publish failed for event {event_id}: {e}")

# Singleton instance
voice_event_publisher = VoiceEventPublisher()

# Example Pub/Sub message format:
"""
{
  "event_type": "voice_turn",
  "event_id": "turn_123",
  "timestamp": "2024-12-29T10:30:00Z",
  "user_id": "user_456", 
  "session_id": "session_789",
  "data": {
    "turn_id": "turn_123",
    "deepgram_response": {
      "channel": {
        "alternatives": [{
          "transcript": "I need organic valley milk",
          "confidence": 0.98,
          "words": [...],
          "sentiment": {
            "sentiment": "neutral",
            "confidence": 0.85
          },
          "intents": [{
            "intent": "product_search",
            "confidence": 0.92
          }],
          "topics": [{
            "topic": "dairy",
            "confidence": 0.88
          }],
          "entities": [{
            "entity": "Organic Valley",
            "type": "brand",
            "confidence": 0.95
          }]
        }]
      }
    },
    "transcript": "I need organic valley milk",
    "sentiment": "neutral",
    "intent": "product_search"
  },
  "source": "deepgram",
  "version": "1.0"
}
"""