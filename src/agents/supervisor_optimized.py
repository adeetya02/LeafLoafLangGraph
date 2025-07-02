"""
Optimized supervisor with aggressive caching and timeouts for <300ms
"""
from typing import Dict, Any, Optional
import asyncio
import time
import json
import os
import re
from langsmith import traceable
from src.agents.memory_aware_base import MemoryAwareAgent
from src.models.state import SearchState
from src.memory.graphiti_wrapper import GraphitiMemoryWrapper
from src.memory.memory_manager import memory_manager
from src.config.constants import (
    FAST_MODE, 
    SUPERVISOR_TIMEOUT_MS,
    SUPERVISOR_MAX_REASONING_STEPS
)
from src.tracing.voice_tracer import trace_voice_request, trace_supervisor_analysis, trace_voice_influence
import structlog

logger = structlog.get_logger()

# No hardcoded patterns - everything decided by LLM

class OptimizedSupervisorAgent(MemoryAwareAgent):
    """Voice-native supervisor with Gemma 2 9B and zero hardcoded patterns"""

    def __init__(self):
        super().__init__("supervisor")
        self.llm = self._init_gemma2_9b()
        self.graphiti_wrapper = GraphitiMemoryWrapper()
        self.memory = memory_manager.session_memory
        
    def _init_gemma2_9b(self):
        """Initialize Gemma 2 9B with environment-aware fallbacks"""
        # Detect environment - check for Cloud Run or App Engine specific vars
        is_gcp = os.getenv("K_SERVICE") or os.getenv("GAE_ENV") or os.getenv("K_REVISION")
        
        if is_gcp:
            logger.info("Running on GCP - trying Vertex AI Gemma first")
            # On GCP: Primary = Vertex AI Gemma, Fallback = HuggingFace
            
            # Try 1: Vertex AI Gemma models
            try:
                import vertexai
                from vertexai.generative_models import GenerativeModel, GenerationConfig
                
                project_id = os.getenv("GCP_PROJECT_ID", "leafloafai")
                location = os.getenv("GCP_LOCATION", "us-central1")
                vertexai.init(project=project_id, location=location)
                
                # Try available Gemini models
                # Try regular Gemini API first if key exists
                # Always try Gemini API first with hardcoded key
                gemini_key = "AIzaSyAGLGwNEXgoksFCawjU_x3pWMC-RFTlhPA"
                if gemini_key:
                    try:
                        import google.generativeai as genai
                        genai.configure(api_key=gemini_key)
                        
                        # Try different Gemini models
                        for model_name in ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']:
                            try:
                                model = genai.GenerativeModel(model_name)
                                # Test the model
                                test_response = model.generate_content("Say yes")
                                if test_response.text:
                                    logger.info(f"Using {model_name} via Google AI API on GCP")
                                    return model
                            except:
                                continue
                                
                    except Exception as e:
                        logger.debug(f"Gemini API failed: {e}")
                
                # Try Vertex AI models as fallback
                for model_name in ["gemini-pro", "gemini-1.0-pro", "text-bison"]:
                    try:
                        model = GenerativeModel(
                            model_name,
                            generation_config=GenerationConfig(
                                temperature=0.1,
                                max_output_tokens=150,
                                top_p=0.95,
                                top_k=20
                            )
                        )
                        logger.info(f"Successfully initialized {model_name} on Vertex AI")
                        return model
                    except Exception as model_error:
                        logger.debug(f"{model_name} not available: {model_error}")
                        continue
                        
                raise Exception("No Google AI models available")
                
            except Exception as vertex_error:
                logger.warning(f"Vertex AI failed: {vertex_error}")
                
                # Try 2: HuggingFace as fallback on GCP
                try:
                    hf_api_key = os.getenv("HUGGINGFACE_API_KEY")
                    if hf_api_key:
                        return self._init_huggingface_gemma(hf_api_key)
                except Exception as hf_error:
                    logger.warning(f"HuggingFace fallback failed: {hf_error}")
                    
        else:
            logger.info("Running locally - trying HuggingFace Gemma first")
            # Local: Primary = HuggingFace, Fallback = Vertex AI Gemini
            
            # Try 1: HuggingFace Gemma
            try:
                hf_api_key = os.getenv("HUGGINGFACE_API_KEY")
                if not hf_api_key:
                    raise ValueError("HUGGINGFACE_API_KEY not found")
                    
                return self._init_huggingface_gemma(hf_api_key)
                
            except Exception as hf_error:
                logger.warning(f"HuggingFace failed: {hf_error}")
                
                # Try 2: Google AI or Vertex AI as fallback
                try:
                    # Try regular Gemini API first
                    gemini_key = "AIzaSyAGLGwNEXgoksFCawjU_x3pWMC-RFTlhPA"
                    if gemini_key:
                        try:
                            import google.generativeai as genai
                            genai.configure(api_key=gemini_key)
                            
                            # Try different models
                            for model_name in ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']:
                                try:
                                    model = genai.GenerativeModel(model_name)
                                    test_response = model.generate_content("Say yes")
                                    if test_response.text:
                                        logger.info(f"Using {model_name} via Google AI API as fallback")
                                        return model
                                except:
                                    continue
                                    
                        except Exception as e:
                            logger.debug(f"Gemini API fallback failed: {e}")
                    
                    # Try Vertex AI if Gemini API fails
                    import vertexai
                    from vertexai.generative_models import GenerativeModel, GenerationConfig
                    
                    project_id = os.getenv("GCP_PROJECT_ID", "leafloafai")
                    location = os.getenv("GCP_LOCATION", "us-central1")
                    vertexai.init(project=project_id, location=location)
                    
                    # Try Gemini models that actually work
                    for model_name in ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]:
                        try:
                            model = GenerativeModel(
                                model_name,
                                generation_config=GenerationConfig(
                                    temperature=0.1,
                                    max_output_tokens=150,
                                    top_p=0.95,
                                    top_k=20
                                )
                            )
                            logger.info(f"Using {model_name} as local fallback")
                            return model
                        except:
                            continue
                    
                except Exception as vertex_error:
                    logger.warning(f"Vertex AI fallback failed: {vertex_error}")
                    
        # Try Groq as fallback
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            try:
                from groq import Groq
                client = Groq(api_key=groq_key)
                
                logger.info("Using Groq as final fallback")
                
                # Wrap Groq in our interface
                class GroqModel:
                    def __init__(self, client):
                        self.client = client
                        
                    def generate_content(self, prompt: str) -> Any:
                        try:
                            response = self.client.chat.completions.create(
                                model="mixtral-8x7b-32768",  # Fast and capable
                                messages=[{"role": "user", "content": prompt}],
                                temperature=0.1,
                                max_tokens=150
                            )
                            
                            class Response:
                                def __init__(self, text):
                                    self.text = text
                            
                            return Response(response.choices[0].message.content)
                        except Exception as e:
                            logger.error(f"Groq generation failed: {e}")
                            raise
                
                return GroqModel(client)
                
            except Exception as e:
                logger.warning(f"Groq fallback failed: {e}")
        
        # Final fallback - simple rule-based analyzer
        logger.warning("All LLM options failed, using simple rule-based analyzer")
        from src.integrations.simple_intent_analyzer import SimpleIntentAnalyzer
        return SimpleIntentAnalyzer()
    
    def _init_huggingface_gemma(self, api_key: str):
        """Initialize HuggingFace Gemma with Pro subscription"""
        from huggingface_hub import InferenceClient
        
        # Since you have Pro, use a dedicated inference endpoint or serverless API
        # Try using the Inference API directly without testing
        try:
            # Try multiple models in order of preference - Gemma models for Pro users
            models_to_try = [
                "google/gemma-2-9b-it",                   # Gemma 2 9B Instruct
                "google/gemma-2-9b",                      # Gemma 2 9B base
                "google/gemma-7b-it",                     # Gemma 7B Instruct
                "google/gemma-2b-it",                     # Gemma 2B Instruct (faster)
                "mistralai/Mistral-7B-Instruct-v0.3"     # Fallback
            ]
            
            client = InferenceClient(token=api_key)
            
            for model_id in models_to_try:
                try:
                    # Test the model with a simple query
                    test_response = client.text_generation(
                        "Hi",
                        model=model_id,
                        max_new_tokens=10
                    )
                    if test_response:
                        logger.info(f"Using {model_id} via HuggingFace Pro")
                        break
                except Exception as e:
                    logger.debug(f"{model_id} not available: {e}")
                    continue
            else:
                # If no model worked, use the most reliable one
                model_id = "mistralai/Mistral-7B-Instruct-v0.3"
                logger.info(f"Falling back to {model_id}")
            
            logger.info(f"Using {model_id} via HuggingFace Inference API")
            
            # Wrap in our interface
            class HFModel:
                def __init__(self, client, model_name):
                    self.client = client
                    self.model_name = model_name
                    
                def generate_content(self, prompt: str) -> Any:
                    try:
                        # Use the model parameter in the call
                        response = self.client.text_generation(
                            prompt,
                            model=self.model_name,
                            max_new_tokens=150,
                            temperature=0.1,
                            top_p=0.95,
                            do_sample=True,
                            return_full_text=False
                        )
                        
                        class Response:
                            def __init__(self, text):
                                self.text = text
                        
                        # Log the raw response for debugging
                        logger.debug(f"HuggingFace raw response: {response[:200]}")
                        return Response(response)
                    except Exception as e:
                        logger.error(f"HuggingFace {self.model_name} generation failed: {e}")
                        raise
            
            return HFModel(client, model_id)
            
        except Exception as e:
            logger.error(f"Failed to init HuggingFace: {e}")
            raise
    
    async def _get_agent_specific_context(self, user_id: str, session_id: str, query: str, base_context: Dict) -> Dict[str, Any]:
        """Get voice-specific patterns from Graphiti for routing decisions"""
        try:
            # Parallel fetch for performance
            tasks = []
            
            # Get voice patterns if available
            if hasattr(self.graphiti_wrapper, 'get_voice_patterns'):
                tasks.append(self.graphiti_wrapper.get_voice_patterns(user_id))
            else:
                tasks.append(asyncio.create_task(asyncio.sleep(0)))  # Placeholder
            
            # Get intent history
            if hasattr(self.graphiti_wrapper, 'get_intent_history'):
                tasks.append(self.graphiti_wrapper.get_intent_history(user_id, limit=5))
            else:
                tasks.append(asyncio.create_task(asyncio.sleep(0)))  # Placeholder
                
            # Get typical queries
            if hasattr(self.graphiti_wrapper, 'get_typical_queries'):
                tasks.append(self.graphiti_wrapper.get_typical_queries(user_id))
            else:
                tasks.append(asyncio.create_task(asyncio.sleep(0)))  # Placeholder
            
            # Wait with short timeout
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=0.05  # 50ms max
            )
            
            return {
                "voice_patterns": results[0] if not isinstance(results[0], Exception) else {},
                "intent_history": results[1] if not isinstance(results[1], Exception) else [],
                "typical_queries": results[2] if not isinstance(results[2], Exception) else [],
                "has_memory": not all(isinstance(r, Exception) for r in results)
            }
        except Exception as e:
            logger.debug(f"Failed to get agent context: {e}")
            return {"has_memory": False}
    
    async def analyze_with_voice_context(self, query: str, voice_metadata: Dict, memory_context: Dict) -> Dict[str, Any]:
        """Use Gemma 2 9B for voice-aware routing with zero patterns"""
        
        # Build comprehensive prompt
        prompt = f"""<task>
Analyze this voice query for a grocery shopping assistant.

Voice Context:
- Pace: {voice_metadata.get('pace', 'normal')} (slow/normal/fast)
- Emotion: {voice_metadata.get('emotion', 'neutral')}
- Volume: {voice_metadata.get('volume', 'normal')}
- Background noise: {voice_metadata.get('noise_level', 'quiet')}
- Speaking duration: {voice_metadata.get('duration', 0)}s

User said: "{query}"

Memory Context:
- Has previous interactions: {memory_context.get('has_memory', False)}
- Last intent: {memory_context.get('intent_history', [{}])[0].get('intent', 'none') if memory_context.get('intent_history') else 'none'}
- Common phrases: {memory_context.get('typical_queries', [])}

Determine the following and output as JSON:
{{
  "intent": "product_search|add_to_order|remove_from_order|update_order|list_order|confirm_order|promotion_query|general_chat",
  "confidence": 0.0-1.0,
  "search_alpha": 0.0-1.0,
  "urgency": "low|medium|high",
  "response_style": "brief|normal|detailed",
  "reasoning": "One sentence explanation",
  "voice_synthesis": {{
    "voice_type": "default|friendly|professional|empathetic|casual",
    "emotion": "neutral|excited|empathetic|informative|welcoming",
    "speaking_rate": 0.8-1.2,
    "pitch_adjustment": -2.0 to 2.0,
    "cultural_adaptation": "none|greeting|formal|casual",
    "adapted_text": "Only if cultural adaptation needed, otherwise null"
  }}
}}

Intent Guidelines:
- product_search: Looking for products, categories, or ideas
- add_to_order: Wants to add items to cart
- remove_from_order: Wants to remove items
- update_order: Changing quantities
- list_order: Viewing cart contents
- confirm_order: Checking out
- promotion_query: Asking about deals/discounts
- general_chat: Greetings or general questions

Search Alpha Guidelines (only for product_search):
- 0.0-0.3: Exact match needed (specific brands, SKUs)
- 0.4-0.6: Balanced search (general products)
- 0.7-1.0: Semantic/exploratory (ideas, suggestions)

Voice Pattern Rules:
- Fast pace + short query = high urgency
- Slow pace + hesitations = needs guidance (detailed response)
- Background noise = keep response brief
- Long speaking duration = user explaining context (normal response)
</task>

Output only valid JSON, no other text."""
        
        try:
            # Use appropriate method based on LLM type
            if hasattr(self.llm, 'generate_content'):
                # HuggingFace Gemma 2 or Vertex AI
                if asyncio.iscoroutinefunction(self.llm.generate_content):
                    response = await self.llm.generate_content(prompt)
                else:
                    # Run in executor to avoid blocking
                    loop = asyncio.get_event_loop()
                    
                    # Add timeout for Gemini API call
                    try:
                        logger.debug(f"Calling Gemini API with prompt length: {len(prompt)}")
                        logger.debug(f"First 200 chars of prompt: {prompt[:200]}")
                        response = await asyncio.wait_for(
                            loop.run_in_executor(
                                None,
                                self.llm.generate_content,
                                prompt
                            ),
                            timeout=10.0  # 10 second timeout
                        )
                        logger.debug(f"Gemini API returned, response type: {type(response)}")
                        logger.debug(f"Response attributes: {dir(response)}")
                    except asyncio.TimeoutError:
                        logger.error("Gemini API call timed out after 10 seconds")
                        raise
                    except Exception as e:
                        logger.error(f"Gemini API call failed: {e}", exc_info=True)
                        raise
                
                if not response:
                    logger.error("LLM returned None response")
                    raise ValueError("LLM returned None")
                
                if not hasattr(response, 'text'):
                    logger.error(f"LLM response has no text attribute. Type: {type(response)}, attrs: {dir(response)}")
                    raise ValueError("LLM response has no text attribute")
                    
                if not response.text:
                    logger.error(f"LLM returned empty text. Response: {response}")
                    raise ValueError("Empty LLM response text")
                    
                result_text = response.text.strip() if response.text else ""
                logger.info(f"Raw LLM response length: {len(result_text)}")
                logger.info(f"Raw LLM response: '{result_text[:500]}'")
                if not result_text:
                    logger.error(f"Empty LLM response! Response object: {response}, Has text: {hasattr(response, 'text')}, Text value: {response.text}")
            else:
                # Fallback client
                response = await self.llm.analyze_query(query, {"voice_metadata": voice_metadata})
                return response
            
            # Parse JSON response
            # Clean up the response text (remove any extra whitespace/newlines)
            cleaned_text = result_text.strip()
            
            # Remove markdown code blocks if present
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]  # Remove ```json
                if cleaned_text.endswith('```'):
                    cleaned_text = cleaned_text[:-3]  # Remove trailing ```
                cleaned_text = cleaned_text.strip()
            elif cleaned_text.startswith('```'):
                cleaned_text = cleaned_text[3:]  # Remove ```
                if cleaned_text.endswith('```'):
                    cleaned_text = cleaned_text[:-3]  # Remove trailing ```
                cleaned_text = cleaned_text.strip()
            
            # Try to extract JSON if there's extra text
            json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
            if json_match:
                cleaned_text = json_match.group(0)
            
            try:
                return json.loads(cleaned_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}")
                logger.error(f"JSON error position: line {e.lineno}, column {e.colno}")
                logger.error(f"Original text: '{result_text[:500] if result_text else 'NONE'}'")
                logger.error(f"Cleaned text: '{cleaned_text[:500] if cleaned_text else 'NONE'}'")
                logger.error(f"Response object: {response}")
                logger.error(f"Response has text: {hasattr(response, 'text')}")
                if hasattr(response, 'text'):
                    logger.error(f"Response.text is None: {response.text is None}")
                    logger.error(f"Response.text type: {type(response.text)}")
                    logger.error(f"Response.text repr: {repr(response.text)}")
                raise
            
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}", exc_info=True)
            # Log more details about the failure
            logger.error(f"LLM type: {type(self.llm).__name__}")
            logger.error(f"Query: {query}")
            logger.error(f"Voice metadata: {voice_metadata}")
            
            # Try to use SimpleIntentAnalyzer if we have it
            try:
                from src.integrations.simple_intent_analyzer import SimpleIntentAnalyzer
                if isinstance(self.llm, SimpleIntentAnalyzer):
                    # Already using simple analyzer, return emergency fallback
                    logger.warning("SimpleIntentAnalyzer also failed, using emergency fallback")
                else:
                    # Try simple analyzer
                    logger.info("Falling back to SimpleIntentAnalyzer")
                    simple_analyzer = SimpleIntentAnalyzer()
                    response = simple_analyzer.generate_content(prompt)
                    if response and hasattr(response, 'text') and response.text:
                        return json.loads(response.text)
            except Exception as fallback_error:
                logger.error(f"SimpleIntentAnalyzer fallback failed: {fallback_error}")
            
            # Emergency fallback
            return {
                "intent": "product_search",
                "confidence": 0.6,
                "search_alpha": 0.5,
                "urgency": "medium",
                "response_style": "normal",
                "reasoning": "Fallback due to LLM error",
                "voice_synthesis": {
                    "voice_type": "default",
                    "emotion": "neutral",
                    "speaking_rate": 1.0,
                    "pitch_adjustment": 0.0,
                    "cultural_adaptation": "none",
                    "adapted_text": None
                }
            }

    async def _run(self, state: SearchState) -> SearchState:
        """Voice-native query analysis with Gemma 2 9B - zero patterns"""
        
        start_time = time.time()
        query = state["query"]
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        
        # Extract voice metadata if available
        voice_metadata = state.get("voice_metadata", {})
        
        # Initialize voice_metadata in state if not present
        if "voice_metadata" not in state:
            state["voice_metadata"] = {}
        
        # Start voice tracing if voice metadata is present
        trace_id = None
        if voice_metadata and session_id:
            trace_id = trace_voice_request(session_id, user_id or "anonymous", query, voice_metadata)
            state["trace_id"] = trace_id
        
        # Log analysis start
        logger.info(f"🎙️ Voice-native analysis starting",
                   query=query[:50],
                   trace_id=trace_id,
                   voice_metadata=voice_metadata)
        
        # ALWAYS use LLM - no cache, no patterns
        try:
            # Get memory context in parallel (non-blocking)
            memory_task = asyncio.create_task(
                self.get_memory_context(user_id, session_id, query)
            )
            
            # Try to get memory with very short timeout
            try:
                memory_context = await asyncio.wait_for(memory_task, timeout=0.05)
            except asyncio.TimeoutError:
                logger.debug("Memory fetch timed out, proceeding without")
                memory_context = {"has_memory": False}
            
            # Adjust timeout based on voice urgency and environment
            is_gcp = os.getenv("K_SERVICE") or os.getenv("GAE_ENV") or os.getenv("K_REVISION")
            
            if is_gcp:
                # Shorter timeouts on GCP with better connectivity
                base_timeout = 0.25  # 250ms default
                if voice_metadata.get("pace") == "fast":
                    base_timeout = 0.20  # Faster for urgent users
                elif voice_metadata.get("pace") == "slow":
                    base_timeout = 0.30  # More time for thoughtful users
            else:
                # Longer timeouts for local development
                base_timeout = 2.0  # 2 seconds default
                if voice_metadata.get("pace") == "fast":
                    base_timeout = 1.5  # Still give reasonable time
                elif voice_metadata.get("pace") == "slow":
                    base_timeout = 2.5  # More time for thoughtful users
            
            # Analyze with Gemma 2 9B
            llm_task = asyncio.create_task(
                self.analyze_with_voice_context(query, voice_metadata, memory_context)
            )
            
            analysis = await asyncio.wait_for(llm_task, timeout=base_timeout)
            
            # Apply memory boost if available
            if memory_context.get("has_memory") and analysis.get("confidence", 0) < 0.9:
                analysis["confidence"] = min(1.0, analysis["confidence"] + 0.1)
                logger.debug(f"Applied memory boost: +0.1 confidence")
            
            # Extract results
            intent = analysis.get("intent", "product_search")
            confidence = analysis.get("confidence", 0.8)
            alpha = analysis.get("search_alpha", 0.5)
            urgency = analysis.get("urgency", "medium")
            response_style = analysis.get("response_style", "normal")
            voice_synthesis = analysis.get("voice_synthesis", {
                "voice_type": "default",
                "emotion": "neutral",
                "speaking_rate": 1.0,
                "pitch_adjustment": 0.0,
                "cultural_adaptation": "none",
                "adapted_text": None
            })
            
            # Trace supervisor analysis
            if trace_id:
                trace_supervisor_analysis(trace_id, {
                    "intent": intent,
                    "confidence": confidence,
                    "original_alpha": alpha,
                    "urgency": urgency,
                    "response_style": response_style,
                    "reasoning": analysis.get("reasoning", ""),
                    "voice_influence": {
                        "pace_impact": voice_metadata.get("pace"),
                        "emotion_impact": voice_metadata.get("emotion"),
                        "volume_impact": voice_metadata.get("volume")
                    }
                })
            reasoning = analysis.get("reasoning", "LLM analysis completed")
            
            elapsed = (time.time() - start_time) * 1000
            logger.info(
                f"Gemma 2 analysis: {elapsed:.0f}ms",
                intent=intent,
                confidence=confidence,
                alpha=alpha,
                urgency=urgency,
                voice_pace=voice_metadata.get("pace", "unknown")
            )
            
        except asyncio.TimeoutError:
            elapsed = (time.time() - start_time) * 1000
            logger.warning(f"LLM timeout at {elapsed:.0f}ms, using emergency fallback")
            
            # Emergency fallback - still no patterns!
            intent = "product_search"
            confidence = 0.6
            alpha = 0.5
            urgency = "medium"
            response_style = "normal"
            reasoning = "LLM timeout - using safe defaults"
            voice_synthesis = {
                "voice_type": "default",
                "emotion": "neutral",
                "speaking_rate": 1.0,
                "pitch_adjustment": 0.0,
                "cultural_adaptation": "none",
                "adapted_text": None
            }
            
        except Exception as e:
            logger.error(f"LLM error: {e}")
            intent = "product_search"
            confidence = 0.5
            alpha = 0.5
            urgency = "medium"
            response_style = "normal"
            reasoning = f"LLM error: {str(e)}"
            voice_synthesis = {
                "voice_type": "default",
                "emotion": "neutral",
                "speaking_rate": 1.0,
                "pitch_adjustment": 0.0,
                "cultural_adaptation": "none",
                "adapted_text": None
            }
        
        # Update state with results
        state["intent"] = intent
        state["confidence"] = confidence
        state["enhanced_query"] = query
        state["search_params"]["alpha"] = alpha
        state["voice_metadata"]["urgency"] = urgency
        state["voice_metadata"]["response_style"] = response_style
        
        # Add voice synthesis parameters for TTS
        state["voice_synthesis_params"] = voice_synthesis
        
        elapsed = (time.time() - start_time) * 1000
        state["reasoning"].append(f"Voice-native ({elapsed:.0f}ms): {reasoning}")
        
        # Record decision for learning
        asyncio.create_task(self.record_decision(
            decision={
                "intent": intent,
                "confidence": confidence,
                "alpha": alpha,
                "urgency": urgency
            },
            context={
                "query": query,
                "voice_metadata": voice_metadata,
                "elapsed_ms": elapsed
            }
        ))
        
        return self._finalize_routing(state, elapsed)

    def _finalize_routing(self, state: SearchState, elapsed_ms: float) -> SearchState:
        """Finalize routing and add timing"""
        # Add timing
        if "agent_timings" not in state:
            state["agent_timings"] = {}
        state["agent_timings"]["supervisor"] = elapsed_ms
        
        # Route based on intent
        intent = state.get("intent", "product_search")
        
        if intent in ["add_to_order", "remove_from_order", "update_order", "list_order", "confirm_order"]:
            routing = "order_agent"
        elif intent in ["promotion_query", "apply_promotion"]:
            routing = "promotion_agent"
        elif intent == "general_chat":
            routing = "general_chat"
        else:
            routing = "product_search"
        
        state["routing_decision"] = routing
        state["should_search"] = routing == "product_search"
        state["is_general_chat"] = routing == "general_chat"
        
        # Prepare search params if needed
        if state["should_search"]:
            state["search_params"].update({
                "original_query": state.get("enhanced_query", state["query"]),
                "intent": intent,
                "alpha": state["search_params"].get("alpha", 0.5)
            })
        
        # Add routing message
        state["messages"].append({
            "role": "assistant",
            "content": f"[Routing to {routing}]",
            "tool_calls": None,
            "tool_call_id": None
        })
        
        return state