# Next Session Prompt - Multi-Modal Voice-Native Supervisor

## Primary Focus
Enhance `OptimizedSupervisorAgent` to be memory-aware, multi-modal, and voice-native while maintaining <300ms performance.

## Key Tasks

### 1. Make OptimizedSupervisorAgent Memory-Aware
- Change inheritance from `BaseAgent` to `MemoryAwareAgent`
- Implement `_get_agent_specific_context` method
- Add Graphiti integration for routing patterns
- Maintain performance with parallel memory fetching

### 2. Fix Critical Memory Issues
- Uncomment session memory integration in `graphiti_memory_spanner.py:200`
- Increase memory timeouts from 50ms to 500ms
- Add retry logic for Spanner queries
- Implement proper health checks

### 3. Implement Voice-Native Features
- Word-level streaming for <200ms first audio
- Voice urgency detection from prosody
- Streaming routing decisions
- Interrupt handling

### 4. Add Multi-Modal Support (Phase 2)
- Image input handling with OCR
- Visual product search
- Multi-modal context fusion
- Upgrade to Gemini 2.5 Pro

## Reference
See `/Users/adi/Desktop/LeafLoafLangGraph/WORKING_DOCUMENT.md` for complete context.

## Test After Implementation
```bash
python3 run.py
# Voice: http://localhost:8080/static/voice_conversational.html
# Test: "Do you have bell peppers?" → Should show 20 products with personalization
```