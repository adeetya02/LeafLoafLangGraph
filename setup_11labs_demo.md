# 11Labs Voice Demo Setup Guide

## Quick Setup for Tonight's Demo

### Option 1: Use 11Labs Conversational AI (No API Key Needed for Testing)

1. **Go to 11Labs Conversational AI**
   - Visit: https://elevenlabs.io/conversational-ai
   - Sign up/Login to 11Labs

2. **Create Your Agent**
   ```
   Name: LeafLoaf Assistant
   Voice: Rachel (or any female voice)
   First Message: "Hi! Welcome to LeafLoaf. I can help you find organic groceries and manage your order. What are you looking for today?"
   Language: English
   ```

3. **Configure Webhooks**
   Since we already have webhook endpoints, configure these:
   ```
   Search Products: https://leafloaf-*.run.app/api/v1/voice/webhook/search
   Add to Cart: https://leafloaf-*.run.app/api/v1/voice/webhook/add_to_cart
   Show Cart: https://leafloaf-*.run.app/api/v1/voice/webhook/show_cart
   Confirm Order: https://leafloaf-*.run.app/api/v1/voice/webhook/confirm_order
   ```

4. **Test with Their Web Widget**
   - 11Labs provides a test widget
   - Can embed in any webpage
   - Works immediately

### Option 2: Fix API Key and Use Direct Integration

1. **Get New API Key**
   - Login to 11Labs: https://elevenlabs.io/
   - Go to Profile → API Keys
   - Generate new key

2. **Update .env.yaml**
   ```yaml
   ELEVENLABS_API_KEY: "your_new_key_here"
   ```

3. **Test Voice Manager**
   ```python
   # src/voice/voice_manager.py
   import os
   import httpx
   from typing import Optional
   
   class VoiceManager:
       def __init__(self):
           self.api_key = os.getenv("ELEVENLABS_API_KEY")
           self.voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel
           
       async def text_to_speech(self, text: str) -> bytes:
           """Convert text to speech"""
           async with httpx.AsyncClient() as client:
               response = await client.post(
                   f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}",
                   headers={"xi-api-key": self.api_key},
                   json={
                       "text": text,
                       "model_id": "eleven_monolingual_v1",
                       "voice_settings": {
                           "stability": 0.5,
                           "similarity_boost": 0.5
                       }
                   }
               )
               return response.content
   ```

## Demo Script

### Scene 1: Introduction
**User**: "Hi, I need help with grocery shopping"
**System**: "Hi! Welcome to LeafLoaf. I can help you find organic groceries. What are you looking for today?"

### Scene 2: Product Search
**User**: "I need organic milk and some bananas"
**System**: "I found organic milk options for you. I have Organic Valley Whole Milk for $5.99. For bananas, I have organic bananas at $1.99 per pound. Would you like to add these to your cart?"

### Scene 3: Cart Management
**User**: "Yes, add 2 cartons of milk and 3 pounds of bananas"
**System**: "I've added 2 cartons of Organic Valley Whole Milk and 3 pounds of organic bananas to your cart. Your total is $17.95. Would you like to add anything else?"

### Scene 4: Personalization (if user has history)
**User**: "What's my usual milk order?"
**System**: "You usually order 2 cartons of Amul Toned Milk every week. Would you like to add your usual order?"

### Scene 5: Order Completion
**User**: "That's all, please confirm my order"
**System**: "Your order of 5 items totaling $17.95 has been confirmed. It will be delivered tomorrow by 10 AM. Thank you for shopping with LeafLoaf!"

## Testing Without 11Labs

If 11Labs setup fails, use browser's Web Speech API:

```javascript
// Quick browser test
const recognition = new webkitSpeechRecognition();
recognition.continuous = true;
recognition.onresult = (event) => {
    const text = event.results[event.results.length-1][0].transcript;
    console.log("You said:", text);
    // Call our API
    fetch('https://leafloaf.run.app/api/v1/search', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({query: text})
    }).then(r => r.json()).then(console.log);
};
recognition.start();

// For TTS
const utterance = new SpeechSynthesisUtterance("Welcome to LeafLoaf!");
speechSynthesis.speak(utterance);
```

## Recommended Approach

1. **For Tonight**: Use 11Labs Conversational AI (Option 1)
   - Fastest setup
   - No API key issues
   - Professional quality
   - Works immediately

2. **Future**: Build custom voice manager with proper API key
   - More control
   - Custom flows
   - Better integration

The existing webhook handlers in `src/api/voice_webhooks.py` are ready to use!