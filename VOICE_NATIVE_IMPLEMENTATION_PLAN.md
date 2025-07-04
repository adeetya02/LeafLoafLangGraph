# Voice-Native Implementation Plan

## Current Voice Flow

```
User speaks → Deepgram STT → Basic metadata → Supervisor (uses it) → Other agents (ignore it)
```

## Target Voice Flow

```
User speaks → Deepgram STT → Rich metadata → All agents adapt → Personalized experience
```

## Quick Wins (Can Do Now)

### 1. Calculate Speech Pace in voice_streaming_debug.py

```python
async def on_utterance_end(self, *args, **kwargs):
    # Calculate voice metadata
    if self.speech_started_time:
        self.speech_duration = time.time() - self.speech_started_time
        
        # Calculate pace
        words = self.current_utterance.split()
        self.word_count = len(words)
        
        if self.speech_duration > 0:
            words_per_minute = (self.word_count / self.speech_duration) * 60
            
            if words_per_minute < 120:
                self.speech_pace = "slow"
            elif words_per_minute > 180:
                self.speech_pace = "fast"
            else:
                self.speech_pace = "normal"
        
        # Detect hesitations
        hesitations = len(re.findall(r'\b(um|uh|hmm|err)\b', self.current_utterance.lower()))
        
        # Build metadata
        self.voice_metadata = {
            "pace": self.speech_pace,
            "duration": self.speech_duration,
            "word_count": self.word_count,
            "words_per_minute": words_per_minute,
            "hesitations": hesitations,
            "language": self.detected_language
        }
```

### 2. Pass Rich Metadata Through Pipeline

```python
# When calling the main API
response = await self.process_with_supervisor(
    self.current_utterance,
    voice_metadata=self.voice_metadata  # Pass the rich metadata
)
```

### 3. Make Product Search Voice-Aware

Simple changes to ProductSearchReactAgent:

```python
async def _run(self, state: SearchState) -> SearchState:
    # Get voice insights
    voice_metadata = state.get("voice_metadata", {})
    
    # Adjust search limit based on pace
    if voice_metadata.get("pace") == "fast":
        # User is rushed - show fewer options
        limit = min(5, state.get("search_params", {}).get("limit", 10))
    elif voice_metadata.get("pace") == "slow" and voice_metadata.get("hesitations", 0) > 2:
        # User is exploring/confused - show more options
        limit = 15
    
    # Log voice influence
    self.logger.info(f"Voice-adjusted search: pace={voice_metadata.get('pace')}, limit={limit}")
```

### 4. Make Order Agent Quantity-Smart

```python
# In OrderReactAgent._plan_order_tools
def _plan_order_tools(self, state, query, current_order, search_results, iteration, memory_context):
    voice_metadata = state.get("voice_metadata", {})
    
    # Fast pace = assume usual quantities
    if voice_metadata.get("pace") == "fast" and memory_context.get("order_patterns"):
        # Use historical quantities
        for product in identified_products:
            usual_qty = memory_context["order_patterns"].get(product, {}).get("usual_quantity", 1)
            tool_calls.append({
                "type": "function",
                "function": {
                    "name": "add_to_cart",
                    "arguments": json.dumps({
                        "product_id": product["id"],
                        "quantity": usual_qty  # Voice-aware quantity
                    })
                }
            })
```

## Multi-Modal Preparation (For Tomorrow)

### 1. Unified Input Handler

```python
class MultiModalInputHandler:
    async def process_input(self, input_data):
        """Handle voice, text, or image inputs uniformly"""
        
        modality_data = {
            "primary_modality": None,
            "voice": None,
            "text": None,
            "image": None,
            "combined_intent": None
        }
        
        # Voice input
        if input_data.get("audio"):
            transcript = await self.process_voice(input_data["audio"])
            modality_data["voice"] = {
                "transcript": transcript,
                "metadata": input_data.get("voice_metadata")
            }
            modality_data["primary_modality"] = "voice"
        
        # Text input  
        if input_data.get("text"):
            modality_data["text"] = {
                "content": input_data["text"],
                "metadata": {
                    "length": len(input_data["text"]),
                    "has_list": "\n" in input_data["text"]
                }
            }
            if not modality_data["primary_modality"]:
                modality_data["primary_modality"] = "text"
        
        # Image input
        if input_data.get("image"):
            image_analysis = await self.process_image(input_data["image"])
            modality_data["image"] = {
                "analysis": image_analysis,
                "metadata": input_data.get("image_metadata")
            }
            if not modality_data["primary_modality"]:
                modality_data["primary_modality"] = "image"
        
        return modality_data
```

### 2. Multi-Modal State

```python
# Extend SearchState
class MultiModalSearchState(SearchState):
    modality_data: Dict[str, Any] = {}
    primary_modality: str = "text"
    modality_confidence: Dict[str, float] = {}
```

### 3. Modality-Aware Routing

```python
# In supervisor
async def analyze_with_multi_modal_context(self, modality_data):
    """Route based on all available modalities"""
    
    # Voice + Image: "What's this?" while showing product
    if modality_data["voice"] and modality_data["image"]:
        return self._handle_voice_plus_image(modality_data)
    
    # Text list + Voice: "Add these" with shopping list
    if modality_data["text"] and modality_data["voice"]:
        return self._handle_text_plus_voice(modality_data)
    
    # Single modality
    return self._handle_single_modality(modality_data)
```

## Testing Voice Awareness

### 1. Voice Scenarios to Test

```python
# Test different voice patterns
test_scenarios = [
    {
        "audio": "fast_rushed_order.wav",
        "expected": {
            "pace": "fast",
            "search_limit": 5,
            "use_usual_quantities": True
        }
    },
    {
        "audio": "slow_exploring.wav", 
        "expected": {
            "pace": "slow",
            "search_limit": 15,
            "detailed_responses": True
        }
    },
    {
        "audio": "confused_hesitant.wav",
        "expected": {
            "hesitations": ">2",
            "offer_help": True,
            "simplify_options": True
        }
    }
]
```

### 2. Multi-Modal Test Cases

```python
# Voice + Image
{
    "voice": "What's the price of this?",
    "image": "photo_of_product.jpg",
    "expected_behavior": "Identify product from image, provide price"
}

# Voice + Text
{
    "voice": "Add all these to my cart",
    "text": "Milk 2L\nBread\nEggs dozen",
    "expected_behavior": "Parse list, add all items with voice context"
}

# All three
{
    "voice": "Is this the same as what's on my list?",
    "text": "Organic whole milk",
    "image": "milk_carton.jpg",
    "expected_behavior": "Compare image to text, confirm match"
}
```

## Implementation Steps

### Today:
1. ✅ Enhance voice metadata collection
2. ✅ Pass metadata through full pipeline
3. ✅ Make search respect voice urgency
4. ✅ Add voice-aware quantities

### Tomorrow:
1. 🔄 Add image input handling
2. 🔄 Create unified multi-modal processor
3. 🔄 Test voice + image scenarios
4. 🔄 Implement voice + text list handling

### This Week:
1. 📅 Full multi-modal routing
2. 📅 Consistency checking across modalities
3. 📅 Advanced voice pattern detection
4. 📅 Production testing

## Key Principle

**Every agent should adapt to HOW the user communicates, not just WHAT they say.**

- Fast speakers get quick results
- Hesitant users get more guidance
- Multi-modal inputs get unified understanding
- The system feels naturally responsive