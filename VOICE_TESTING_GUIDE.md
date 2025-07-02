# Voice Testing Guide

## Quick Start Testing

### 1. Start the Server
```bash
python3 run.py
```

### 2. Test Voice Interface
Open in browser: http://localhost:8080/static/voice_conversational.html

### 3. Test via WebSocket
```bash
python3 test_function_calling.py
```

### 4. Test Scenarios

#### Scenario 1: Basic Greeting
- Say: "Hello"
- Expected: Normal conversational response
- Function Call: None

#### Scenario 2: Show Categories
- Say: "What are my options?" or "What do you have?"
- Expected: Lists available categories
- Function Call: `show_categories()`

#### Scenario 3: Product Search
- Say: "I need organic milk" or "Show me dairy products"
- Expected: Searches and returns products
- Function Call: `search_products(query)`

#### Scenario 4: Complex Queries
- Say: "I'm making pasta tonight, what do I need?"
- Expected: Should understand context and search appropriately

### 5. Check Logs

Function calling logs:
```bash
grep "Function call found" voice_test_*.log
```

Search execution:
```bash
grep "Searching for products" voice_test_*.log
```

Errors:
```bash
grep -E "error|Error|ERROR" voice_test_*.log
```

## Current Status

✅ Working:
- Deepgram STT (Speech-to-Text)
- Deepgram TTS (Text-to-Speech)  
- Gemini 2.0 Flash function calling
- WebSocket connections

🚧 Issues:
- Search integration needs to use full multi-agent system
- Need voice-native multi-modal supervisor

## WebSocket Message Format

### Send Text Input
```json
{
  "type": "text_input",
  "text": "I need organic milk"
}
```

### Receive Responses
```json
{
  "type": "assistant_response",
  "text": "I found several organic milk options for you..."
}

{
  "type": "products",
  "data": [
    {
      "name": "Organic Valley Whole Milk",
      "price": 5.99,
      "unit": "gallon"
    }
  ]
}
```