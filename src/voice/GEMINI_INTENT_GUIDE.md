# Gemini Intent Detection Guide

## Why Let Gemini Handle Intent Detection?

Instead of hardcoding rules for intent detection, we let Gemini naturally understand context and intent. This provides:

- **Natural Understanding**: Handles ambiguous phrases, typos, and conversational flow
- **Context Awareness**: Understands intent based on conversation history
- **No Maintenance**: No need to update rules for new phrases
- **Multi-Intent**: Can detect multiple intents in one message

## Comparison: Hardcoded vs Gemini

### Hardcoded Rules (v1)
```python
# Limited and rigid
if "hello" in text or "hi" in text:
    return "greeting"
elif "add" in text or "cart" in text:
    return "cart_management"
# Misses: "throw in some milk", "I'll take 2", "gimme that"
```

### Gemini Natural Detection (v2)
```python
# Gemini understands naturally
"throw in some milk" → intent: "add_to_cart"
"I'll take 2" → intent: "add_to_cart" + quantity: 2
"gimme that" → intent: "add_to_cart" + needs_clarification
```

## Examples of Gemini's Superior Understanding

### 1. Ambiguous Phrases
```
User: "The usual"
Hardcoded: product_search (wrong)
Gemini: intent: "reorder_favorites" (understands context)

User: "I'm good"
Hardcoded: greeting (wrong)
Gemini: intent: "decline_suggestion" (understands refusal)
```

### 2. Complex Requests
```
User: "Hi, running low on milk and eggs, any deals?"
Hardcoded: Can only detect one intent
Gemini: intents: ["greeting", "product_search", "check_deals"]
```

### 3. Conversational Context
```
User: "What's good for breakfast?"
Assistant: "Greek yogurt, oatmeal, or eggs?"
User: "The second one"
Hardcoded: clarification (doesn't understand)
Gemini: intent: "select_option", product: "oatmeal"
```

## Implementation

### Simple Usage (v2)
```python
from src.voice.models.gemini_voice_v2 import GeminiVoiceModelV2

# Initialize
model = GeminiVoiceModelV2()

# Let Gemini handle everything
response, data = await model.generate_response(
    "Hey, got any good pasta on sale?",
    extract_entities=True
)

# Gemini returns:
# response: "Hi! Yes, we have several pasta options on sale today..."
# data: {
#   "intent": "product_search_with_deals",
#   "products": ["pasta"],
#   "preferences": ["on_sale"]
# }
```

### With Conversation Styles
```python
# Different styles, same understanding
model.set_conversation_style("efficient_helper")
response, data = await model.generate_response("Got milk?")
# Response: "Yes. 5 options. Add to cart?"

model.set_conversation_style("personal_shopper")
response, data = await model.generate_response("Got milk?")
# Response: "Yes! We have your usual 2% organic, plus some new oat milk alternatives you might enjoy."
```

## Prompt Structure

The v2 system uses a single intelligent prompt:

```
You are an AI grocery shopping assistant for LeafLoaf.

Your task is to:
1. Understand the user's intent from their message
2. Respond appropriately based on the context
3. Extract relevant entities when applicable

[Intent examples and guidelines...]

RESPONSE: [conversational response]
ENTITIES: {"intent": "detected_intent", "products": [...], ...}
```

## Benefits Over Hardcoded Rules

1. **Handles Typos**: "I nede milke" → understands as "I need milk"
2. **Regional Variations**: "soda" vs "pop" vs "soft drink"
3. **Slang/Informal**: "chuck it in the cart" → add to cart
4. **Multiple Languages**: Can potentially handle code-switching
5. **Context Memory**: Remembers previous conversation
6. **Emotion Detection**: Can adjust response based on urgency/mood

## Testing Intent Detection

Run the test to see Gemini in action:
```bash
export GEMINI_API_KEY='your-key'
python test_gemini_intent_detection.py
```

## When to Use Each Version

- **Use v2 (Gemini Intent)**: For production, voice interfaces, natural conversation
- **Use v1 (Hardcoded)**: Only for testing without API key, or very specific controlled scenarios

## Future Enhancements

1. **Intent Confidence**: Return confidence scores
2. **Intent Hierarchy**: Primary and secondary intents
3. **Custom Intents**: Train on your specific use cases
4. **Multi-turn Intent**: Track intent across conversation
5. **Voice Metadata**: Use voice tone/speed for intent