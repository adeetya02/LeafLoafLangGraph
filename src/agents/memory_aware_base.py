"""
Memory-aware base agent class that provides memory context and learning capabilities
"""
from typing import Dict, Any, Optional, List
import asyncio
import structlog
from abc import abstractmethod
from datetime import datetime
from src.agents.base import BaseAgent
from src.memory.memory_registry import MemoryRegistry
from src.memory.memory_interfaces import MemoryBackend
import os

logger = structlog.get_logger()

class MemoryAwareAgent(BaseAgent):
    """Base class for agents with full memory awareness and learning capabilities"""
    
    def __init__(self, agent_name: str):
        super().__init__(agent_name)
        self.agent_name = agent_name  # Store for compatibility
        self._memory_manager = None
        self._interaction_id = None
        
    async def get_memory_manager(self):
        """Lazy load memory manager"""
        if not self._memory_manager:
            backend = MemoryBackend.SPANNER if os.getenv("SPANNER_INSTANCE_ID") else MemoryBackend.IN_MEMORY
            self._memory_manager = MemoryRegistry.get_or_create(
                self.agent_name,
                config={"backend": backend}
            )
        return self._memory_manager
    
    async def get_memory_context(self, user_id: str, session_id: str, query: str) -> Dict[str, Any]:
        """Get relevant memory context for this agent's decision making"""
        try:
            memory_manager = await self.get_memory_manager()
            
            # Get base context
            base_context = await memory_manager.get_context(query)
            
            # Get agent-specific context
            agent_context = await self._get_agent_specific_context(
                user_id, session_id, query, base_context
            )
            
            return {
                **base_context,
                **agent_context,
                "memory_available": True
            }
        except Exception as e:
            logger.warning(f"Failed to get memory context: {e}")
            return {"memory_available": False}
    
    @abstractmethod
    async def _get_agent_specific_context(
        self, 
        user_id: str, 
        session_id: str, 
        query: str, 
        base_context: Dict
    ) -> Dict[str, Any]:
        """Each agent implements their specific memory needs"""
        pass
    
    async def record_decision(self, decision: Dict[str, Any], context: Dict[str, Any]):
        """Record agent decision for learning"""
        try:
            memory_manager = await self.get_memory_manager()
            
            # Create interaction record
            interaction = {
                "agent": self.agent_name,
                "decision": decision,
                "context": context,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            # Store for later learning
            self._interaction_id = await self._store_interaction(interaction)
            
            # Log for debugging
            logger.info(
                f"Recorded {self.agent_name} decision",
                decision_type=decision.get("type"),
                interaction_id=self._interaction_id
            )
            
        except Exception as e:
            logger.error(f"Failed to record decision: {e}")
    
    async def learn_from_outcome(self, outcome: Dict[str, Any]):
        """Learn from the outcome of our decision"""
        if not self._interaction_id:
            return
            
        try:
            memory_manager = await self.get_memory_manager()
            
            # Update interaction with outcome
            await self._update_interaction_outcome(self._interaction_id, outcome)
            
            # Trigger pattern learning if applicable
            if outcome.get("success"):
                await self._update_success_patterns(outcome)
            else:
                await self._update_failure_patterns(outcome)
                
        except Exception as e:
            logger.error(f"Failed to learn from outcome: {e}")
    
    async def _store_interaction(self, interaction: Dict) -> str:
        """Store interaction and return ID"""
        import uuid
        from src.analytics.bigquery_client import bigquery_client
        
        interaction_id = str(uuid.uuid4())
        
        try:
            # Store to BigQuery for analytics
            event_data = {
                "event_id": interaction_id,
                "user_id": interaction.get("user_id", "anonymous"),
                "session_id": interaction.get("session_id"),
                "agent_name": self.agent_name,
                "interaction_type": interaction.get("type", "unknown"),
                "query": interaction.get("query", ""),
                "decision": interaction.get("decision", {}),
                "timestamp": datetime.now().isoformat(),
                "metadata": interaction.get("metadata", {})
            }
            
            # Fire and forget to BigQuery
            await bigquery_client.stream_interaction_event(event_data)
            
            # Store in memory for immediate access
            if not hasattr(self, '_recent_interactions'):
                self._recent_interactions = {}
            self._recent_interactions[interaction_id] = interaction
            
            # Keep only last 100 interactions in memory
            if len(self._recent_interactions) > 100:
                oldest_id = next(iter(self._recent_interactions))
                del self._recent_interactions[oldest_id]
            
            logger.debug(f"Stored interaction {interaction_id} for agent {self.agent_name}")
            
        except Exception as e:
            logger.error(f"Failed to store interaction: {e}")
        
        return interaction_id
    
    async def _update_interaction_outcome(self, interaction_id: str, outcome: Dict):
        """Update stored interaction with outcome"""
        try:
            # Update in-memory record
            if hasattr(self, '_recent_interactions') and interaction_id in self._recent_interactions:
                self._recent_interactions[interaction_id]["outcome"] = outcome
                self._recent_interactions[interaction_id]["outcome_timestamp"] = datetime.now().isoformat()
            
            # Stream outcome event to BigQuery
            from src.analytics.bigquery_client import bigquery_client
            
            outcome_event = {
                "event_id": f"{interaction_id}_outcome",
                "interaction_id": interaction_id,
                "user_id": outcome.get("user_id", "anonymous"),
                "agent_name": self.agent_name,
                "outcome_type": outcome.get("type", "unknown"),
                "success": outcome.get("success", False),
                "metadata": outcome
            }
            
            await bigquery_client.stream_interaction_event(outcome_event)
            
            logger.debug(f"Updated outcome for interaction {interaction_id}")
            
        except Exception as e:
            logger.error(f"Failed to update interaction outcome: {e}")
    
    async def _update_success_patterns(self, outcome: Dict):
        """Update patterns based on successful outcomes"""
        try:
            # Get memory manager
            memory_manager = await self.get_memory_manager()
            if not memory_manager:
                return
            
            # Extract pattern data from outcome
            pattern_type = outcome.get("pattern_type")
            pattern_data = outcome.get("pattern_data", {})
            
            # Update confidence for successful patterns
            if pattern_type == "routing":
                # Successful routing decision
                await self._update_routing_pattern(
                    query_pattern=pattern_data.get("query_pattern"),
                    chosen_agent=pattern_data.get("chosen_agent"),
                    success=True
                )
            
            elif pattern_type == "search_refinement":
                # Successful search refinement
                await self._update_search_pattern(
                    original_query=pattern_data.get("original_query"),
                    refined_query=pattern_data.get("refined_query"),
                    clicked_position=pattern_data.get("clicked_position", 0)
                )
            
            elif pattern_type == "quantity_suggestion":
                # Successful quantity suggestion
                await self._update_quantity_pattern(
                    product_sku=pattern_data.get("product_sku"),
                    suggested_quantity=pattern_data.get("suggested_quantity"),
                    accepted=True
                )
            
            logger.debug(f"Updated success pattern: {pattern_type}")
            
        except Exception as e:
            logger.error(f"Failed to update success patterns: {e}")
    
    async def _update_failure_patterns(self, outcome: Dict):
        """Learn from failures to avoid them"""
        try:
            # Get memory manager
            memory_manager = await self.get_memory_manager()
            if not memory_manager:
                return
            
            # Extract failure data
            failure_type = outcome.get("failure_type")
            failure_data = outcome.get("failure_data", {})
            
            # Learn from different types of failures
            if failure_type == "routing_error":
                # Wrong agent was chosen
                await self._update_routing_pattern(
                    query_pattern=failure_data.get("query_pattern"),
                    chosen_agent=failure_data.get("chosen_agent"),
                    success=False
                )
            
            elif failure_type == "irrelevant_results":
                # Search results were not helpful
                await self._decrease_search_confidence(
                    query=failure_data.get("query"),
                    search_params=failure_data.get("search_params")
                )
            
            elif failure_type == "quantity_rejected":
                # User rejected quantity suggestion
                await self._update_quantity_pattern(
                    product_sku=failure_data.get("product_sku"),
                    suggested_quantity=failure_data.get("suggested_quantity"),
                    accepted=False
                )
            
            logger.debug(f"Learned from failure: {failure_type}")
            
        except Exception as e:
            logger.error(f"Failed to update failure patterns: {e}")
    
    # Helper methods for pattern updates
    
    async def _update_routing_pattern(self, query_pattern: str, chosen_agent: str, success: bool):
        """Update routing pattern confidence"""
        # This would update the pattern in Graphiti
        # For now, just log
        adjustment = 0.05 if success else -0.05
        logger.info(f"Would adjust routing pattern: {query_pattern} -> {chosen_agent} by {adjustment}")
    
    async def _update_search_pattern(self, original_query: str, refined_query: str, clicked_position: int):
        """Update search refinement pattern"""
        # Higher position clicks mean better refinement
        confidence_boost = max(0.1, 0.5 - (clicked_position * 0.1))
        logger.info(f"Would boost search pattern: '{original_query}' -> '{refined_query}' by {confidence_boost}")
    
    async def _update_quantity_pattern(self, product_sku: str, suggested_quantity: int, accepted: bool):
        """Update quantity suggestion pattern"""
        adjustment = 0.05 if accepted else -0.05
        logger.info(f"Would adjust quantity pattern: {product_sku} qty={suggested_quantity} by {adjustment}")
    
    async def _decrease_search_confidence(self, query: str, search_params: Dict):
        """Decrease confidence in search parameters"""
        logger.info(f"Would decrease confidence for search params: {search_params} on query: {query}")

    def get_memory_insights(self, memory_context: Dict) -> Dict[str, Any]:
        """Extract actionable insights from memory context"""
        insights = {
            "has_preferences": bool(memory_context.get("preferences")),
            "has_patterns": bool(memory_context.get("patterns")),
            "confidence_boost": 0.0
        }
        
        # Boost confidence if we have strong patterns
        if memory_context.get("patterns"):
            pattern_strength = memory_context.get("pattern_strength", 0.0)
            insights["confidence_boost"] = min(0.2, pattern_strength * 0.3)
            
        return insights