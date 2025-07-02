# Voice Implementation Setup Guide

## Overview
This branch contains the voice implementation for LeafLoaf LangGraph, featuring real-time conversational AI with WebSocket streaming, voice-native supervision, and comprehensive speech-to-text/text-to-speech capabilities.

## Important: API Key Setup

**All API keys have been removed from the codebase for security reasons. You must provide your own API keys to use the voice features.**

### Required API Keys

1. **Deepgram API Key** (for speech-to-text and text-to-speech)
   - Sign up at https://deepgram.com
   - Get your API key from the Deepgram console
   - Set in environment: `DEEPGRAM_API_KEY=your-key-here`

2. **Other Required Keys** (see `.env.yaml.template`)
   - HuggingFace API Key
   - Weaviate API Key
   - LangChain API Key
   - Google Cloud credentials (optional)

### Setup Instructions

1. **Copy the environment template**:
   ```bash
   cp .env.yaml.template .env.yaml
   ```

2. **Edit `.env.yaml`** and add your API keys:
   ```yaml
   DEEPGRAM_API_KEY: "your-deepgram-api-key"
   HUGGINGFACE_API_KEY: "your-huggingface-key"
   WEAVIATE_URL: "your-weaviate-url"
   WEAVIATE_API_KEY: "your-weaviate-key"
   # ... other keys
   ```

3. **Never commit `.env.yaml`** to version control!

## Voice Features Implemented

### 1. WebSocket Real-Time Conversation
- **File**: `src/api/voice_websocket.py`
- **Endpoint**: `/api/v1/voice-streaming/ws/{session_id}`
- **Features**:
  - Real-time speech-to-text
  - Streaming text-to-speech
  - Continuous conversation flow
  - Session management

### 2. Voice-Native Supervisor
- **File**: `src/agents/supervisor_optimized.py`
- **Model**: Gemma 2 9B (HuggingFace/Vertex AI)
- **Features**:
  - Voice metadata processing (pace, emotion, urgency)
  - Intent detection optimized for voice
  - Dynamic search parameter adjustment

### 3. HTML Voice Interfaces
- **Basic Test**: `/static/voice_test_basic.html`
- **Conversational**: `/static/voice_conversational.html`
- **Features**:
  - WebSocket audio streaming
  - Real-time transcription display
  - Product result visualization

### 4. Voice Configuration
- **File**: `src/config/voice_config.py`
- **Customizable**:
  - STT/TTS models
  - Conversation parameters
  - Response styles
  - Audio processing settings

## Running the Voice Implementation

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the main server**:
   ```bash
   python run.py
   ```

3. **Access voice interfaces**:
   - Basic: http://localhost:8080/static/voice_test_basic.html
   - Conversational: http://localhost:8080/static/voice_conversational.html

## Files Removed for Security

The following files contained hardcoded API keys and have been removed:
- `src/api/voice_deepgram_conversational.py`
- `src/static/voice_neighborhood.html`
- Various test scripts with embedded credentials

To recreate similar functionality, use the environment variables approach shown in the remaining files.

## Architecture Overview

```
User Voice → WebSocket → STT (Deepgram) → Voice-Native Supervisor
                                              ↓
                                         Intent Detection
                                              ↓
                                    Product Search / Order Agent
                                              ↓
                                      Response Compiler
                                              ↓
                                       TTS (Deepgram)
                                              ↓
                                        Audio Stream → User
```

## Troubleshooting

1. **"DEEPGRAM_API_KEY not found"**: Make sure you've set up your `.env.yaml` file
2. **WebSocket connection fails**: Check that the server is running on the correct port
3. **No audio output**: Verify browser permissions for microphone access
4. **Search returns no results**: Check Weaviate connection and API key

## Contributing

When contributing to this voice implementation:
1. Never hardcode API keys in source files
2. Use environment variables for all credentials
3. Update `.gitignore` if adding new sensitive files
4. Test with your own API keys before submitting PRs

## Support

For issues or questions about the voice implementation, please open an issue on GitHub.