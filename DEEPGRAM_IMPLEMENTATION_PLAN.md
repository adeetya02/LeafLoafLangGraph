# Deepgram Implementation Plan for LeafLoaf Voice Commerce

## Overview
Unified voice pipeline using Deepgram for STT + Intelligence + TTS, with comprehensive logging for ML and Graphiti personalization.

## 🎯 Open Items & Tasks

### 1. Deepgram Account Setup
- [ ] Get Deepgram API key with access to:
  - Nova-2 STT model (best for conversational AI)
  - Audio Intelligence features (sentiment, intent, topics)
  - Aura TTS (for response generation)
- [ ] Estimate usage and costs:
  - STT: $0.0059/minute
  - Audio Intelligence: +$0.0025/minute
  - Aura TTS: ~$0.015/1000 characters
- [ ] Set up usage alerts and limits

### 2. Audio Intelligence Configuration
- [ ] Enable all intelligence features:
  ```
  - sentiment: true
  - intent: true
  - topics: true
  - summarize: true
  - detect_language: true
  - detect_entities: true
  - measurements: true (for quantities like "2 gallons")
  ```
- [ ] Custom vocabulary for grocery terms:
  ```
  - Brand names: "Organic Valley", "Horizon", "Chobani"
  - Indian items: "sabzi", "dal", "atta", "ghee"
  - Measurements: "gallon", "pound", "dozen"
  - Store sections: "dairy", "produce", "bakery"
  ```
- [ ] Keyword boosting for important terms

### 3. Data Capture Architecture
- [ ] Real-time streaming to three destinations:
  1. **BigQuery** - Raw conversation warehouse
  2. **Graphiti** - User insights and relationships
  3. **Redis** - Session state and hot data

- [ ] Schema design for each destination
- [ ] Implement buffering for reliability
- [ ] Set up data retention policies

### 4. ML Data Pipeline
- [ ] Capture for "ease of finding products":
  ```
  - Time to successful search
  - Number of query refinements
  - Sentiment progression during search
  - Intent clarity scores
  - Abandoned vs completed searches
  ```

- [ ] Features to extract:
  ```
  Voice Features:
  - Speaking pace
  - Hesitation patterns
  - Emotion indicators
  - Confidence levels
  
  Behavioral Features:
  - Query complexity
  - Brand specificity
  - Category navigation
  - Correction patterns
  
  Outcome Features:
  - Search success rate
  - Time to cart addition
  - Cart abandonment
  - Satisfaction indicators
  ```

### 5. Graphiti Integration Enhancements
- [ ] New relationship types:
  ```
  SPEAKS_WITH_EMOTION -> [urgency, excitement, frustration]
  PREFERS_INTERACTION_STYLE -> [brief, detailed, conversational]
  STRUGGLES_TO_FIND -> [product_category]
  CONFIDENTLY_ORDERS -> [product_type]
  ```

- [ ] Voice-based user properties:
  ```
  {
    "communication_profile": {
      "typical_sentiment": "positive",
      "urgency_triggers": ["almost out", "need today"],
      "preferred_response_length": "brief",
      "accent_region": "south_asian",
      "code_switching_frequency": 0.3
    },
    "search_behavior": {
      "avg_time_to_find": 23.5,
      "refinement_count": 1.2,
      "success_rate": 0.89,
      "problematic_categories": ["spices", "ethnic_foods"]
    }
  }
  ```

### 6. Testing Framework
- [ ] Create test scenarios for:
  ```
  1. Multi-accent testing (US, UK, Indian, Spanish)
  2. Background noise scenarios
  3. Emotional state variations
  4. Code-switching conversations
  5. Complex queries with corrections
  ```

- [ ] Metrics to track:
  ```
  - Transcription accuracy by accent
  - Intent detection accuracy
  - Sentiment correlation with outcomes
  - Time to understanding
  - User satisfaction scores
  ```

### 7. Privacy & Compliance (Post-Test Phase)
- [ ] Define data handling:
  ```
  - Audio storage: Yes/No
  - Transcription retention: 90 days
  - Anonymization rules
  - User consent flow
  - Data deletion API
  ```

- [ ] Compliance checklist:
  ```
  - GDPR requirements
  - CCPA requirements
  - COPPA (if family accounts)
  - Industry standards
  ```

## 📊 Success Metrics

### User Experience
- **Search Success Rate**: >90% find products in <3 attempts
- **Time to Cart**: <30 seconds for regular items
- **Sentiment Improvement**: Negative → Positive during session
- **Task Completion**: >85% of intents fulfilled

### ML Model Performance
- **Intent Accuracy**: >95% for common intents
- **Product Matching**: >90% correct on first try
- **Reorder Prediction**: Within 2 days of need
- **Churn Prediction**: 80% accuracy at 30 days

### Business Impact
- **Conversion Rate**: Voice > Text by 20%
- **Cart Size**: +15% with voice suggestions
- **Customer Retention**: +25% for voice users
- **Support Tickets**: -40% for voice users

## 🚀 Implementation Phases

### Phase 1: Basic Integration (Week 1)
- Deepgram STT with streaming
- Basic intent detection
- Simple TTS responses
- Session logging to BigQuery

### Phase 2: Intelligence Layer (Week 2)
- All audio intelligence features
- Graphiti integration
- Real-time personalization
- A/B testing framework

### Phase 3: ML Pipeline (Week 3)
- Feature extraction pipeline
- First ML models (intent, satisfaction)
- Personalization engine v2
- Performance optimization

### Phase 4: Advanced Features (Week 4+)
- Proactive suggestions
- Emotional response adaptation
- Multi-language support
- Family member detection

## 🔧 Technical Decisions

### Streaming vs Batch
- **Decision**: Streaming for real-time feel
- **Buffer Strategy**: 250ms chunks
- **Interruption Handling**: Immediate audio stop

### Data Storage
- **Hot Storage**: Redis (last 24 hours)
- **Warm Storage**: BigQuery (90 days)
- **Cold Storage**: GCS (1 year)
- **Graphiti**: Persistent in Spanner

### ML Architecture
- **Real-time Models**: Vertex AI endpoints
- **Batch Training**: Vertex AI pipelines
- **Feature Store**: Feast on BigQuery
- **Model Registry**: Vertex AI Model Registry

## 📝 Next Steps

1. **Get Deepgram API access** with all features
2. **Design BigQuery schema** for conversation data
3. **Create Graphiti voice relationships**
4. **Build prototype** with streaming
5. **Start collecting test data**

## 🤔 Open Questions

1. **Voice Authentication**: Add voiceprint ID?
2. **Multilingual Strategy**: One model or many?
3. **Edge Cases**: How to handle kids ordering?
4. **Feedback Loop**: Explicit or implicit learning?
5. **Response Personality**: Consistent or adaptive?

---

*This document will evolve as we implement and learn from real user interactions.*