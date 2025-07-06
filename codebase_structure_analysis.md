# LeafLoaf LangGraph - Comprehensive Codebase Documentation

## Project Overview

LeafLoaf is a production-grade grocery shopping system built with a sophisticated multi-agent architecture using LangGraph. The system features voice-native AI, personalized search, and real-time learning capabilities.

## Directory Structure Overview

```
src/
├── agents/              # Multi-agent system components
├── analytics/           # Analytics and tracking
├── api/                 # FastAPI endpoints and voice interfaces
├── cache/              # Redis caching layer
├── config/             # Configuration management
├── core/               # Core system components (LangGraph)
├── data_capture/       # Data capture strategies
├── integrations/       # External service integrations
├── jobs/               # Background jobs and schedulers
├── memory/             # Memory systems (Graphiti, Spanner)
├── middleware/         # API middleware
├── ml/                 # Machine learning components
├── models/             # Data models and state definitions
├── monitoring/         # System monitoring
├── personalization/    # Personalization features
├── services/           # Business logic services
├── tests/              # Test suites
├── tools/              # Agent tools
├── tracing/            # Distributed tracing
├── utils/              # Utility functions
└── voice/              # Voice processing pipeline
```

## Core System Architecture

### 1. Entry Points (`src/api/`)

The system has multiple entry points for different use cases:

#### Main API Endpoints
- **`main.py`**: Primary FastAPI application with search, cart, and order endpoints
- **`main_production.py`**: Production-optimized version with enhanced monitoring
- **`main_thin.py`**: Lightweight version for specific deployments

#### Voice Endpoints (30+ implementations!)
- **HTTP-based**: `voice_http.py`, `voice_streaming.py`, `voice_sse.py`
- **WebSocket-based**: `voice_websocket.py`, `voice_conversational.py`
- **Deepgram Integration**: Multiple variants for different use cases
  - `voice_deepgram_enhanced.py`: Enhanced with metadata processing
  - `voice_deepgram_dynamic_intents.py`: Dynamic intent learning
  - `voice_deepgram_conversational.py`: Full conversational flow
- **Google/Gemini Integration**: 
  - `voice_gemini_native.py`: Native Gemini voice
  - `voice_google_unified.py`: Unified Google services
  - `voice_vertex_personalized.py`: Vertex AI with personalization

### 2. Core Graph System (`src/core/`)

The heart of the system using LangGraph:

- **`graph.py`**: Main LangGraph orchestration
  - Defines the agent workflow
  - Routes between supervisor → search → order → compiler
  - Manages state transitions
  
- **`graph_v2.py`**: Enhanced version with parallel execution
- **`parallel_graph.py`**: Experimental parallel agent execution
- **`config_manager.py`**: Centralized configuration management

### 3. Multi-Agent System (`src/agents/`)

#### Primary Agents
1. **Supervisor Agents** (Multiple Implementations):
   - `supervisor_optimized.py`: Production supervisor with Gemma 2 9B
   - `supervisor_voice_native.py`: Voice-aware routing
   - `supervisor_dynamic_intents.py`: Dynamic intent learning
   
2. **Search Agent**:
   - `product_search.py`: Weaviate hybrid search with voice-driven alpha
   - Inherits from `memory_aware_base.py`
   
3. **Order Agent**:
   - `order_agent.py`: React pattern with cart management tools
   - Full CRUD operations for cart
   
4. **Response Compiler**:
   - `response_compiler.py`: Merges results with voice adaptation
   
5. **Specialized Agents**:
   - `conversational_agent.py`: Natural conversation handling
   - `promotion_agent.py`: Promotion management
   - `personalized_ranker.py`: Re-ranking based on preferences

#### Personalization Agents
- `dietary_cultural_intelligence.py`: Dietary restriction handling
- `my_usual_analyzer.py`: Regular purchase patterns
- `reorder_intelligence.py`: Predictive restocking

### 4. Memory Systems (`src/memory/`)

Complex memory architecture with multiple backends:

#### Core Memory Components
- **`memory_registry.py`**: Registry pattern for memory instances
- **`memory_manager.py`**: Base memory management
- **`improved_memory_manager.py`**: Enhanced with multi-backend support
- **`memory_interfaces.py`**: Abstract interfaces for backends

#### Graphiti Integration
- **`graphiti_memory.py`**: Core Graphiti memory implementation
- **`graphiti_memory_spanner.py`**: Google Spanner backend
- **`graphiti_wrapper.py`**: User/session management wrapper
- **`graphiti_vertex_ai.py`**: Vertex AI integration

#### Session Management
- **`session_memory.py`**: In-memory session storage
- **`firestore_session.py`**: Firestore session persistence
- **`conversation_memory.py`**: Conversation history tracking

#### Entity Extraction
- **`gemini_entity_extractor.py`**: Gemini-based extraction
- **`vertex_ai_entity_extractor.py`**: Vertex AI extraction
- **`production_entity_extractor.py`**: Production-optimized

### 5. Voice Processing (`src/voice/`)

Sophisticated voice handling with multiple providers:

#### Core Voice Components
- **`deepgram/`**: Deepgram SDK integration
  - `conversational_client.py`: Full duplex STT/TTS
  - `streaming_client.py`: Real-time streaming
  - `dynamic_intent_learner.py`: Intent learning from voice
  
- **`models/`**: Voice model implementations
  - `gemini_voice.py`: Gemini voice processing
  - `voice_prompts.py`: Voice-specific prompts

#### Voice Handlers
- **`production_voice_handler.py`**: Production voice processing
- **`google_voice_handler.py`**: Google Cloud Speech integration
- **`conversation_insights.py`**: Voice metadata extraction

### 6. Integrations (`src/integrations/`)

External service connections:

#### LLM Clients
- **`gemma_client.py`**: Base Gemma integration
- **`gemma_production_client.py`**: Production-optimized
- **`llm_client.py`**: Generic LLM interface

#### Database Clients
- **`weaviate_client_optimized.py`**: Optimized Weaviate search
- **`spanner_graph_client.py`**: Spanner graph operations
- **`neo4j_config.py`**: Neo4j configuration

#### Voice Services
- **`elevenlabs_voice.py`**: ElevenLabs TTS
- **`voice_analyzer.py`**: Voice characteristic analysis

### 7. Personalization Engine (`src/personalization/`)

Self-learning personalization features:

- **`graphiti_personalization_engine.py`**: Core personalization with Graphiti
- **`instant_personalizer.py`**: Real-time personalization
- **`dietary_cultural_filter.py`**: Dietary/cultural filtering
- **`complementary_products.py`**: Product pairing suggestions
- **`quantity_memory.py`**: Purchase quantity patterns
- **`budget_awareness.py`**: Price sensitivity detection
- **`household_intelligence.py`**: Multi-member household patterns

### 8. Analytics & Monitoring (`src/analytics/`)

- **`bigquery_client.py`**: BigQuery streaming analytics
- **`voice_analytics.py`**: Voice-specific analytics

### 9. Caching Layer (`src/cache/`)

Redis-based caching with feature flags:

- **`redis_manager.py`**: Core Redis operations
- **`redis_feature.py`**: Feature flag management
- **`redis_design.py`**: Cache design patterns

### 10. Tools (`src/tools/`)

Agent tool implementations:

- **`order_tools.py`**: Cart management tools (add, remove, update, confirm)
- **`search_tools.py`**: Search-related tools
- **`tool_executor.py`**: Tool execution framework

## Data Flow Architecture

```
User Request → API Endpoint → Graph Orchestration → Agent Pipeline → Response

1. Voice/Text Input
   ↓
2. API Layer (FastAPI)
   - Voice processing (STT)
   - Request validation
   - Session management
   ↓
3. LangGraph Orchestration
   - State initialization
   - Agent routing
   ↓
4. Supervisor Agent
   - Intent analysis
   - Voice metadata processing
   - Routing decision
   ↓
5. Specialized Agents (parallel/sequential)
   - Product Search (Weaviate)
   - Order Management (React)
   - Promotion Check
   ↓
6. Memory Systems
   - Graphiti learning
   - Session persistence
   - Pattern extraction
   ↓
7. Response Compilation
   - Result merging
   - Voice adaptation
   - Personalization
   ↓
8. Output Processing
   - TTS (for voice)
   - JSON response
   - Analytics capture
```

## Key Design Patterns

### 1. Agent Factory Pattern
```python
# src/core/graph.py
def create_supervisor():
    """Create a new supervisor instance for each request"""
    return SupervisorReactAgent()
```

### 2. Memory-Aware Agent Pattern
```python
# All agents inherit from MemoryAwareAgent
class OptimizedSupervisorAgent(MemoryAwareAgent):
    async def get_memory_context(self, user_id, session_id, query):
        return await self._get_agent_specific_context(...)
```

### 3. Registry Pattern
```python
# src/memory/memory_registry.py
MemoryRegistry.register("default", GraphitiMemoryWrapper())
```

### 4. Voice Metadata Flow
```python
# Voice characteristics influence search and response
voice_metadata = {
    "pace": "fast",
    "emotion": "urgent",
    "volume": 0.8
}
# → alpha = 0.3 (keyword-focused search)
```

## Configuration Structure

### Environment Configuration
- `.env.yaml`: Base environment variables
- `.env.production.yaml`: Production overrides
- `src/config/settings.py`: Settings management
- `src/config/constants.py`: System constants
- `src/config/voice_config.py`: Voice-specific configuration

### Agent Configuration
- `config/agent_priorities.yaml`: Agent routing priorities
- `config/product_attributes.py`: Product search attributes

## Testing Infrastructure

- **Unit Tests**: Component-level testing
- **Integration Tests**: `test_voice_scenarios_comprehensive.py`
- **Personalization Tests**: `run_all_personalization_tests.py` (103 tests)
- **Synthetic Data**: `synthetic_user_generator.py`

## Deployment Structure

### Local Development
```bash
python3 run.py  # Main API server
python3 -m src.api.voice_deepgram_conversational  # Voice WebSocket
```

### Production (GCP)
- Cloud Run deployment
- Spanner for graph storage
- BigQuery for analytics
- Vertex AI for LLMs

## Performance Characteristics

### Latency Breakdown
- **Total Response**: 1.3-1.5s (voice)
- **Supervisor**: 500-800ms
- **Search**: 300-400ms
- **Compilation**: 100-200ms
- **Voice Overhead**: 100-200ms

### Scalability Features
- Stateless agents
- Redis caching
- Parallel agent execution
- Stream processing

## Security & Error Handling

- Environment-aware model selection
- Graceful fallbacks
- Comprehensive error logging
- API key management
- Session isolation

## Future Architecture Considerations

1. **Multi-modal Support**: Architecture ready for voice + image + text
2. **Streaming Enhancements**: True streaming for voice responses
3. **Distributed Agents**: Agent deployment across services
4. **Advanced Caching**: Predictive cache warming
5. **ML Pipeline**: Real-time model updates

This architecture represents a sophisticated, production-ready system that balances performance, scalability, and maintainability while providing cutting-edge voice-native AI capabilities for grocery shopping.