# Holistic Voice Analytics Framework

## Design Philosophy
Design for universal human shopping patterns, not specific ethnic groups. Focus on behavioral and communication patterns that transcend cultural boundaries.

## Core Voice Metrics (Universal)

### 1. Query Specificity Score (0.0-1.0)
Measures how specific vs vague the query is, universally applicable.

```python
class QuerySpecificity:
    def analyze(self, transcript: str, voice_metadata: Dict) -> float:
        """Universal specificity analysis"""
        
        indicators = {
            # Specific indicators (any language/culture)
            "brand_mentioned": bool(re.search(r'\b[A-Z][a-z]+\b', transcript)),
            "quantity_mentioned": bool(re.search(r'\d+', transcript)),
            "size_mentioned": bool(re.search(r'(small|medium|large|\d+oz|\d+g|\d+ml)', transcript.lower())),
            "exact_product": len(transcript.split()) < 5 and not any(vague in transcript.lower() for vague in ['something', 'anything', 'stuff']),
            
            # Vague indicators (universal)
            "exploratory_words": any(word in transcript.lower() for word in [
                'something', 'anything', 'maybe', 'possibly', 'options',
                'what do you have', 'show me', 'looking for'
            ]),
            "question_marks": transcript.count('?'),
            "hesitation_sounds": len(re.findall(r'\b(um|uh|hmm|err|ah)\b', transcript.lower()))
        }
        
        # Calculate score
        specific_count = sum([
            indicators['brand_mentioned'],
            indicators['quantity_mentioned'], 
            indicators['size_mentioned'],
            indicators['exact_product']
        ])
        
        vague_count = sum([
            indicators['exploratory_words'],
            indicators['question_marks'] > 0,
            indicators['hesitation_sounds'] > 2
        ])
        
        specificity = (specific_count - vague_count) / 4.0
        return max(0.0, min(1.0, (specificity + 1.0) / 2.0))
```

### 2. Confidence Level Analysis
Universal markers of certainty vs uncertainty in voice.

```python
class ConfidenceAnalysis:
    def analyze(self, transcript: str, voice_metadata: Dict) -> Dict:
        """Analyze speaker confidence universally"""
        
        # Universal confidence markers
        high_confidence = [
            'definitely', 'exactly', 'specifically', 'always', 'usually',
            'need', 'want', 'get me', 'give me', 'add'
        ]
        
        low_confidence = [
            'maybe', 'perhaps', 'possibly', 'might', 'could',
            'not sure', 'i think', 'probably', 'or something'
        ]
        
        # Voice characteristics (universal)
        voice_confidence = {
            "steady_pace": voice_metadata.get('pace_variance', 0) < 0.2,
            "clear_articulation": voice_metadata.get('clarity_score', 0) > 0.7,
            "minimal_pauses": voice_metadata.get('pause_ratio', 0) < 0.1,
            "consistent_volume": voice_metadata.get('volume_variance', 0) < 0.3
        }
        
        # Calculate scores
        text_confidence = (
            sum(1 for word in high_confidence if word in transcript.lower()) -
            sum(1 for word in low_confidence if word in transcript.lower())
        ) / max(len(transcript.split()), 1)
        
        voice_score = sum(voice_confidence.values()) / len(voice_confidence)
        
        return {
            "overall_confidence": (text_confidence + voice_score) / 2,
            "text_confidence": text_confidence,
            "voice_confidence": voice_score,
            "confidence_level": self._categorize_confidence((text_confidence + voice_score) / 2)
        }
    
    def _categorize_confidence(self, score: float) -> str:
        if score > 0.7: return "high"
        elif score > 0.4: return "medium"
        else: return "low"
```

### 3. Shopping Mode Detection
Universal shopping patterns that apply to all users.

```python
class ShoppingModeDetector:
    def detect_mode(self, transcript: str, voice_metadata: Dict, context: Dict) -> str:
        """Detect universal shopping modes"""
        
        modes = {
            "quick_grab": {
                "indicators": [
                    voice_metadata.get('pace') == 'fast',
                    voice_metadata.get('duration', 10) < 3,
                    any(word in transcript.lower() for word in ['usual', 'regular', 'always get']),
                    context.get('time_of_day') in ['early_morning', 'late_evening']
                ],
                "weight": 0.8
            },
            
            "meal_planning": {
                "indicators": [
                    'dinner' in transcript.lower() or 'lunch' in transcript.lower(),
                    'recipe' in transcript.lower() or 'cooking' in transcript.lower(),
                    'ingredients' in transcript.lower(),
                    voice_metadata.get('duration', 0) > 5,
                    len(transcript.split(',')) > 2  # Multiple items
                ],
                "weight": 0.9
            },
            
            "bulk_shopping": {
                "indicators": [
                    any(word in transcript.lower() for word in ['bulk', 'stock up', 'wholesale']),
                    re.search(r'\b\d{2,}\b', transcript),  # Large quantities
                    'case of' in transcript.lower(),
                    context.get('days_since_last_order', 0) > 14
                ],
                "weight": 0.85
            },
            
            "exploration": {
                "indicators": [
                    voice_metadata.get('pace') == 'slow',
                    any(word in transcript.lower() for word in ['what', 'show', 'options', 'new']),
                    voice_metadata.get('hesitations', 0) > 2,
                    '?' in transcript
                ],
                "weight": 0.7
            },
            
            "emergency": {
                "indicators": [
                    voice_metadata.get('emotion') in ['stressed', 'urgent'],
                    any(word in transcript.lower() for word in ['now', 'urgent', 'asap', 'quickly']),
                    voice_metadata.get('volume') == 'loud',
                    context.get('time_of_day') == 'late_night'
                ],
                "weight": 0.95
            }
        }
        
        # Score each mode
        mode_scores = {}
        for mode, config in modes.items():
            score = sum(config['indicators']) / len(config['indicators'])
            mode_scores[mode] = score * config['weight']
        
        # Return highest scoring mode
        return max(mode_scores.items(), key=lambda x: x[1])[0]
```

### 4. Intent Complexity Analysis
How complex is what the user is trying to accomplish?

```python
class IntentComplexity:
    def analyze(self, transcript: str, voice_metadata: Dict) -> Dict:
        """Analyze complexity of user intent"""
        
        # Universal complexity indicators
        complexity_factors = {
            "multiple_items": len(re.split(r'[,;]|and', transcript)) > 1,
            "conditional_logic": any(word in transcript.lower() for word in ['if', 'but', 'except', 'unless']),
            "comparisons": any(word in transcript.lower() for word in ['better', 'cheaper', 'versus', 'or']),
            "specific_requirements": any(word in transcript.lower() for word in ['organic', 'gluten-free', 'sugar-free', 'vegan']),
            "quantity_calculations": bool(re.search(r'\d+\s*(for|per|each)', transcript.lower())),
            "substitutions": 'instead' in transcript.lower() or 'replace' in transcript.lower()
        }
        
        complexity_score = sum(complexity_factors.values()) / len(complexity_factors)
        
        return {
            "complexity_score": complexity_score,
            "complexity_level": self._categorize_complexity(complexity_score),
            "factors": {k: v for k, v in complexity_factors.items() if v},
            "recommended_response": self._recommend_response(complexity_score)
        }
    
    def _categorize_complexity(self, score: float) -> str:
        if score > 0.6: return "complex"
        elif score > 0.3: return "moderate"
        else: return "simple"
    
    def _recommend_response(self, score: float) -> str:
        if score > 0.6: return "detailed_guided"
        elif score > 0.3: return "structured_options"
        else: return "quick_direct"
```

### 5. Emotional State Detection
Universal emotional indicators in voice.

```python
class EmotionalStateDetector:
    def detect_state(self, voice_metadata: Dict, transcript: str) -> Dict:
        """Detect emotional state from universal voice markers"""
        
        states = {
            "neutral": {
                "pitch_variance": (0.8, 1.2),
                "pace": "normal",
                "volume": "normal",
                "keywords": []
            },
            
            "happy/excited": {
                "pitch_variance": (1.1, 1.5),
                "pace": "fast",
                "volume": "normal_to_loud",
                "keywords": ['great', 'awesome', 'love', 'perfect', 'excited']
            },
            
            "frustrated": {
                "pitch_variance": (0.9, 1.3),
                "pace": "variable",
                "volume": "loud",
                "keywords": ['again', 'always', 'never', 'why', 'come on']
            },
            
            "confused": {
                "pitch_variance": (1.0, 1.4),
                "pace": "slow",
                "volume": "normal",
                "keywords": ['what', 'which', 'how', 'where', "don't understand"]
            },
            
            "rushed": {
                "pitch_variance": (0.9, 1.1),
                "pace": "fast",
                "volume": "normal_to_loud",
                "keywords": ['quick', 'hurry', 'fast', 'now']
            }
        }
        
        # Match against patterns
        detected_state = "neutral"
        max_score = 0
        
        for state, patterns in states.items():
            score = 0
            
            # Voice matching
            if voice_metadata.get('pitch_ratio', 1.0) >= patterns['pitch_variance'][0] and \
               voice_metadata.get('pitch_ratio', 1.0) <= patterns['pitch_variance'][1]:
                score += 0.3
            
            if voice_metadata.get('pace') == patterns['pace']:
                score += 0.3
                
            if patterns['volume'] in ['normal', voice_metadata.get('volume')]:
                score += 0.2
            
            # Keyword matching
            keyword_matches = sum(1 for kw in patterns['keywords'] if kw in transcript.lower())
            score += min(0.2, keyword_matches * 0.05)
            
            if score > max_score:
                max_score = score
                detected_state = state
        
        return {
            "emotional_state": detected_state,
            "confidence": max_score,
            "response_adaptation": self._get_response_style(detected_state)
        }
    
    def _get_response_style(self, state: str) -> Dict:
        styles = {
            "neutral": {"tone": "informative", "pace": "normal", "detail": "standard"},
            "happy/excited": {"tone": "enthusiastic", "pace": "upbeat", "detail": "enhanced"},
            "frustrated": {"tone": "calming", "pace": "steady", "detail": "concise"},
            "confused": {"tone": "patient", "pace": "slow", "detail": "step_by_step"},
            "rushed": {"tone": "efficient", "pace": "quick", "detail": "minimal"}
        }
        return styles.get(state, styles["neutral"])
```

### 6. Context Extraction
Universal context understanding from voice patterns.

```python
class ContextExtractor:
    def extract_context(self, transcript: str, voice_metadata: Dict, session_data: Dict) -> Dict:
        """Extract universal shopping context"""
        
        context = {
            "shopping_occasion": self._detect_occasion(transcript),
            "urgency_level": self._calculate_urgency(voice_metadata, transcript),
            "decision_style": self._detect_decision_style(voice_metadata, transcript),
            "assistance_needed": self._assess_assistance_need(voice_metadata, transcript),
            "preference_indicators": self._extract_preferences(transcript)
        }
        
        return context
    
    def _detect_occasion(self, transcript: str) -> str:
        """Detect shopping occasion from universal markers"""
        occasions = {
            "daily_essentials": ['milk', 'bread', 'eggs', 'usual', 'regular'],
            "special_meal": ['dinner', 'guests', 'recipe', 'special', 'party'],
            "health_focused": ['organic', 'healthy', 'diet', 'nutrition', 'vitamins'],
            "convenience": ['quick', 'easy', 'ready', 'frozen', 'instant'],
            "exploration": ['new', 'try', 'different', 'options', 'what do you have']
        }
        
        for occasion, keywords in occasions.items():
            if any(kw in transcript.lower() for kw in keywords):
                return occasion
        
        return "general_shopping"
    
    def _calculate_urgency(self, voice_metadata: Dict, transcript: str) -> float:
        """Calculate urgency from universal indicators"""
        urgency_score = 0.0
        
        # Voice indicators
        if voice_metadata.get('pace') == 'fast': urgency_score += 0.3
        if voice_metadata.get('volume') == 'loud': urgency_score += 0.2
        if voice_metadata.get('duration', 10) < 3: urgency_score += 0.2
        
        # Text indicators
        urgent_words = ['now', 'quick', 'asap', 'urgent', 'hurry', 'fast']
        urgency_score += min(0.3, sum(0.1 for word in urgent_words if word in transcript.lower()))
        
        return min(1.0, urgency_score)
```

## Integration with Voice Pipeline

```python
class HolisticVoiceAnalyzer:
    def __init__(self):
        self.specificity_analyzer = QuerySpecificity()
        self.confidence_analyzer = ConfidenceAnalysis()
        self.mode_detector = ShoppingModeDetector()
        self.complexity_analyzer = IntentComplexity()
        self.emotion_detector = EmotionalStateDetector()
        self.context_extractor = ContextExtractor()
    
    async def analyze(self, transcript: str, voice_metadata: Dict, context: Dict) -> Dict:
        """Perform holistic voice analysis"""
        
        # Run all analyzers in parallel
        results = await asyncio.gather(
            self.specificity_analyzer.analyze(transcript, voice_metadata),
            self.confidence_analyzer.analyze(transcript, voice_metadata),
            self.mode_detector.detect_mode(transcript, voice_metadata, context),
            self.complexity_analyzer.analyze(transcript, voice_metadata),
            self.emotion_detector.detect_state(voice_metadata, transcript),
            self.context_extractor.extract_context(transcript, voice_metadata, context)
        )
        
        # Combine results
        holistic_analysis = {
            "specificity_score": results[0],
            "confidence_analysis": results[1],
            "shopping_mode": results[2],
            "intent_complexity": results[3],
            "emotional_state": results[4],
            "context": results[5],
            
            # Derived insights
            "recommended_actions": self._recommend_actions(results),
            "search_strategy": self._determine_search_strategy(results),
            "response_parameters": self._calculate_response_params(results)
        }
        
        return holistic_analysis
    
    def _recommend_actions(self, results: List) -> List[str]:
        """Recommend actions based on holistic analysis"""
        actions = []
        
        specificity = results[0]
        confidence = results[1]['overall_confidence']
        mode = results[2]
        complexity = results[3]['complexity_level']
        emotion = results[4]['emotional_state']
        
        # Universal recommendations
        if specificity < 0.3:
            actions.append("show_categories")
            actions.append("offer_suggestions")
        
        if confidence < 0.4:
            actions.append("provide_guidance")
            actions.append("ask_clarifying_questions")
        
        if mode == "emergency":
            actions.append("prioritize_speed")
            actions.append("show_available_now")
        
        if complexity == "complex":
            actions.append("break_down_request")
            actions.append("handle_step_by_step")
        
        if emotion == "confused":
            actions.append("simplify_options")
            actions.append("provide_examples")
        
        return actions
    
    def _determine_search_strategy(self, results: List) -> Dict:
        """Determine optimal search strategy"""
        specificity = results[0]
        confidence = results[1]['overall_confidence']
        mode = results[2]
        
        # Calculate search alpha based on holistic analysis
        if specificity > 0.8 and confidence > 0.7:
            # Very specific and confident - keyword focus
            alpha = 0.2
        elif specificity < 0.3 or mode == "exploration":
            # Vague or exploring - semantic focus
            alpha = 0.8
        else:
            # Balanced approach
            alpha = 0.5
        
        return {
            "alpha": alpha,
            "limit": 10 if mode == "quick_grab" else 20,
            "include_alternatives": specificity < 0.5,
            "boost_availability": mode == "emergency",
            "show_categories": specificity < 0.3
        }
```

## Voice Metadata Enhancement

```python
# Enhanced voice metadata collection
class EnhancedVoiceMetadata:
    def __init__(self):
        self.reset()
    
    def reset(self):
        # Basic metrics
        self.duration = 0
        self.word_count = 0
        self.pace = "normal"
        
        # Advanced metrics
        self.pitch_mean = 0
        self.pitch_variance = 0
        self.volume_mean = 0
        self.volume_variance = 0
        
        # Speech patterns
        self.pause_count = 0
        self.pause_duration_total = 0
        self.hesitation_count = 0
        self.self_corrections = 0
        self.repetitions = 0
        
        # Clarity metrics
        self.articulation_score = 0
        self.background_noise_level = 0
        self.audio_quality = 0
        
        # Derived metrics
        self.pace_variance = 0  # How consistent is their pace
        self.energy_level = 0   # Overall energy in voice
        self.clarity_score = 0  # How clear is their speech