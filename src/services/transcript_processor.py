"""
Asynchronous transcript processor for sentiment analysis and ML training
Captures voice transcripts and processes them through Deepgram's batch API
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import structlog
from deepgram import DeepgramClient
import aiofiles
import os

logger = structlog.get_logger()

class TranscriptProcessor:
    """Process transcripts asynchronously for sentiment and ML features"""
    
    def __init__(self, deepgram_api_key: str):
        self.deepgram = DeepgramClient(deepgram_api_key)
        self.transcript_queue = asyncio.Queue()
        self.processing = False
        
        # Storage paths
        self.transcript_dir = "data/transcripts"
        self.analysis_dir = "data/analysis"
        os.makedirs(self.transcript_dir, exist_ok=True)
        os.makedirs(self.analysis_dir, exist_ok=True)
        
    async def capture_transcript(self, user_id: str, session_id: str, transcript: str, 
                               response: str, metadata: Optional[Dict] = None):
        """Capture transcript for async processing"""
        transcript_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "session_id": session_id,
            "transcript": transcript,
            "response": response,
            "metadata": metadata or {},
            "processing_status": "pending"
        }
        
        # Add to processing queue
        await self.transcript_queue.put(transcript_data)
        
        # Also save to file for persistence
        filename = f"{self.transcript_dir}/{session_id}_{datetime.utcnow().timestamp()}.json"
        async with aiofiles.open(filename, 'w') as f:
            await f.write(json.dumps(transcript_data, indent=2))
            
        logger.info(f"Captured transcript for processing", 
                   user_id=user_id, 
                   session_id=session_id,
                   length=len(transcript))
        
    async def analyze_transcript(self, text: str) -> Dict[str, Any]:
        """Analyze transcript using Deepgram's batch API for Audio Intelligence"""
        try:
            # Use Deepgram's analyze API for text
            # This gives us sentiment, intents, topics, entities, summary
            response = await self.deepgram.analyze.v("1").analyze_text(
                {"text": text},
                {
                    "language": "en",
                    "sentiment": True,
                    "intents": True,
                    "topics": True,
                    "entities": True,
                    "summarize": True
                }
            )
            
            if response and hasattr(response, 'results'):
                results = response.results
                return {
                    "sentiment": results.sentiment.segments[0].sentiment if results.sentiment else None,
                    "sentiment_score": results.sentiment.segments[0].confidence if results.sentiment else 0,
                    "intents": [{"intent": i.intent, "confidence": i.confidence} 
                               for i in results.intents.segments[0].intents] if results.intents else [],
                    "topics": [{"topic": t.topic, "confidence": t.confidence} 
                              for t in results.topics.segments[0].topics] if results.topics else [],
                    "entities": [{"entity": e.value, "type": e.entity_type} 
                                for e in results.entities.entities] if results.entities else [],
                    "summary": results.summary.short if results.summary else ""
                }
            return {}
            
        except Exception as e:
            logger.error(f"Error analyzing transcript: {e}")
            return {}
    
    async def process_for_graphiti(self, transcript_data: Dict, analysis: Dict) -> Dict:
        """Process analyzed transcript for Graphiti memory and ML training"""
        # Extract key information for Graphiti
        graphiti_data = {
            "timestamp": transcript_data["timestamp"],
            "user_id": transcript_data["user_id"],
            "session_id": transcript_data["session_id"],
            
            # User query understanding
            "user_query": transcript_data["transcript"],
            "query_intent": analysis.get("intents", [{}])[0].get("intent") if analysis.get("intents") else None,
            "query_sentiment": analysis.get("sentiment"),
            "query_entities": analysis.get("entities", []),
            
            # Response tracking
            "assistant_response": transcript_data["response"],
            
            # Topics for personalization
            "topics": analysis.get("topics", []),
            
            # ML features
            "features": {
                "query_length": len(transcript_data["transcript"].split()),
                "sentiment_score": analysis.get("sentiment_score", 0),
                "has_product_intent": any(i["intent"] in ["search_product", "buy", "order"] 
                                        for i in analysis.get("intents", [])),
                "entity_count": len(analysis.get("entities", [])),
                "is_question": transcript_data["transcript"].strip().endswith("?")
            }
        }
        
        # Save for ML training
        ml_filename = f"{self.analysis_dir}/ml_{transcript_data['session_id']}_{datetime.utcnow().timestamp()}.json"
        async with aiofiles.open(ml_filename, 'w') as f:
            await f.write(json.dumps(graphiti_data, indent=2))
            
        return graphiti_data
    
    async def start_processing(self):
        """Start the async processing loop"""
        self.processing = True
        logger.info("Started transcript processor")
        
        while self.processing:
            try:
                # Get transcript from queue (wait up to 1 second)
                transcript_data = await asyncio.wait_for(
                    self.transcript_queue.get(), 
                    timeout=1.0
                )
                
                # Analyze the transcript
                analysis = await self.analyze_transcript(transcript_data["transcript"])
                
                # Process for Graphiti and ML
                graphiti_data = await self.process_for_graphiti(transcript_data, analysis)
                
                # Log success
                logger.info("Processed transcript",
                          user_id=transcript_data["user_id"],
                          sentiment=analysis.get("sentiment"),
                          intent=graphiti_data["query_intent"])
                
                # TODO: Send to Graphiti memory
                # TODO: Send to BigQuery for ML pipeline
                
            except asyncio.TimeoutError:
                # No transcripts to process, continue
                continue
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                await asyncio.sleep(1)
    
    async def stop_processing(self):
        """Stop the processing loop"""
        self.processing = False
        logger.info("Stopped transcript processor")
    
    async def get_user_insights(self, user_id: str) -> Dict[str, Any]:
        """Get aggregated insights for a user from processed transcripts"""
        insights = {
            "total_conversations": 0,
            "average_sentiment": 0,
            "common_intents": {},
            "favorite_topics": {},
            "product_interests": []
        }
        
        # Read all analysis files for user
        for filename in os.listdir(self.analysis_dir):
            if filename.startswith("ml_") and filename.endswith(".json"):
                async with aiofiles.open(f"{self.analysis_dir}/{filename}", 'r') as f:
                    data = json.loads(await f.read())
                    
                    if data["user_id"] == user_id:
                        insights["total_conversations"] += 1
                        
                        # Aggregate sentiment
                        if data["query_sentiment"]:
                            insights["average_sentiment"] = (
                                insights["average_sentiment"] + 
                                data["features"]["sentiment_score"]
                            ) / insights["total_conversations"]
                        
                        # Count intents
                        intent = data.get("query_intent")
                        if intent:
                            insights["common_intents"][intent] = \
                                insights["common_intents"].get(intent, 0) + 1
                        
                        # Aggregate topics
                        for topic in data.get("topics", []):
                            topic_name = topic.get("topic")
                            if topic_name:
                                insights["favorite_topics"][topic_name] = \
                                    insights["favorite_topics"].get(topic_name, 0) + 1
                        
                        # Extract product interests from entities
                        for entity in data.get("query_entities", []):
                            if entity.get("type") == "product":
                                insights["product_interests"].append(entity.get("entity"))
        
        return insights


# Singleton instance
_processor: Optional[TranscriptProcessor] = None

def get_transcript_processor(api_key: str) -> TranscriptProcessor:
    """Get or create the transcript processor singleton"""
    global _processor
    if _processor is None:
        _processor = TranscriptProcessor(api_key)
    return _processor