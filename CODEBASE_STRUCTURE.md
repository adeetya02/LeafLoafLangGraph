# LeafLoaf LangGraph Codebase Structure 🏗️

## Complete Codebase Map

```
LeafLoafLangGraph/
│
├── src/                              # Main source code
│   ├── agents/                       # Multi-agent system components
│   │   ├── __init__.py
│   │   ├── memory_aware_base.py     # Base class for all agents (memory integration)
│   │   ├── supervisor_optimized.py  # Voice-native supervisor with Gemma 2 9B
│   │   ├── product_search.py        # Product search agent with Weaviate
│   │   ├── order_agent.py           # Cart management with React pattern
│   │   ├── response_compiler.py     # Response formatting and compilation
│   │   └── promotion_agent.py       # Deals and promotions handling
│   │
│   ├── api/                          # API endpoints and routers
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app setup and configuration
│   │   ├── voice_deepgram_endpoint.py      # Main Deepgram WebSocket endpoint
│   │   ├── voice_deepgram_conversational.py # Conversational voice interface
│   │   ├── voice_deepgram_with_metadata.py # Voice with metadata extraction
│   │   ├── voice_http_endpoint.py   # HTTP polling for Cloud Run
│   │   └── [30+ voice endpoints]    # Various voice implementations
│   │
│   ├── core/                         # Core system components
│   │   ├── __init__.py
│   │   ├── graph.py                 # LangGraph orchestration and workflow
│   │   ├── state_manager.py         # Global state management
│   │   └── constants.py             # System-wide constants
│   │
│   ├── memory/                       # Memory and personalization systems
│   │   ├── __init__.py
│   │   ├── memory_manager.py        # Unified memory management
│   │   ├── memory_registry.py       # Registry pattern for backends
│   │   ├── graphiti_wrapper.py      # Graphiti integration wrapper
│   │   ├── graphiti_memory_spanner.py # Spanner backend for Graphiti
│   │   ├── session_memory.py        # Session state management
│   │   └── preference_service.py    # User preference handling
│   │
│   ├── tools/                        # Agent tools and utilities
│   │   ├── __init__.py
│   │   ├── search_tools.py          # Product search tools
│   │   ├── order_tools.py           # Cart operation tools
│   │   ├── tool_executor.py         # Tool execution framework
│   │   └── recommendation_tools.py  # ML recommendation tools
│   │
│   ├── voice/                        # Voice processing components
│   │   ├── __init__.py
│   │   ├── deepgram/                # Deepgram integration
│   │   │   ├── nova3_client.py     # Nova-3 streaming client
│   │   │   ├── streaming_client.py  # Basic streaming client
│   │   │   └── conversational_client.py # Full duplex client
│   │   ├── processors/              # Voice processors
│   │   │   ├── transcript_processor.py # Transcript analysis
│   │   │   └── voice_analyzer.py   # Voice characteristic analysis
│   │   └── synthesis/               # TTS components
│   │       ├── tts_manager.py       # TTS management
│   │       └── voice_params.py      # Voice synthesis parameters
│   │
│   ├── models/                       # Data models and schemas
│   │   ├── __init__.py
│   │   ├── state.py                 # SearchState and other states
│   │   ├── product.py               # Product data models
│   │   ├── order.py                 # Order and cart models
│   │   └── voice_metadata.py        # Voice metadata models
│   │
│   ├── config/                       # Configuration management
│   │   ├── __init__.py
│   │   ├── settings.py              # Environment settings
│   │   ├── constants.py             # Application constants
│   │   ├── product_attributes.py    # Product attribute definitions
│   │   └── agent_priorities.yaml    # Agent routing priorities
│   │
│   ├── utils/                        # Utility functions
│   │   ├── __init__.py
│   │   ├── id_generator.py          # ID generation utilities
│   │   ├── logging_setup.py         # Structured logging setup
│   │   ├── async_helpers.py         # Async utility functions
│   │   └── redis_manager.py         # Redis connection management
│   │
│   ├── analytics/                    # Analytics and ML
│   │   ├── __init__.py
│   │   ├── bigquery_client.py       # BigQuery integration
│   │   ├── event_tracker.py         # Event tracking
│   │   └── ml_recommendations.py    # ML recommendation engine
│   │
│   ├── personalization/              # Personalization features
│   │   ├── __init__.py
│   │   ├── graphiti_engine.py       # Graphiti-based personalization
│   │   ├── smart_search.py          # Personalized search ranking
│   │   ├── reorder_intelligence.py  # Reorder predictions
│   │   └── dietary_intelligence.py  # Dietary preference handling
│   │
│   ├── data/                         # Data access layer
│   │   ├── __init__.py
│   │   ├── weaviate_client.py       # Weaviate connection
│   │   ├── weaviate_optimized.py    # Optimized Weaviate client
│   │   └── product_loader.py        # Product data loading
│   │
│   └── static/                       # Static HTML files
│       ├── voice_test.html          # Voice testing interface
│       ├── voice_conversational.html # Conversational interface
│       └── [various test pages]      # Testing interfaces
│
├── tests/                            # Test suite
│   ├── __init__.py
│   ├── conftest.py                  # Pytest configuration
│   ├── README.md                    # Test documentation
│   ├── agents/                      # Agent tests
│   ├── deepgram/                    # Deepgram tests
│   ├── voice/                       # Voice tests
│   ├── memory/                      # Memory tests
│   ├── integration/                 # Integration tests
│   └── implementation/              # Work-in-progress implementations
│       └── deepgram/                # Deepgram streaming tests
│
├── scripts/                          # Utility scripts
│   ├── test_*.py                    # Various test scripts
│   ├── run_*.py                     # Execution scripts
│   └── setup_*.py                   # Setup scripts
│
├── docs/                             # Documentation
│   ├── SYSTEM_ARCHITECTURE.md       # System design
│   ├── API_DOCUMENTATION.md         # API docs
│   └── [extensive documentation]     # Various docs
│
├── config/                           # Configuration files
│   ├── agent_priorities.yaml        # Agent routing config
│   └── prompts/                     # LLM prompts
│
├── data/                             # Data files
│   └── suppliers/                   # Supplier catalogs
│
└── Root Files
    ├── run.py                       # Main application runner
    ├── run_tests.py                 # Test runner
    ├── requirements.txt             # Python dependencies
    ├── .env.yaml                    # Environment variables
    └── CLAUDE.md                    # AI context documentation
```

## 🔑 Key Components Deep Dive

### 1. Multi-Agent System (`src/agents/`)

#### **Supervisor Agent** (`supervisor_optimized.py`)
- **Purpose**: Routes queries to appropriate agents using voice-aware LLM
- **Key Features**:
  - Voice-native with Gemma 2 9B
  - Environment-aware model selection (HuggingFace ↔ Vertex AI)
  - Voice metadata analysis for routing decisions
  - Timeout adaptation based on urgency
- **Dependencies**: LangChain, Graphiti, Voice metadata

#### **Product Search Agent** (`product_search.py`)
- **Purpose**: Searches products using Weaviate hybrid search
- **Key Features**:
  - Voice-influenced alpha calculation
  - Memory-aware personalization
  - Hybrid search (keyword + vector)
  - Connection pooling for performance
- **Dependencies**: Weaviate, Memory Manager, Search Tools

#### **Order Agent** (`order_agent.py`)
- **Purpose**: Manages cart operations with natural language
- **Key Features**:
  - React pattern for tool selection
  - Memory-aware quantity suggestions
  - Complementary product recommendations
  - State management for cart
- **Dependencies**: Order Tools, Memory Manager, Session Memory

#### **Response Compiler** (`response_compiler.py`)
- **Purpose**: Formats final responses with voice adaptation
- **Key Features**:
  - Section-based compilation
  - Voice synthesis parameter generation
  - Response style adaptation
  - Memory-aware formatting
- **Dependencies**: All agents, Voice parameters

### 2. Voice System (`src/voice/`)

#### **Deepgram Integration** (`deepgram/`)
- **nova3_client.py**: Production-ready Nova-3 streaming client
  - WebSocket connection management
  - Audio format validation (linear16)
  - Keepalive mechanism
  - Ethnic product recognition
  
- **streaming_client.py**: Basic STT streaming
- **conversational_client.py**: Full duplex STT+TTS

#### **Voice Processing Pipeline**
```
Audio Input → Deepgram STT → Transcript + Metadata → Supervisor → Agent Processing → Response → TTS
```

### 3. Memory System (`src/memory/`)

#### **Memory Manager** (`memory_manager.py`)
- **Purpose**: Unified interface for all memory operations
- **Features**:
  - Registry pattern for multiple backends
  - Automatic fallback (Spanner → Neo4j → In-memory)
  - Caching layer
  - Async operations

#### **Graphiti Integration** (`graphiti_wrapper.py`, `graphiti_memory_spanner.py`)
- **Purpose**: Self-learning personalization through graph relationships
- **Features**:
  - Entity extraction (products, preferences, constraints)
  - Relationship tracking (PREFERS, AVOIDS, BOUGHT_WITH)
  - Pattern learning
  - Spanner backend for production

### 4. Core System (`src/core/`)

#### **LangGraph Orchestration** (`graph.py`)
- **Purpose**: Orchestrates multi-agent workflow
- **Key Components**:
  ```python
  # Workflow definition
  workflow = StateGraph(SearchState)
  workflow.add_node("supervisor", supervisor_node)
  workflow.add_node("product_search", product_search_node)
  workflow.add_node("order_agent", order_agent_node)
  workflow.add_node("response_compiler", response_compiler_node)
  
  # Conditional routing
  workflow.add_conditional_edges(
      "supervisor",
      route_based_on_intent,
      {
          "product_search": "product_search",
          "order_agent": "order_agent",
          "general_chat": "response_compiler"
      }
  )
  ```

### 5. API Layer (`src/api/`)

#### **Main Application** (`main.py`)
- FastAPI setup with routers
- Static file serving
- Health checks
- Error handling middleware

#### **Voice Endpoints** (30+ implementations)
- **WebSocket**: Real-time streaming (`voice_deepgram_endpoint.py`)
- **HTTP Polling**: Cloud Run compatible (`voice_http_endpoint.py`)
- **Conversational**: Full duplex voice (`voice_deepgram_conversational.py`)

### 6. Data Access (`src/data/`)

#### **Weaviate Client** (`weaviate_optimized.py`)
- **Features**:
  - Connection pooling (5-10 connections)
  - Health checks
  - Hybrid search implementation
  - Performance optimizations

## 🔄 Data Flow Architecture

### 1. Voice Request Flow
```
1. Client → WebSocket → API Endpoint
2. Audio → Deepgram STT → Transcript + Voice Metadata
3. SearchState created with voice context
4. Supervisor analyzes intent with voice awareness
5. Routes to appropriate agent(s)
6. Agent executes with memory context
7. Response compiled with voice adaptation
8. TTS parameters generated → Audio response
```

### 2. Memory Integration Flow
```
1. User Query → Entity Extraction
2. Graphiti analyzes entities and relationships
3. Memory context retrieved (50-100ms timeout)
4. Context influences:
   - Search parameters (alpha, filters)
   - Result ranking
   - Quantity suggestions
   - Response style
5. New relationships recorded for learning
```

### 3. Personalization Flow
```
1. Query → Memory Context Retrieval
2. 10 Personalization Features Applied:
   - Smart search ranking
   - "My usual" identification
   - Reorder predictions
   - Dietary filtering
   - Cultural preferences
   - Complementary products
   - Quantity memory
   - Budget awareness
   - Household patterns
   - Seasonal preferences
3. Results personalized → Response
```

## 🏗️ Key Design Patterns

### 1. Factory Pattern
```python
# Agent creation to avoid concurrency issues
def create_supervisor():
    return SupervisorReactAgent()
```

### 2. Registry Pattern
```python
# Memory backend registration
class MemoryRegistry:
    def register(name, backend):
        self._backends[name] = backend
```

### 3. Memory-Aware Base Class
```python
class MemoryAwareAgent(BaseAgent):
    async def get_memory_context(self, user_id, session_id, query):
        # Agent-specific memory retrieval
```

### 4. Fire-and-Forget Analytics
```python
# Non-blocking analytics
asyncio.create_task(
    bigquery_client.stream_event(event_data)
)
```

## 🚀 Entry Points

### Main Application
```bash
python run.py  # Starts FastAPI server on port 8080
```

### Key Endpoints
- `/api/v1/search` - Text-based product search
- `/api/v1/voice/deepgram/ws` - Voice WebSocket endpoint
- `/api/v1/cart/*` - Cart operations
- `/health` - Health check

### Test Runner
```bash
python run_tests.py --component deepgram --coverage
```

## 🔧 Configuration

### Environment Variables (`.env.yaml`)
```yaml
DEEPGRAM_API_KEY: "xxx"
WEAVIATE_URL: "https://xxx"
WEAVIATE_API_KEY: "xxx"
HUGGINGFACE_API_KEY: "xxx"
GOOGLE_CLOUD_PROJECT: "xxx"
```

### Agent Configuration (`config/agent_priorities.yaml`)
- Routing priorities
- Intent patterns
- Agent capabilities

## 📊 Performance Characteristics

### Latency Targets
- Voice response: <2s total
- Supervisor: 500-800ms
- Search: 300-400ms
- Memory fetch: 50-100ms
- Response compilation: <100ms

### Optimization Strategies
- Connection pooling
- Parallel processing
- Aggressive timeouts
- Fire-and-forget analytics
- Environment-aware configurations

## 🔍 Debugging & Monitoring

### Logging
- Structured logging with `structlog`
- Request tracing with trace_id
- Performance metrics logged

### Error Handling
- Graceful fallbacks at every level
- Timeout-based degradation
- User-friendly error messages

## 🎯 Extension Points

### Adding New Agents
1. Create agent class inheriting from `MemoryAwareAgent`
2. Implement required methods
3. Add to graph workflow in `core/graph.py`
4. Register in supervisor routing

### Adding New Voice Endpoints
1. Create endpoint in `api/`
2. Implement WebSocket or HTTP handler
3. Integrate with Deepgram client
4. Add voice metadata extraction

### Adding Personalization Features
1. Extend Graphiti relationships
2. Add to memory context retrieval
3. Apply in relevant agents
4. Track outcomes for learning

This codebase represents a sophisticated, production-grade voice-native grocery shopping system with advanced personalization and learning capabilities.