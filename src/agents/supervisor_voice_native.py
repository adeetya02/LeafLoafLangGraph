"""
Voice-Native Multi-Modal Supervisor Agent
Built on top of existing supervisor with full voice and multi-modal support
"""
from typing import Dict, Any, Optional, List, AsyncGenerator
import asyncio
import time
import json
import os
from datetime import datetime
from langsmith import traceable
from src.agents.supervisor_optimized import OptimizedSupervisorAgent
from src.models.state import SearchState
from src.models.voice_state import (
    VoiceMetadata, VoiceTranscript, MultiModalInput,
    VoiceSession, ConversationContext, VoiceResponse,
    VoiceSearchState
)
from src.voice.google_voice_handler import GoogleVoiceHandler
from src.memory.graphiti_wrapper import GraphitiMemoryWrapper
from src.memory.memory_manager import memory_manager
from src.config.constants import (
    FAST_MODE, 
    SUPERVISOR_TIMEOUT_MS,
    SUPERVISOR_MAX_REASONING_STEPS
)
import structlog

logger = structlog.get_logger()

class VoiceNativeSupervisor(OptimizedSupervisorAgent):
    """
    Enhanced supervisor that natively handles voice and multi-modal inputs
    
    Key Features:
    - Voice metadata influences routing and response style
    - Multi-modal input processing (voice, text, future: image)
    - Conversation context for multi-turn dialogue
    - Cultural and linguistic awareness
    - Emotion-aware responses
    """
    
    def __init__(self):
        super().__init__()
        self.voice_handler = GoogleVoiceHandler()
        self._conversation_contexts: Dict[str, ConversationContext] = {}
        
    @traceable(name="voice_native_supervisor")
    async def execute(self, state: SearchState) -> SearchState:
        """
        Execute supervisor with voice-native processing
        
        This method extends the base supervisor to handle:
        1. Multi-modal inputs (voice + text)
        2. Voice metadata for routing
        3. Conversation context
        4. Voice-optimized responses
        """
        import time
        start = time.time()
        
        try:
            # Extract or create voice state
            voice_state = self._extract_voice_state(state)
            
            # Process multi-modal input if present
            if voice_state and voice_state.get("multi_modal_input"):
                state = await self._process_multimodal_input(state, voice_state)
            
            # Analyze with voice context
            analysis_result = await self._analyze_with_voice_context(state, voice_state)
            
            # Update state with voice-aware routing
            state["routing_decision"] = analysis_result["routing"]
            state["intent"] = analysis_result["intent"]
            state["confidence"] = analysis_result["confidence"]
            state["reasoning"].append(analysis_result["reasoning"])
            
            # Add voice-specific routing hints
            if voice_state:
                state["voice_routing_hints"] = self._generate_voice_routing_hints(
                    voice_state, 
                    analysis_result
                )
            
            # Generate voice response configuration if needed
            if voice_state and voice_state.get("voice_session"):
                voice_response = await self._prepare_voice_response(
                    state, 
                    voice_state,
                    analysis_result
                )
                state["voice_response"] = voice_response
            
        except Exception as e:
            logger.error(f"Voice supervisor error: {e}")
            state["error"] = str(e)
            state["routing_decision"] = "error"
        
        finally:
            elapsed = (time.time() - start) * 1000
            if 'agent_timings' not in state:
                state['agent_timings'] = {}
            state['agent_timings']['voice_supervisor'] = elapsed
            
        return state
    
    def _extract_voice_state(self, state: SearchState) -> Optional[Dict[str, Any]]:
        """Extract voice-related state from SearchState"""
        # Check if state has voice fields (future: when we update SearchState)
        voice_fields = {}
        
        # For now, check for voice metadata in state
        if hasattr(state, 'voice_metadata') or 'voice_metadata' in state:
            voice_fields['voice_metadata'] = state.get('voice_metadata')
            
        if hasattr(state, 'voice_session') or 'voice_session' in state:
            voice_fields['voice_session'] = state.get('voice_session')
            
        if hasattr(state, 'multi_modal_input') or 'multi_modal_input' in state:
            voice_fields['multi_modal_input'] = state.get('multi_modal_input')
            
        return voice_fields if voice_fields else None
    
    async def _process_multimodal_input(
        self, 
        state: SearchState, 
        voice_state: Dict[str, Any]
    ) -> SearchState:
        """Process multi-modal input and enrich state"""
        multi_modal = voice_state.get("multi_modal_input", {})
        
        # If voice input, use transcript as query
        if multi_modal.get("voice_transcript"):
            transcript = multi_modal["voice_transcript"]
            state["query"] = transcript["text"]
            
            # Add voice context to state
            state["voice_confidence"] = transcript["confidence"]
            state["detected_language"] = transcript["language_code"]
            
        # Extract conversation context
        session_id = voice_state.get("voice_session", {}).get("session_id")
        if session_id:
            state["conversation_context"] = self._get_conversation_context(session_id)
            
        return state
    
    async def _analyze_with_voice_context(
        self, 
        state: SearchState,
        voice_state: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze query with voice context for enhanced understanding
        
        Voice metadata influences:
        - Intent detection (urgency, emotion)
        - Routing decisions (fast pace → quick results)
        - Response style (empathetic, professional)
        """
        # Build enhanced prompt with voice context
        prompt = self._build_voice_aware_prompt(state, voice_state)
        
        try:
            # Use the LLM with voice context
            if hasattr(self.llm, 'generate_content'):
                # Vertex AI Gemini
                response = self.llm.generate_content(prompt)
                response_text = response.text
            else:
                # HuggingFace or other
                response_text = await self.llm.generate(prompt)
            
            # Parse response
            analysis = self._parse_supervisor_response(response_text)
            
            # Enhance with voice insights
            if voice_state:
                analysis = self._enhance_with_voice_insights(analysis, voice_state)
                
            return analysis
            
        except Exception as e:
            logger.error(f"Voice analysis error: {e}")
            return {
                "routing": "product_search",
                "intent": "search",
                "confidence": 0.5,
                "reasoning": f"Fallback due to error: {str(e)}"
            }
    
    def _build_voice_aware_prompt(
        self, 
        state: SearchState,
        voice_state: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt that includes voice context"""
        query = state["query"]
        
        # Base prompt
        prompt = f"""You are a voice-aware grocery shopping assistant supervisor.
        
User Query: "{query}"

"""
        
        # Add voice context if available
        if voice_state and voice_state.get("voice_metadata"):
            metadata = voice_state["voice_metadata"]
            prompt += f"""Voice Context:
- Speaking pace: {metadata.get('pace', 'normal')}
- Emotion: {metadata.get('emotion', 'neutral')}
- Clarity: {metadata.get('clarity', 'medium')}
- Language: {metadata.get('language_code', 'en-US')}
- Stress level: {metadata.get('stress_level', 'normal')}
- Hesitations: {metadata.get('hesitation_count', 0)}

"""
        
        # Add conversation context if available
        if state.get("conversation_context"):
            context = state["conversation_context"]
            prompt += f"""Conversation Context:
- Current topic: {context.get('current_topic', 'none')}
- Pending clarification: {context.get('pending_clarification', 'none')}
- User mood: {context.get('user_mood', 'neutral')}
- Incomplete tasks: {', '.join(context.get('incomplete_tasks', []))}

"""
        
        # Add routing instructions
        prompt += """Analyze this query considering the voice and conversation context.

Determine:
1. Intent: What does the user want? (search, order, help, clarify, general_chat)
2. Routing: Which agent should handle this? (product_search, order_agent, promotion_agent, response_compiler)
3. Confidence: How confident are you? (0.0-1.0)
4. Reasoning: Brief explanation
5. Voice hints: How should we respond? (brief/detailed, friendly/professional, slow/normal pace)

Consider:
- Fast pace + high urgency → Quick, direct responses
- Confusion/hesitation → Offer clarification
- Emotional state → Adjust response tone
- Language/culture → Appropriate product suggestions

Respond in JSON format:
{
    "intent": "...",
    "routing": "...",
    "confidence": 0.0,
    "reasoning": "...",
    "voice_response_hints": {
        "style": "friendly|professional|empathetic",
        "pace": "slow|normal|fast",
        "detail_level": "brief|normal|detailed"
    }
}
"""
        
        return prompt
    
    def _parse_supervisor_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response with voice hints"""
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    "routing": result.get("routing", "product_search"),
                    "intent": result.get("intent", "search"),
                    "confidence": float(result.get("confidence", 0.8)),
                    "reasoning": result.get("reasoning", ""),
                    "voice_response_hints": result.get("voice_response_hints", {})
                }
        except Exception as e:
            logger.error(f"Failed to parse voice supervisor response: {e}")
            
        # Fallback parsing
        return super()._parse_supervisor_response(response_text)
    
    def _enhance_with_voice_insights(
        self, 
        analysis: Dict[str, Any],
        voice_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhance analysis with voice-specific insights"""
        metadata = voice_state.get("voice_metadata", {})
        
        # Adjust routing based on voice signals
        if metadata.get("emotion") == "urgent" and metadata.get("pace") == "fast":
            # User seems in a hurry
            analysis["voice_insights"] = {
                "user_state": "hurried",
                "recommendation": "provide_quick_results",
                "max_results": 5
            }
            
        elif metadata.get("emotion") == "confused" and metadata.get("hesitation_count", 0) > 2:
            # User seems confused
            analysis["voice_insights"] = {
                "user_state": "confused",
                "recommendation": "offer_clarification",
                "response_type": "clarification"
            }
            # Maybe route to help instead
            if analysis["confidence"] < 0.7:
                analysis["routing"] = "response_compiler"
                analysis["intent"] = "clarify"
                
        elif metadata.get("emotion") == "frustrated":
            # User seems frustrated
            analysis["voice_insights"] = {
                "user_state": "frustrated",
                "recommendation": "empathetic_response",
                "response_style": "empathetic"
            }
            
        return analysis
    
    def _generate_voice_routing_hints(
        self, 
        voice_state: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate hints for downstream agents based on voice"""
        hints = {}
        metadata = voice_state.get("voice_metadata", {})
        
        # Search hints based on voice
        if analysis["routing"] == "product_search":
            # Fast pace → keyword search (lower alpha)
            # Slow pace → semantic search (higher alpha)
            if metadata.get("pace") == "fast":
                hints["suggested_alpha"] = 0.3
                hints["search_strategy"] = "keyword_focused"
            elif metadata.get("pace") == "slow":
                hints["suggested_alpha"] = 0.7
                hints["search_strategy"] = "semantic_focused"
            else:
                hints["suggested_alpha"] = 0.5
                hints["search_strategy"] = "balanced"
                
            # Result count based on user state
            if metadata.get("emotion") == "urgent":
                hints["max_results"] = 5
            else:
                hints["max_results"] = 10
                
        # Order hints based on voice
        elif analysis["routing"] == "order_agent":
            if metadata.get("emotion") == "confident":
                hints["confirmation_style"] = "brief"
            else:
                hints["confirmation_style"] = "detailed"
                
        # Response style hints
        hints["response_style"] = analysis.get("voice_response_hints", {})
        
        return hints
    
    async def _prepare_voice_response(
        self,
        state: SearchState,
        voice_state: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> VoiceResponse:
        """Prepare voice response configuration"""
        session_id = voice_state.get("voice_session", {}).get("session_id", "default")
        
        # Determine response style from analysis
        voice_hints = analysis.get("voice_response_hints", {})
        style = voice_hints.get("style", "normal")
        
        # Placeholder text - actual response comes from downstream agents
        text = f"Processing your {analysis['intent']} request..."
        
        # Generate voice response
        voice_response = await self.voice_handler.generate_voice_response(
            text=text,
            session_id=session_id,
            response_type=analysis["intent"],
            voice_metadata=voice_state.get("voice_metadata"),
            style_hint=style
        )
        
        return voice_response
    
    def _get_conversation_context(self, session_id: str) -> ConversationContext:
        """Get or create conversation context for session"""
        if session_id not in self._conversation_contexts:
            self._conversation_contexts[session_id] = ConversationContext(
                history=[],
                current_topic=None,
                pending_clarification=None,
                user_mood=None,
                engagement_level="medium",
                incomplete_tasks=[],
                confirmed_items=[]
            )
        return self._conversation_contexts[session_id]
    
    async def process_voice_stream(
        self,
        audio_generator: AsyncGenerator[bytes, None],
        session_id: str,
        existing_state: Optional[SearchState] = None
    ) -> AsyncGenerator[SearchState, None]:
        """
        Process streaming voice input and yield updated states
        
        This is the main entry point for voice conversations
        """
        async for multi_modal_input in self.voice_handler.process_voice_input(
            audio_generator, 
            session_id
        ):
            # Only process final transcripts
            if not multi_modal_input["voice_transcript"]["is_final"]:
                continue
                
            # Create or update state
            if existing_state:
                state = existing_state.copy()
            else:
                state = self._create_initial_state()
                
            # Add voice data to state
            state["multi_modal_input"] = multi_modal_input
            state["voice_metadata"] = multi_modal_input["voice_metadata"]
            state["voice_session"] = {
                "session_id": session_id,
                "start_time": datetime.utcnow(),
                "turn_count": 1,
                "is_active": True,
                "preferred_language": multi_modal_input["voice_metadata"]["language_code"],
                "detected_languages": [multi_modal_input["voice_metadata"]["language_code"]]
            }
            
            # Process through supervisor
            updated_state = await self.execute(state)
            
            yield updated_state
    
    def _create_initial_state(self) -> SearchState:
        """Create initial state for voice conversation"""
        from src.utils.id_generator import generate_request_id
        from datetime import datetime
        
        return SearchState(
            messages=[],
            query="",
            request_id=generate_request_id(),
            timestamp=datetime.utcnow(),
            alpha_value=0.5,
            search_strategy="hybrid",
            intent=None,
            next_action=None,
            confidence=0.0,
            routing_decision=None,
            should_search=False,
            search_params={},
            reasoning=[],
            search_results=[],
            search_metadata={},
            pending_tool_calls=[],
            completed_tool_calls=[],
            agent_status={},
            agent_timings={},
            total_execution_time=0.0,
            trace_id=None,
            final_response={},
            should_continue=True,
            error=None,
            enhanced_query=None,
            current_order={},
            order_metadata={},
            user_context=None,
            preferences=[],
            session_id=None
        )