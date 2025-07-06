# Migration Guide: Dynamic Intent-Aware Deepgram Clients

## Overview
This guide explains how to migrate from the original Deepgram clients to the new dynamic intent-aware versions.

## What's New

### Dynamic Intent Learning
- **No hardcoded intents**: System learns from supervisor classifications
- **Pattern recognition**: Identifies phrases that correlate with specific intents
- **Automatic updates**: Custom intents refresh periodically based on usage
- **Deepgram integration**: Leverages Deepgram's extended intent mode with custom intents

### Key Benefits
1. **Adaptive**: Intents evolve based on actual user queries
2. **No maintenance**: No need to manually update intent lists
3. **Supervisor-driven**: Single source of truth for intent classification
4. **Performance**: Deepgram can optimize recognition for learned patterns

## Migration Steps

### 1. Update Imports

**Before:**
```python
from src.voice.deepgram.streaming_client import DeepgramStreamingClient
from src.voice.deepgram.conversational_client import DeepgramConversationalClient
from src.voice.deepgram.nova3_client import DeepgramNova3Client
```

**After:**
```python
from src.voice.deepgram.client_factory import (
    create_streaming_client,
    create_conversational_client,
    create_nova3_client
)
```

### 2. Update Client Creation

**Before:**
```python
client = DeepgramStreamingClient(api_key)
```

**After:**
```python
client = create_streaming_client(api_key)
# or
client = create_streaming_client(api_key, enable_dynamic_intents=True)
```

### 3. Update Connection Code

**Before:**
```python
await client.connect(
    on_transcript=handle_transcript,
    on_error=handle_error,
    model="nova-2",
    language="en-US"
)
```

**After:**
```python
await client.connect(
    on_transcript=handle_transcript,
    on_error=handle_error,
    model="nova-2",
    language="en-US",
    enable_intents=True  # New parameter
)
```

### 4. Handle Intent Information

**Before:**
```python
async def handle_transcript(data):
    transcript = data["transcript"]
    is_final = data["is_final"]
    # Process transcript
```

**After:**
```python
async def handle_transcript(data):
    transcript = data["transcript"]
    is_final = data["is_final"]
    
    # New: Check for Deepgram's intent detection
    if "intent_info" in data and data["intent_info"]:
        deepgram_intent = data["intent_info"]["intent"]
        intent_confidence = data["intent_info"]["confidence"]
        # Use Deepgram's intent if available
```

### 5. Feed Supervisor Classifications Back

**New requirement**: When the supervisor classifies a query, feed it back to Deepgram:

```python
# In your supervisor or main flow
result = await supervisor.analyze_with_voice_context(query, voice_metadata, memory_context)

# Feed the classification back to Deepgram client
await deepgram_client.observe_supervisor_intent(
    transcript=query,
    intent=result["intent"],
    confidence=result["confidence"]
)
```

### 6. Monitor Intent Learning

**New capability**: Monitor what intents are being learned:

```python
# Get statistics
stats = deepgram_client.get_intent_statistics()
print(f"Total observations: {stats['total_observations']}")
print(f"Intent counts: {stats['intent_counts']}")
print(f"Current custom intents: {stats['current_custom_intents']}")

# Get current custom intents
intents = deepgram_client.get_current_custom_intents()
print(f"Active custom intents: {intents}")
```

## Complete Example

```python
from src.voice.deepgram.client_factory import create_streaming_client

# Create client with dynamic intents
client = create_streaming_client()

# Define handlers
async def handle_transcript(data):
    transcript = data["transcript"]
    is_final = data["is_final"]
    
    if is_final and transcript:
        # Process with supervisor
        result = await supervisor.analyze_query(transcript)
        
        # Feed back to Deepgram for learning
        await client.observe_supervisor_intent(
            transcript=transcript,
            intent=result["intent"],
            confidence=result["confidence"]
        )
        
        # Use the intent
        print(f"Supervisor intent: {result['intent']}")
        
        # Check if Deepgram also detected an intent
        if "intent_info" in data:
            print(f"Deepgram intent: {data['intent_info']['intent']}")

# Connect with intents enabled
await client.connect(
    on_transcript=handle_transcript,
    enable_intents=True
)

# Send audio
await client.send_audio(audio_data)

# Monitor learning
stats = client.get_intent_statistics()
print(f"Learned from {stats['total_observations']} queries")
```

## Backward Compatibility

If you need to disable dynamic intents temporarily:

```python
# Create without dynamic intents
client = create_streaming_client(api_key)

# Connect without intents
await client.connect(
    on_transcript=handle_transcript,
    enable_intents=False  # Disable intent features
)
```

## Troubleshooting

### Intents Not Being Detected
1. Ensure `enable_intents=True` in connect()
2. Check that supervisor classifications are being fed back
3. Verify at least 3 occurrences of a pattern (minimum threshold)

### Performance Impact
- Intent learning runs in background (default: every 60s)
- Minimal overhead on audio processing
- Custom intents sent only at connection time (or via update)

### Debugging
```python
# Enable debug logging
import structlog
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
)

# Check intent learner state
learner = client.intent_learner
patterns = learner.transcript_to_intent_patterns
print(f"Learned patterns: {patterns}")
```

## Best Practices

1. **Feed all classifications**: Even low-confidence ones help learning
2. **Use consistent intent names**: Supervisor should use stable intent names
3. **Monitor and adjust**: Check statistics regularly
4. **Let it learn**: System improves over time with more data

## Next Steps

1. Update WebSocket handlers to use new clients
2. Modify supervisor to feed classifications back
3. Add monitoring dashboards for intent statistics
4. Test with real user queries to build patterns