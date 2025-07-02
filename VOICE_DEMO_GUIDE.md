# 🎤 LeafLoaf Voice Assistant Demo Guide

## Quick Start

1. **Open the Voice Interface**
   ```
   http://127.0.0.1:8080/static/voice_conversational.html
   ```

2. **Click "Start Conversation"**
   - Allow microphone access when prompted
   - You'll hear: "Hello! I'm LeafLoaf, your personal grocery shopping assistant. What can I help you find today?"

3. **Try These Conversations:**

### 🛒 Product Search
- "I need some organic milk"
- "Show me gluten-free pasta options"
- "What's the price of avocados?"
- "I'm looking for fresh vegetables"

### 🍳 Recipe Shopping
- "I want to make spaghetti carbonara"
- "What do I need for a Greek salad?"
- "Help me shop for taco night"

### 💬 Natural Conversation
- "What's on sale today?"
- "I'm on a budget, what do you recommend?"
- "Do you have any vegan options?"
- "I need baby food and diapers"

## Features Working Now

✅ **Real-time Speech Recognition** - Deepgram STT
✅ **Natural Voice Responses** - Deepgram TTS  
✅ **Product Search** - Connected to Weaviate database
✅ **Conversational Context** - Remembers what you said
✅ **Visual Product Display** - Shows products found

## Voice Commands

- **"Stop"** - End conversation
- **"Clear cart"** - Start fresh
- **"What's in my cart?"** - Review items
- **"Add that to cart"** - Add last shown item

## Monitoring (Optional)

In another terminal, run:
```bash
python3 monitor_voice.py
```

This shows:
- What you're saying (real-time transcription)
- LeafLoaf's responses
- Products found
- Any errors

## Troubleshooting

### No Sound?
1. Check browser permissions for microphone
2. Ensure speakers/headphones are connected
3. Try refreshing the page

### Connection Error?
1. Make sure server is running: `python3 run.py`
2. Check the URL is correct: http://127.0.0.1:8080
3. Look at browser console for errors (F12)

### Not Understanding?
- Speak clearly and naturally
- Wait for the "Listening..." status
- Try shorter phrases first

## What's Happening Behind the Scenes

1. **Your Voice** → Microphone → WebSocket → Server
2. **Deepgram STT** → Converts speech to text
3. **LangGraph** → Understands intent, searches products
4. **LLM Response** → Generates natural reply
5. **Deepgram TTS** → Converts reply to speech
6. **Speaker** → You hear LeafLoaf's voice

## Cool Things to Notice

- 🎯 **Intent Detection**: Knows when you're searching vs chatting
- 🧠 **Context Aware**: Remembers previous queries
- 🔍 **Smart Search**: Uses semantic + keyword matching
- 💬 **Natural Flow**: Handles interruptions and corrections
- 📝 **Transcript Capture**: Saves for ML training (async)

## Next: Testing on GCP

Once local testing is complete, we'll deploy to Cloud Run for production voice shopping!