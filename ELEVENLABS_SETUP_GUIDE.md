# ElevenLabs Voice Integration Setup Guide

## 🎯 Overview
This guide will help you set up ElevenLabs Conversational AI so your customers can call and interact with LeafLoaf.

## 📋 Prerequisites
- ElevenLabs account (with Conversational AI access)
- Your deployed API is working: https://leafloaf-langraph-32905605817.us-central1.run.app

## 🚀 Step-by-Step Setup

### 1. Create Your ElevenLabs Agent

1. Go to [ElevenLabs Conversational AI](https://elevenlabs.io/app/conversational-ai)
2. Click "Create agent" 
3. Choose "Blank agent"

### 2. Configure Basic Settings

**Agent Name**: LeafLoaf Shopping Assistant

**System Prompt**:
```
You are a helpful grocery shopping assistant for LeafLoaf. 
Help customers find products, manage their cart, and place orders.
Be conversational and friendly. Keep responses concise for voice.

When customers ask for products, use the search_products tool.
When they want to add items, use add_to_cart with the position number.
Always maintain the session_id throughout the conversation.
```

**First Message**: 
```
Hello! Welcome to LeafLoaf. I can help you with your grocery shopping. What are you looking for today?
```

### 3. Add Custom Tools (Webhooks)

Click "Add tool" for each of these:

#### Tool 1: Search Products
- **Name**: search_products
- **Description**: Search for grocery products
- **Server URL**: https://leafloaf-langraph-32905605817.us-central1.run.app/api/v1/voice/webhook/search
- **Method**: POST
- **Parameters**:
  ```json
  {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "What to search for"
      },
      "session_id": {
        "type": "string", 
        "description": "Session ID for the conversation"
      }
    },
    "required": ["query", "session_id"]
  }
  ```

#### Tool 2: Add to Cart
- **Name**: add_to_cart
- **Description**: Add products to shopping cart by position number
- **Server URL**: https://leafloaf-langraph-32905605817.us-central1.run.app/api/v1/voice/webhook/add_to_cart
- **Method**: POST
- **Parameters**:
  ```json
  {
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "position": {
              "type": "number",
              "description": "Position of product from search (1-5)"
            },
            "quantity": {
              "type": "number",
              "description": "How many to add"
            }
          }
        }
      },
      "session_id": {
        "type": "string"
      }
    },
    "required": ["items", "session_id"]
  }
  ```

#### Tool 3: Show Cart
- **Name**: show_cart
- **Description**: Show current cart contents
- **Server URL**: https://leafloaf-langraph-32905605817.us-central1.run.app/api/v1/voice/webhook/show_cart
- **Method**: POST
- **Parameters**:
  ```json
  {
    "type": "object",
    "properties": {
      "session_id": {
        "type": "string"
      }
    },
    "required": ["session_id"]
  }
  ```

#### Tool 4: Confirm Order
- **Name**: confirm_order
- **Description**: Confirm and place the order
- **Server URL**: https://leafloaf-langraph-32905605817.us-central1.run.app/api/v1/voice/webhook/confirm_order
- **Method**: POST
- **Parameters**:
  ```json
  {
    "type": "object",
    "properties": {
      "session_id": {
        "type": "string"
      }
    },
    "required": ["session_id"]
  }
  ```

### 4. Voice Settings
- **Voice**: Rachel (or choose your preferred voice)
- **Stability**: 0.5
- **Similarity Boost**: 0.75
- **Language**: English

### 5. Advanced Settings
- **Temperature**: 0.7
- **Max tokens**: 150 (keep responses concise)

### 6. Test Your Agent

1. Click "Test agent" in the ElevenLabs interface
2. Try these test conversations:

**Test 1: Basic Search**
```
You: "Hi, I need some milk"
Bot: [Should search and return milk products]
You: "Add the first one to my cart"
Bot: [Should add to cart]
```

**Test 2: Complex Order**
```
You: "I need organic vegetables"
Bot: [Shows organic vegetables]
You: "Add 2 of the first item"
Bot: [Adds to cart]
You: "What's in my cart?"
Bot: [Shows cart contents]
You: "That's all, please confirm"
Bot: [Confirms order]
```

### 7. Get Phone Number

Once testing works:
1. Click "Deploy" 
2. Choose "Phone number"
3. Select a phone number (US numbers available)
4. Share this number with your customers!

## 📞 Customer Demo Script

Give this to your 5 customers:

```
LeafLoaf Voice Shopping - Demo Instructions

1. Call: [Your ElevenLabs Phone Number]

2. Try saying:
   - "I need organic milk and bread"
   - "Show me your cheapest rice"
   - "Add 2 kg of tomatoes to my cart"
   - "What vegetables do you have?"
   - "What's in my cart?"
   - "I'm done, please confirm my order"

3. The assistant will:
   - Search for products
   - Tell you what's available with prices
   - Add items to your cart
   - Confirm your order

Tips:
- Say "the first one" or "number 2" to select from search results
- Ask "what's my total?" to check cart value
- Say "remove milk from cart" to remove items
```

## 🐛 Troubleshooting

### If webhooks aren't working:
1. Check the webhook URLs are exactly as shown above
2. Verify the API is still running: https://leafloaf-langraph-32905605817.us-central1.run.app/health
3. Check ElevenLabs logs for error messages

### If voice recognition is poor:
1. Ask customers to speak clearly
2. Reduce background noise
3. Try different voice models in settings

### Common Issues:
- **"Session not found"**: The conversation restarted. Start fresh.
- **"No products found"**: Try simpler search terms
- **Timeout errors**: The API might be cold starting. Try again.

## 📊 Monitor Usage

In ElevenLabs dashboard, you can see:
- Number of calls
- Average call duration  
- Tool usage statistics
- Error rates

## 🎉 Ready to Demo!

Your LeafLoaf voice assistant is now ready. Share the phone number with your 5 customers and let them experience conversational grocery shopping!