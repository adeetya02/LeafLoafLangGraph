# Dialogflow Integration Guide for LeafLoaf

## What is Dialogflow?

Dialogflow is Google's natural language understanding (NLU) platform that enables conversational interfaces. It converts user speech/text into structured data that your application can understand and act upon.

## Architecture Overview

```
User Voice → Google STT → Dialogflow → Intent + Entities → Your App → Response → Google TTS → User
```

## Key Concepts

### 1. **Agent**
- The Dialogflow bot that processes conversations
- Has a unique ID and language settings
- We created: "LeafLoaf Shopping Assistant"

### 2. **Intents**
Think of intents as the "what does the user want to do?"

Examples:
- `product.search` - User wants to find products
- `order.add` - User wants to add items to cart
- `order.view` - User wants to see their cart
- `general.greeting` - User is saying hello

### 3. **Entities**
Entities are the "important pieces of information" in user input.

Examples:
- `@product` - "milk", "bread", "apples"
- `@quantity` - "2", "dozen", "five"
- `@category` - "organic", "dairy", "fruits"

### 4. **Training Phrases**
Examples you provide to train Dialogflow:

```
Intent: product.search
Training phrases:
- "I need milk" → extracts: product=milk
- "Show me organic vegetables" → extracts: category=organic, product=vegetables
- "Do you have bananas?" → extracts: product=bananas
```

## How Our Implementation Works

### 1. Voice Flow (src/api/voice_dialogflow_cx.py)

```python
# User speaks
audio_chunk → 

# Google Speech-to-Text
transcript = "I need 2 gallons of milk"

# Send to Dialogflow
response = dialogflow.detect_intent(
    session=session_id,
    text_input=transcript
)

# Dialogflow returns:
{
    "intent": "order.add",
    "parameters": {
        "quantity": 2,
        "unit": "gallons",
        "product": "milk"
    },
    "confidence": 0.92
}

# Our app processes based on intent
if intent == "product.search":
    results = search_products(product)
elif intent == "order.add":
    cart.add_item(product, quantity)
```

### 2. Session Management
- Each conversation has a unique session ID
- Dialogflow maintains context across the conversation
- Example: "Add milk" → "How much?" → "2 gallons" (Dialogflow remembers we're talking about milk)

### 3. WebSocket Integration
```javascript
// Frontend sends audio chunks
websocket.send(audioData)

// Backend processes:
1. Accumulate audio → STT → Get text
2. Send text to Dialogflow → Get intent
3. Process intent → Get response
4. Generate speech → TTS → Send audio back
5. WebSocket sends audio chunks to frontend
```

## Current Setup Status

### ✅ Completed:
1. Created Dialogflow agent: "LeafLoaf Shopping Assistant"
2. Created basic intents: `product.search`, `order.add`
3. Set up Google Cloud project: "leafloafai"
4. Enabled required APIs

### ❌ Still Needed:
1. Set `DIALOGFLOW_AGENT_ID` environment variable
2. Create more intents (greetings, checkout, etc.)
3. Add more training phrases
4. Configure fulfillment webhooks

## How to Complete Setup

### 1. Get Agent ID
```bash
# List all agents
gcloud alpha dialogflow agents list --project=leafloafai

# Or use the Console:
# https://dialogflow.cloud.google.com/
```

### 2. Set Environment Variable
```bash
export DIALOGFLOW_AGENT_ID="your-agent-id-here"
```

### 3. Create More Intents (Programmatically)
```python
# Example: Create greeting intent
intent = dialogflow.Intent(
    display_name="general.greeting",
    training_phrases=[
        "Hello", "Hi", "Hey there", "Good morning"
    ],
    messages=[
        "Hello! What groceries can I help you find today?"
    ]
)
```

## Benefits of Dialogflow

1. **Pre-trained NLU**: Understands variations ("I need milk" = "Get me some milk" = "milk please")
2. **Context Management**: Maintains conversation state
3. **Multi-language**: Supports 30+ languages
4. **Entity Extraction**: Automatically pulls out important info
5. **Integration**: Works seamlessly with Google STT/TTS

## Testing the Integration

1. **Via API**:
```bash
curl -X POST http://localhost:8080/api/v1/voice/dialogflow/test \
  -H "Content-Type: application/json" \
  -d '{"text": "I need organic milk"}'
```

2. **Via WebSocket**:
- Open `/static/voice_dialogflow_test.html`
- Click microphone
- Say "I need milk and bread"
- Dialogflow will extract intent and entities

## Next Steps

1. **Get the Agent ID** from Google Cloud Console
2. **Add to .env.yaml**:
   ```yaml
   DIALOGFLOW_AGENT_ID: "projects/leafloafai/agent"
   ```
3. **Test the WebSocket connection** with proper agent ID
4. **Add more intents** for complete shopping experience