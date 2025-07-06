# LeafLoaf LangGraph - Upcoming Work Plan

## Completed Work ✅
1. **Voice Integration** - Deepgram STT/TTS with multilingual support
2. **Voice-Native Supervisor** - Gemma 2 9B with voice metadata processing
3. **Graphiti Integration** - Production-ready with Spanner backend
4. **Pure Graphiti Learning** - All 10 personalization features migrated
5. **Holistic Voice Analytics Design** - Universal framework for all communities

## Upcoming Work 🚀

### Phase 1: Voice Analytics Implementation (This Week)
1. **Holistic Voice Analyzers**
   - [ ] QuerySpecificityAnalyzer - Detect vague vs specific queries
   - [ ] ConfidenceAnalyzer - Measure certainty in voice
   - [ ] ShoppingModeDetector - Identify shopping patterns (quick_grab, meal_planning, etc.)
   - [ ] ComplexityAnalyzer - Simple vs complex request detection
   - [ ] EmotionalStateDetector - Detect rushed, confused, neutral states

2. **Voice Pipeline Integration**
   - [ ] Enhanced voice metadata collection in voice_streaming_debug.py
   - [ ] Pass holistic analysis through Episodes.metadata
   - [ ] Update supervisor to use holistic insights for routing
   - [ ] Make agents voice-aware (search, order, response compiler)

3. **Testing & Refinement**
   - [ ] Test with diverse voice samples (different accents, speeds, styles)
   - [ ] Tune thresholds for universal applicability
   - [ ] A/B test response adaptations

### Phase 2: Multi-Modal Capabilities (Next Week)
1. **Image Integration**
   - [ ] Product photo recognition
   - [ ] Receipt scanning with OCR
   - [ ] Handwritten list processing
   - [ ] Pantry inventory via photos

2. **Voice + Image Combinations**
   - [ ] "Is this gluten-free?" + product photo
   - [ ] "What can I make?" + ingredients photo
   - [ ] "Order more of this" + empty package
   - [ ] "Find similar but cheaper" + premium product

3. **Multi-Modal State Management**
   - [ ] Unified context handling
   - [ ] Cross-modal verification
   - [ ] Confidence boosting with multiple inputs

### Phase 3: Enhanced Attributes System (Week 3)
1. **Static Attribute Expansion**
   - [ ] Add texture attributes (crunchy, smooth, creamy, etc.)
   - [ ] Add temperature attributes (hot, cold, frozen, etc.)
   - [ ] Add convenience attributes (instant, ready-to-eat, etc.)
   - [ ] Add sustainability attributes (eco-friendly, recyclable, etc.)
   - [ ] Add cuisine/cultural attributes (without stereotyping)

2. **ML-Based Attribute Discovery**
   - [ ] Weekly pattern discovery job
   - [ ] Cluster unknown frequent terms
   - [ ] Auto-suggest new attributes
   - [ ] Admin dashboard for review/approval

3. **Hybrid Attribute System**
   - [ ] Combine static + ML attributes
   - [ ] User-specific attribute learning
   - [ ] Dynamic alpha adjustment based on patterns
   - [ ] Store in Spanner MLAttributes table

### Phase 4: Advanced Features (Week 4+)
1. **Nutrition Tracking**
   - [ ] Nutrition goals in user preferences
   - [ ] Automatic macro counting
   - [ ] Health condition awareness
   - [ ] Meal plan integration

2. **Family Shared Accounts**
   - [ ] Multi-member preferences
   - [ ] "Shopping for" context
   - [ ] Shared lists and budgets
   - [ ] Family dietary matrix

3. **Social Shopping**
   - [ ] Recipe sharing with shopping lists
   - [ ] Group buying capabilities
   - [ ] Trusted recommendations
   - [ ] Community meal planning

4. **Smart Inventory**
   - [ ] Visual inventory tracking
   - [ ] Expiration monitoring
   - [ ] Auto-reorder when low
   - [ ] Waste reduction insights

## Technical Debt & Improvements
1. **Performance**
   - [ ] Optimize voice processing latency (target: <1s)
   - [ ] Improve search relevance (current: needs work)
   - [ ] Cache ML predictions in Redis
   - [ ] Batch Spanner writes

2. **Reliability**
   - [ ] Add circuit breakers for external APIs
   - [ ] Implement proper retry logic
   - [ ] Enhanced error messages
   - [ ] Graceful degradation

3. **Monitoring**
   - [ ] Voice analytics dashboard
   - [ ] Personalization effectiveness metrics
   - [ ] Multi-modal usage tracking
   - [ ] ML attribute discovery monitoring

## Long-term Vision
1. **AR Shopping** - Point camera at shelf, get personalized overlays
2. **Predictive Shopping** - AI suggests cart before you ask
3. **Recipe-First Shopping** - Plan meals, auto-generate optimized shopping
4. **Community Features** - Neighborhood group buys, local farmer connections
5. **Health Integration** - Connect with fitness apps, doctor recommendations

---

# Tomorrow's Prompt

## Context Reminder for Claude:

"Hi Claude! I'm continuing work on LeafLoaf LangGraph, our production-grade grocery shopping system with multi-agent architecture. 

**Current Status:**
- Voice integration complete (Deepgram + Gemma 2 9B)
- Graphiti/Spanner backend working for behavioral learning
- Designed holistic voice analytics framework (not yet implemented)
- Existing product/user attributes system in place

**Today's Focus: Implementing Holistic Voice Analytics**

I want to start implementing the holistic voice analytics we designed yesterday. The goal is to make the system understand not just what users say, but how they say it - detecting shopping modes, confidence levels, urgency, etc. This should work universally for all ethnic communities without stereotyping.

**Key Files:**
- Voice pipeline: `voice_streaming_debug.py`
- Supervisor: `src/agents/supervisor_optimized.py`
- Product Search: `src/agents/product_search.py`
- Order Agent: `src/agents/order_agent.py`
- Spanner schema: Already has flexible JSON fields

**Specific Tasks for Today:**
1. Implement the core analyzer classes (QuerySpecificityAnalyzer, ConfidenceAnalyzer, ShoppingModeDetector)
2. Integrate them into voice_streaming_debug.py
3. Update supervisor to use holistic analysis for better routing
4. Test with sample voice inputs

**Important Notes:**
- Design for universal patterns, not specific ethnicities
- Use existing Spanner JSON fields (no schema changes needed)
- Keep backward compatibility
- Test incrementally (your preferred approach)

Ready to implement voice analytics that makes shopping feel natural for everyone?"

---

## Quick Reference Commands

```bash
# Run local server
python3 run.py

# Test voice streaming
python3 voice_streaming_debug.py

# Run tests
python3 test_voice_scenarios_comprehensive.py

# Check Spanner connection
python3 test_spanner_graphrag.py

# Lint and typecheck
ruff check .
```