# Voice Analytics Implementation Plan

## Phase 1: Enhanced Metadata Collection (Immediate)

### 1. Update voice_streaming_debug.py

```python
# Add to voice_streaming_debug.py
from src.voice.holistic_analyzer import HolisticVoiceAnalyzer

class EnhancedVoiceListener:
    def __init__(self):
        self.holistic_analyzer = HolisticVoiceAnalyzer()
        self.voice_buffer = []
        self.audio_analyzer = AudioAnalyzer()  # For pitch/volume analysis
        
    async def on_utterance_end(self, *args, **kwargs):
        # Basic metrics (existing)
        duration = time.time() - self.speech_started_time
        words = self.current_utterance.split()
        word_count = len(words)
        
        # Enhanced metrics
        audio_features = self.audio_analyzer.analyze(self.voice_buffer)
        
        # Build comprehensive metadata
        voice_metadata = {
            # Basic (existing)
            "duration": duration,
            "word_count": word_count,
            "transcript": self.current_utterance,
            
            # Enhanced pace analysis
            "pace": self._calculate_pace(word_count, duration),
            "pace_variance": audio_features.get("pace_variance", 0),
            
            # Audio characteristics
            "pitch_mean": audio_features.get("pitch_mean", 100),
            "pitch_variance": audio_features.get("pitch_variance", 0),
            "volume_mean": audio_features.get("volume_mean", 60),
            "volume_variance": audio_features.get("volume_variance", 0),
            
            # Speech patterns
            "hesitations": self._count_hesitations(self.current_utterance),
            "self_corrections": self._count_corrections(self.current_utterance),
            "pause_ratio": audio_features.get("pause_ratio", 0),
            
            # Quality metrics
            "clarity_score": audio_features.get("clarity_score", 1.0),
            "background_noise": audio_features.get("noise_level", 0),
            "confidence_markers": self._extract_confidence_markers(self.current_utterance)
        }
        
        # Run holistic analysis
        context = await self._get_user_context()
        holistic_results = await self.holistic_analyzer.analyze(
            self.current_utterance,
            voice_metadata,
            context
        )
        
        # Merge results
        voice_metadata["holistic_analysis"] = holistic_results
        
        return voice_metadata
```

### 2. Create Holistic Analyzer Module

```python
# src/voice/holistic_analyzer.py
import asyncio
from typing import Dict, List, Any
import re

class HolisticVoiceAnalyzer:
    """Universal voice analytics for all users"""
    
    def __init__(self):
        self.query_analyzer = QuerySpecificityAnalyzer()
        self.confidence_analyzer = ConfidenceAnalyzer()
        self.mode_detector = ShoppingModeDetector()
        self.complexity_analyzer = ComplexityAnalyzer()
        self.emotion_detector = EmotionDetector()
    
    async def analyze(
        self, 
        transcript: str, 
        voice_metadata: Dict[str, Any],
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform comprehensive voice analysis
        Returns insights that work for all ethnic communities
        """
        
        # Run analyzers in parallel for performance
        tasks = [
            self.query_analyzer.analyze(transcript, voice_metadata),
            self.confidence_analyzer.analyze(transcript, voice_metadata),
            self.mode_detector.detect(transcript, voice_metadata, user_context),
            self.complexity_analyzer.analyze(transcript),
            self.emotion_detector.detect(voice_metadata, transcript)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Combine insights
        analysis = {
            "query_specificity": results[0],
            "confidence_level": results[1], 
            "shopping_mode": results[2],
            "intent_complexity": results[3],
            "emotional_state": results[4],
            
            # Derived insights
            "needs_guidance": results[0]["score"] < 0.3 or results[1]["level"] == "low",
            "is_urgent": results[2] == "emergency" or voice_metadata.get("pace") == "fast",
            "response_style": self._determine_response_style(results),
            "search_parameters": self._optimize_search_params(results)
        }
        
        return analysis
```

## Phase 2: Supervisor Integration

### Update supervisor_optimized.py

```python
# Modify analyze_with_voice_context method
async def analyze_with_voice_context(self, query: str, voice_metadata: Dict, memory_context: Dict) -> Dict[str, Any]:
    """Enhanced voice-aware routing with holistic analysis"""
    
    # Get holistic analysis if available
    holistic = voice_metadata.get("holistic_analysis", {})
    
    # Build enhanced prompt
    prompt = f"""<task>
Analyze this voice query for a grocery shopping assistant.

Query: "{query}"

Holistic Voice Analysis:
- Query Specificity: {holistic.get('query_specificity', {}).get('level', 'unknown')} ({holistic.get('query_specificity', {}).get('score', 0):.2f})
- Confidence Level: {holistic.get('confidence_level', {}).get('level', 'unknown')} 
- Shopping Mode: {holistic.get('shopping_mode', 'unknown')}
- Intent Complexity: {holistic.get('intent_complexity', {}).get('level', 'unknown')}
- Emotional State: {holistic.get('emotional_state', {}).get('state', 'neutral')}
- Needs Guidance: {holistic.get('needs_guidance', False)}
- Is Urgent: {holistic.get('is_urgent', False)}

Voice Characteristics:
- Pace: {voice_metadata.get('pace', 'normal')} (variance: {voice_metadata.get('pace_variance', 0):.2f})
- Clarity: {voice_metadata.get('clarity_score', 1.0):.2f}
- Hesitations: {voice_metadata.get('hesitations', 0)}
- Background Noise: {voice_metadata.get('background_noise', 0)}

Memory Context:
- Previous Interactions: {memory_context.get('has_memory', False)}
- Usual Shopping Pattern: {memory_context.get('shopping_pattern', 'unknown')}

Determine routing and parameters:
{{
  "intent": "product_search|add_to_order|...",
  "confidence": 0.0-1.0,
  "search_alpha": 0.0-1.0,
  "response_parameters": {{
    "style": "brief|normal|detailed|guided",
    "tone": "professional|friendly|empathetic|efficient",
    "provide_examples": true/false,
    "offer_alternatives": true/false
  }},
  "reasoning": "explanation"
}}

Guidelines:
- For vague queries (specificity < 0.3): Increase alpha, offer categories
- For low confidence: Provide guidance and examples
- For urgent/emergency: Minimize options, prioritize speed
- For complex intents: Break down into steps
- For confused emotional state: Simplify and clarify
</task>

Output only valid JSON."""
```

## Phase 3: Agent Voice Awareness

### 1. Product Search Agent Enhancement

```python
# In product_search.py
async def _adjust_search_for_voice(self, search_params: Dict, voice_metadata: Dict) -> Dict:
    """Adjust search based on holistic voice analysis"""
    
    holistic = voice_metadata.get("holistic_analysis", {})
    
    # Universal adjustments based on holistic analysis
    
    # Query specificity adjustments
    specificity = holistic.get("query_specificity", {}).get("score", 0.5)
    if specificity < 0.3:
        # Very vague - show categories and suggestions
        search_params["show_categories"] = True
        search_params["include_suggestions"] = True
        search_params["limit"] = 15  # More options
    elif specificity > 0.8:
        # Very specific - precise matching
        search_params["exact_match_boost"] = 2.0
        search_params["limit"] = 10  # Fewer, more relevant options
    
    # Shopping mode adjustments
    mode = holistic.get("shopping_mode", "general")
    if mode == "quick_grab":
        search_params["boost_previous_purchases"] = True
        search_params["limit"] = 5
    elif mode == "exploration":
        search_params["include_new_products"] = True
        search_params["diversity_boost"] = True
        search_params["limit"] = 20
    elif mode == "meal_planning":
        search_params["group_by_meal_type"] = True
        search_params["include_recipes"] = True
    elif mode == "emergency":
        search_params["availability_required"] = True
        search_params["fastest_delivery"] = True
    
    # Confidence adjustments
    confidence = holistic.get("confidence_level", {}).get("overall", 0.5)
    if confidence < 0.4:
        search_params["fuzzy_matching"] = True
        search_params["synonym_expansion"] = True
    
    # Complexity adjustments
    if holistic.get("intent_complexity", {}).get("level") == "complex":
        search_params["multi_step_search"] = True
        search_params["preserve_context"] = True
    
    return search_params
```

### 2. Order Agent Enhancement

```python
# In order_agent.py
async def _suggest_quantity_from_voice(self, product: Dict, voice_analysis: Dict) -> int:
    """Suggest quantities based on holistic voice analysis"""
    
    # Universal quantity logic
    mode = voice_analysis.get("shopping_mode", "general")
    specificity = voice_analysis.get("query_specificity", {}).get("score", 0.5)
    
    if mode == "bulk_shopping":
        return self._get_bulk_quantity(product)
    elif mode == "quick_grab" and specificity > 0.7:
        # Confident quick shopping - use usual quantity
        return self._get_usual_quantity(product)
    elif voice_analysis.get("needs_guidance", False):
        # Uncertain - suggest standard size
        return 1
    else:
        return self._get_default_quantity(product)

async def _adapt_response_style(self, voice_analysis: Dict) -> Dict:
    """Adapt order confirmation style based on voice"""
    
    emotion = voice_analysis.get("emotional_state", {}).get("state", "neutral")
    complexity = voice_analysis.get("intent_complexity", {}).get("level", "simple")
    
    if emotion == "rushed":
        return {
            "style": "brief",
            "skip_details": True,
            "auto_confirm": True
        }
    elif emotion == "confused" or complexity == "complex":
        return {
            "style": "step_by_step",
            "confirm_each": True,
            "provide_summaries": True
        }
    else:
        return {
            "style": "normal",
            "show_totals": True
        }
```

## Phase 4: Response Compilation

### Enhanced Response Compiler

```python
# In response_compiler.py
def compile_with_voice_adaptation(self, results: Dict, voice_analysis: Dict) -> str:
    """Compile response adapted to voice analysis"""
    
    # Get response parameters
    style = voice_analysis.get("response_style", "normal")
    needs_guidance = voice_analysis.get("needs_guidance", False)
    emotional_state = voice_analysis.get("emotional_state", {}).get("state", "neutral")
    
    # Adapt response format
    if style == "brief":
        return self._compile_brief_response(results)
    elif style == "guided":
        return self._compile_guided_response(results)
    elif emotional_state == "confused":
        return self._compile_clarifying_response(results)
    else:
        return self._compile_standard_response(results)

def _compile_guided_response(self, results: Dict) -> str:
    """Create guided response for users needing help"""
    
    response_parts = []
    
    # Start with reassurance
    response_parts.append("I can help you find what you're looking for.")
    
    # Provide categories if search was vague
    if results.get("show_categories"):
        response_parts.append("\nHere are some categories that might help:")
        for category in results.get("categories", [])[:5]:
            response_parts.append(f"• {category}")
    
    # Show top matches with explanations
    response_parts.append("\nBased on your request, here are some options:")
    for i, product in enumerate(results.get("products", [])[:5], 1):
        response_parts.append(
            f"{i}. {product['name']} - {product.get('description', '')}"
        )
    
    # Offer next steps
    response_parts.append("\nWould you like to add any of these, or see more options?")
    
    return "\n".join(response_parts)
```

## Testing Strategy

### 1. Unit Tests for Each Analyzer

```python
# tests/test_holistic_analyzers.py
import pytest
from src.voice.holistic_analyzer import QuerySpecificityAnalyzer

class TestQuerySpecificity:
    def test_specific_queries(self):
        analyzer = QuerySpecificityAnalyzer()
        
        # Very specific query
        result = analyzer.analyze(
            "Organic Whole Foods 365 milk 1 gallon",
            {"pace": "normal"}
        )
        assert result["score"] > 0.8
        assert result["level"] == "specific"
        
    def test_vague_queries(self):
        analyzer = QuerySpecificityAnalyzer()
        
        # Very vague query
        result = analyzer.analyze(
            "um... something for dinner maybe?",
            {"hesitations": 3}
        )
        assert result["score"] < 0.3
        assert result["level"] == "vague"
```

### 2. Integration Tests

```python
# tests/test_voice_integration.py
async def test_holistic_voice_flow():
    """Test complete voice flow with holistic analysis"""
    
    # Simulate voice input
    voice_input = {
        "transcript": "I need milk and... uh... what else do I usually get?",
        "voice_metadata": {
            "pace": "slow",
            "hesitations": 2,
            "duration": 4.5,
            "clarity_score": 0.8
        }
    }
    
    # Process through pipeline
    result = await process_voice_request(voice_input)
    
    # Verify holistic analysis was applied
    assert result["holistic_analysis"]["query_specificity"]["level"] == "moderate"
    assert result["holistic_analysis"]["needs_guidance"] == True
    assert result["search_params"]["include_suggestions"] == True
    assert "usual" in result["response"]  # Should include usual items
```

## Rollout Plan

### Week 1: Foundation
1. Implement holistic analyzer classes
2. Add to voice_streaming_debug.py
3. Test with diverse voice samples

### Week 2: Integration  
1. Update supervisor with holistic awareness
2. Enhance agents with voice adaptations
3. Test end-to-end flows

### Week 3: Refinement
1. Tune thresholds based on real usage
2. Add analytics tracking
3. A/B test response adaptations

### Week 4: Production
1. Deploy with feature flags
2. Monitor performance metrics
3. Iterate based on user feedback