"""
Base Deepgram Client with Dynamic Intent Support
Provides shared functionality for all Deepgram clients to use dynamic intents
"""
import os
import asyncio
from typing import Optional, List, Dict, Any
from src.voice.deepgram.dynamic_intent_learner import DynamicIntentLearner
import structlog

logger = structlog.get_logger()


class BaseDeepgramClientWithIntents:
    """Base class providing dynamic intent support for Deepgram clients"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DEEPGRAM_API_KEY")
        self.intent_learner = DynamicIntentLearner()
        self._intent_refresh_interval = 60  # seconds
        self._intent_refresh_task = None
        self._current_custom_intents = []
        
    async def start_intent_learning(self):
        """Start the background task that refreshes custom intents"""
        if not self._intent_refresh_task:
            self._intent_refresh_task = asyncio.create_task(self._refresh_intents_loop())
            logger.info("Started dynamic intent learning background task")
    
    async def stop_intent_learning(self):
        """Stop the intent refresh background task"""
        if self._intent_refresh_task:
            self._intent_refresh_task.cancel()
            try:
                await self._intent_refresh_task
            except asyncio.CancelledError:
                pass
            self._intent_refresh_task = None
            logger.info("Stopped dynamic intent learning background task")
    
    async def _refresh_intents_loop(self):
        """Periodically refresh custom intents based on learned patterns"""
        while True:
            try:
                # Generate new custom intents
                new_intents = self.intent_learner.generate_deepgram_custom_intents()
                
                if new_intents != self._current_custom_intents:
                    self._current_custom_intents = new_intents
                    logger.info(f"Updated custom intents: {len(new_intents)} patterns")
                    
                    # Log some examples
                    if new_intents:
                        examples = new_intents[:5]
                        logger.debug(f"Example intents: {examples}")
                
                # Wait before next refresh
                await asyncio.sleep(self._intent_refresh_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error refreshing intents: {e}")
                await asyncio.sleep(self._intent_refresh_interval)
    
    def get_current_custom_intents(self) -> List[str]:
        """Get the current list of custom intents"""
        return self._current_custom_intents.copy()
    
    def _add_custom_intents_to_options(self, options_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Add custom intents to Deepgram options"""
        if self._current_custom_intents:
            # For streaming API, custom intents use the 'intents' parameter
            options_dict['intents'] = self._current_custom_intents
            logger.debug(f"Added {len(self._current_custom_intents)} custom intents to options")
        return options_dict
    
    async def observe_supervisor_intent(self, transcript: str, intent: str, confidence: float):
        """
        Record an intent classification from the supervisor
        This should be called whenever the supervisor classifies a user query
        """
        await self.intent_learner.observe_intent(transcript, intent, confidence)
    
    def get_intent_statistics(self) -> Dict[str, Any]:
        """Get statistics about learned intents"""
        return {
            "intent_counts": self.intent_learner.get_intent_statistics(),
            "current_custom_intents": len(self._current_custom_intents),
            "total_observations": len(self.intent_learner.intent_observations)
        }