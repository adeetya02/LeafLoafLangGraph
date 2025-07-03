# Vertex AI Conversation Setup for LeafLoaf

## What is Vertex AI Conversation?

Vertex AI Conversation is Google's next-generation conversational AI platform that provides:
- Advanced language understanding using PaLM/Gemini models
- Built-in personalization and context management
- Integration with your data (product catalogs, user preferences)
- Multi-turn conversation handling
- No manual intent/entity setup required

## Architecture Overview

```
User Voice → STT → Vertex AI Chat Model → Your Data/Functions → Response → TTS → User
```

## Key Advantages over Dialogflow

1. **No Intent/Entity Setup**: The LLM understands natural language directly
2. **Better Context**: Maintains conversation history automatically
3. **Function Calling**: Can call your APIs directly
4. **Personalization**: Built-in user preference handling
5. **Flexibility**: Handles complex, multi-step conversations

## Setup Steps

### 1. Enable Required APIs

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  speech.googleapis.com \
  texttospeech.googleapis.com \
  discoveryengine.googleapis.com \
  --project=leafloafai
```

### 2. Create Vertex AI Search App (Optional - for product catalog)

```bash
# This allows Vertex AI to search your product database
gcloud alpha discovery-engine data-stores create \
  --data-store-id="leafloaf-products" \
  --location="global" \
  --solution-type="solution-type-search" \
  --project=leafloafai
```

### 3. Configure Environment Variables

Add to `.env.yaml`:
```yaml
# Vertex AI Configuration
GCP_PROJECT_ID: "leafloafai"
GCP_LOCATION: "us-central1"
VERTEX_DATASTORE_ID: "leafloaf-products"  # Optional
GOOGLE_APPLICATION_CREDENTIALS: "/path/to/service-account.json"  # Optional
```

### 4. Initialize Vertex AI in Code

```python
import vertexai
from vertexai.language_models import ChatModel

# Initialize
vertexai.init(project="leafloafai", location="us-central1")

# Create chat model
chat_model = ChatModel.from_pretrained("chat-bison@002")  # or "gemini-pro"

# Start conversation with context
chat = chat_model.start_chat(
    context="""You are LeafLoaf, a personalized grocery shopping assistant.
    
    You help users with:
    - Finding products based on their preferences
    - Managing dietary restrictions (vegan, gluten-free, etc.)
    - Suggesting complementary products
    - Reordering frequently bought items
    - Providing recipe suggestions
    
    Always be helpful, concise, and personalized."""
)
```

## How Our Implementation Works

### 1. Voice Flow (`voice_vertex_conversation.py`)

```python
# 1. Receive audio
audio_data = await websocket.receive()

# 2. Convert to text (Google STT)
transcript = await speech_to_text(audio_data)

# 3. Send to Vertex AI with context
response = chat.send_message(f"""
User said: {transcript}
User preferences: {user_preferences}
Cart contents: {cart_items}

Provide a helpful response and any product recommendations.
""")

# 4. Parse response and execute actions
if "search_products" in response.text:
    products = await search_products(query)
    
# 5. Generate voice response (Google TTS)
audio_response = await text_to_speech(response.text)

# 6. Send back to user
await websocket.send(audio_response)
```

### 2. Personalization Features

```python
# The model maintains context across conversations
chat.send_message("I'm vegetarian")
# Model remembers this for future product recommendations

chat.send_message("Show me pasta")
# Model automatically filters for vegetarian pasta options

chat.send_message("What did I buy last time?")
# Model can access order history and provide reorder suggestions
```

### 3. Function Calling (Advanced)

```python
# Define functions the model can call
functions = [
    {
        "name": "search_products",
        "description": "Search for products in the catalog",
        "parameters": {
            "query": "string",
            "dietary_filter": "string",
            "max_price": "number"
        }
    },
    {
        "name": "add_to_cart",
        "description": "Add items to shopping cart",
        "parameters": {
            "product_id": "string",
            "quantity": "number"
        }
    }
]

# Model automatically calls these based on user intent
```

## Testing the Integration

### 1. Test Endpoint
```bash
curl http://localhost:8080/api/v1/voice/vertex-conversation/test
```

### 2. WebSocket Test
Open the HTML interface and speak naturally:
- "I need milk and eggs"
- "I'm vegan, show me protein options"
- "What's good for pasta dinner?"
- "Add my usual items"
- "Reorder my last purchase"

## Implementation Checklist

- [x] Basic Vertex AI setup in code
- [ ] Enable APIs in GCP
- [ ] Test chat model connection
- [ ] Implement product search integration
- [ ] Add user preference storage
- [ ] Connect to cart management
- [ ] Test voice flow end-to-end

## Next Steps

1. **Enable the APIs** (command above)
2. **Test the chat model** directly
3. **Integrate with your product search**
4. **Add personalization features**
5. **Test with voice interface**