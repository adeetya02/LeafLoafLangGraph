# LeafLoaf Codebase Flow Diagrams 🔄

## 1. Complete System Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        BR[Browser/App]
        VOICE[Voice Input]
        TEXT[Text Input]
    end
    
    subgraph "API Layer (src/api/)"
        WS[WebSocket Endpoint<br/>voice_deepgram_endpoint.py]
        HTTP[HTTP Endpoints<br/>main.py]
        CONV[Conversational<br/>voice_deepgram_conversational.py]
    end
    
    subgraph "Voice Processing (src/voice/)"
        DG[Deepgram Nova-3<br/>nova3_client.py]
        VM[Voice Metadata<br/>Extractor]
        TTS[TTS Manager<br/>tts_manager.py]
    end
    
    subgraph "Core Orchestration (src/core/)"
        GRAPH[LangGraph<br/>graph.py]
        STATE[SearchState<br/>state.py]
    end
    
    subgraph "Multi-Agent System (src/agents/)"
        SUP[Supervisor<br/>supervisor_optimized.py]
        PS[Product Search<br/>product_search.py]
        OA[Order Agent<br/>order_agent.py]
        PA[Promotion Agent<br/>promotion_agent.py]
        RC[Response Compiler<br/>response_compiler.py]
    end
    
    subgraph "Memory System (src/memory/)"
        MM[Memory Manager<br/>memory_manager.py]
        GW[Graphiti Wrapper<br/>graphiti_wrapper.py]
        SM[Session Memory<br/>session_memory.py]
        SPAN[Spanner Backend<br/>graphiti_memory_spanner.py]
    end
    
    subgraph "Data Layer (src/data/)"
        WV[Weaviate Client<br/>weaviate_optimized.py]
        BQ[BigQuery Client<br/>bigquery_client.py]
    end
    
    subgraph "Tools (src/tools/)"
        ST[Search Tools<br/>search_tools.py]
        OT[Order Tools<br/>order_tools.py]
        RT[Recommendation Tools<br/>recommendation_tools.py]
    end
    
    %% Client connections
    BR --> HTTP
    VOICE --> WS
    VOICE --> CONV
    TEXT --> HTTP
    
    %% API to Voice
    WS --> DG
    CONV --> DG
    DG --> VM
    
    %% Voice to Core
    VM --> STATE
    HTTP --> STATE
    STATE --> GRAPH
    
    %% Core to Agents
    GRAPH --> SUP
    SUP --> PS
    SUP --> OA
    SUP --> PA
    PS --> RC
    OA --> RC
    PA --> RC
    
    %% Agents to Memory
    SUP --> MM
    PS --> MM
    OA --> MM
    MM --> GW
    MM --> SM
    GW --> SPAN
    
    %% Agents to Tools
    PS --> ST
    OA --> OT
    PS --> RT
    
    %% Tools to Data
    ST --> WV
    OT --> SM
    RT --> BQ
    
    %% Response flow
    RC --> TTS
    TTS --> BR
```

## 2. Voice Processing Pipeline

```mermaid
sequenceDiagram
    participant C as Client
    participant WS as WebSocket<br/>(voice_deepgram_endpoint)
    participant DG as Deepgram<br/>(nova3_client)
    participant VM as Voice Analyzer
    participant S as Supervisor
    participant A as Agent
    participant RC as Response Compiler
    participant TTS as TTS Service
    
    C->>WS: Audio Stream (PCM 16-bit)
    WS->>DG: Forward Audio
    DG->>DG: STT Processing
    DG-->>WS: Transcript + Metadata
    
    WS->>VM: Extract Voice Characteristics
    Note over VM: Pace, Emotion,<br/>Urgency, Volume
    
    VM->>S: SearchState with<br/>Voice Metadata
    
    S->>S: Analyze Intent +<br/>Voice Context
    Note over S: Calculate alpha,<br/>routing decision,<br/>response style
    
    S->>A: Route to Agent
    A->>A: Process with<br/>Memory Context
    A-->>RC: Results
    
    RC->>RC: Compile Response<br/>with Voice Adaptation
    RC->>TTS: Generate Audio
    TTS-->>C: Audio Response
```

## 3. Memory Integration Flow

```mermaid
graph LR
    subgraph "Query Processing"
        Q[User Query] --> EE[Entity Extraction]
        VM[Voice Metadata] --> EE
    end
    
    subgraph "Memory Manager (memory_manager.py)"
        EE --> MR[Memory Registry]
        MR --> MC{Memory<br/>Context}
    end
    
    subgraph "Graphiti System"
        MC --> GW[Graphiti Wrapper]
        GW --> E[Entities]
        GW --> R[Relationships]
        E --> SPAN[(Spanner DB)]
        R --> SPAN
    end
    
    subgraph "Personalization Features"
        MC --> P1[Smart Search Ranking]
        MC --> P2[My Usual]
        MC --> P3[Reorder Intelligence]
        MC --> P4[Dietary Filters]
        MC --> P5[Cultural Preferences]
        MC --> P6[Complementary Products]
        MC --> P7[Quantity Memory]
        MC --> P8[Budget Awareness]
        MC --> P9[Household Patterns]
        MC --> P10[Seasonal Patterns]
    end
    
    subgraph "Agent Processing"
        P1 --> AG[Agent Decision]
        P2 --> AG
        P3 --> AG
        P4 --> AG
        P5 --> AG
        P6 --> AG
        P7 --> AG
        P8 --> AG
        P9 --> AG
        P10 --> AG
    end
    
    AG --> NR[New Relationships]
    NR --> SPAN
```

## 4. Agent Communication Pattern

```mermaid
stateDiagram-v2
    [*] --> SearchState: Initial Request
    
    SearchState --> Supervisor: Voice + Query
    
    Supervisor --> ProductSearch: product_search intent
    Supervisor --> OrderAgent: order_management intent
    Supervisor --> PromotionAgent: promotion_query intent
    Supervisor --> ResponseCompiler: general_chat intent
    
    ProductSearch --> ResponseCompiler: search_results
    OrderAgent --> ResponseCompiler: order_updates
    PromotionAgent --> ResponseCompiler: promotions
    
    ResponseCompiler --> [*]: Final Response
    
    note right of Supervisor
        Voice-Native Analysis:
        - Intent classification
        - Alpha calculation
        - Response style
        - Urgency detection
    end note
    
    note right of ProductSearch
        Memory-Aware Search:
        - Personalized ranking
        - Dietary filtering
        - Cultural preferences
    end note
    
    note right of OrderAgent
        React Pattern:
        - Tool selection
        - Cart operations
        - Quantity suggestions
    end note
```

## 5. Data Flow Through Key Files

```
1. ENTRY POINTS
   ├── run.py → FastAPI server startup
   ├── src/api/main.py → Route configuration
   └── src/api/voice_deepgram_endpoint.py → WebSocket handler

2. VOICE PROCESSING
   ├── src/voice/deepgram/nova3_client.py → STT streaming
   ├── src/voice/processors/transcript_processor.py → Analysis
   └── src/voice/synthesis/tts_manager.py → Speech synthesis

3. ORCHESTRATION
   ├── src/core/graph.py → LangGraph workflow
   ├── src/models/state.py → State definitions
   └── src/core/state_manager.py → State persistence

4. AGENT EXECUTION
   ├── src/agents/memory_aware_base.py → Base class
   ├── src/agents/supervisor_optimized.py → Routing
   ├── src/agents/product_search.py → Search execution
   └── src/agents/response_compiler.py → Response formatting

5. MEMORY OPERATIONS
   ├── src/memory/memory_manager.py → Unified interface
   ├── src/memory/graphiti_wrapper.py → Graphiti ops
   └── src/memory/graphiti_memory_spanner.py → Storage

6. DATA ACCESS
   ├── src/data/weaviate_optimized.py → Vector search
   ├── src/analytics/bigquery_client.py → Analytics
   └── src/utils/redis_manager.py → Session cache
```

## 6. Voice Metadata Influence

```mermaid
graph TD
    VM[Voice Metadata] --> |Pace: fast<br/>Urgency: high| A1[Alpha = 0.3<br/>Keyword Focus]
    VM --> |Pace: slow<br/>Exploring| A2[Alpha = 0.7<br/>Semantic Focus]
    VM --> |Normal| A3[Alpha = 0.5<br/>Balanced]
    
    VM --> |Frustrated| R1[Brief, Empathetic<br/>Response]
    VM --> |Happy| R2[Detailed, Enthusiastic<br/>Response]
    VM --> |Neutral| R3[Standard<br/>Response]
    
    VM --> |Loud + Fast| T1[Quick Timeout<br/>200ms]
    VM --> |Quiet + Slow| T2[Patient Timeout<br/>2500ms]
    
    A1 --> WV[Weaviate Search]
    A2 --> WV
    A3 --> WV
    
    R1 --> RC[Response Compiler]
    R2 --> RC
    R3 --> RC
    
    T1 --> SUP[Supervisor]
    T2 --> SUP
```

## 7. Error Handling & Fallback Chain

```mermaid
graph TD
    REQ[Request] --> TRY1{Try Primary}
    
    TRY1 -->|Success| RESP[Response]
    TRY1 -->|Timeout 50ms| FB1[Memory Fallback]
    TRY1 -->|Model Error| FB2[Model Fallback]
    TRY1 -->|Search Error| FB3[Search Fallback]
    
    FB1 --> |Skip Memory| CONT[Continue Processing]
    
    FB2 --> |HuggingFace| TRY2{Try Secondary}
    TRY2 -->|Success| RESP
    TRY2 -->|Fail| FB4[Groq Fallback]
    FB4 --> |Success| RESP
    FB4 --> |Fail| DEF[Default Response]
    
    FB3 --> |BM25 Only| RESP
    
    CONT --> RESP
    DEF --> RESP
    
    style FB1 fill:#f9f,stroke:#333,stroke-width:2px
    style FB2 fill:#f9f,stroke:#333,stroke-width:2px
    style FB3 fill:#f9f,stroke:#333,stroke-width:2px
    style FB4 fill:#f9f,stroke:#333,stroke-width:2px
```

## 8. Performance Optimization Points

```
PARALLELIZATION POINTS:
├── Memory fetch + LLM analysis (parallel)
├── Multiple tool calls (concurrent execution)
├── BigQuery streaming (fire-and-forget)
└── Connection pooling (Weaviate)

CACHING LAYERS:
├── In-memory session state
├── Redis cache (when enabled)
├── Connection pool reuse
└── Model instance caching

TIMEOUT STRATEGY:
├── Memory: 50-100ms
├── LLM: 200-2500ms (environment-aware)
├── Search: 300-400ms
└── Total voice: <2s target
```

## Key Code Paths

### Voice Request (Most Common)
1. `voice_deepgram_endpoint.py` → WebSocket connection
2. `nova3_client.py` → Audio processing
3. `supervisor_optimized.py` → Intent analysis
4. `product_search.py` → Product search
5. `response_compiler.py` → Format response
6. Return to client

### Cart Operation
1. `voice_deepgram_endpoint.py` → WebSocket
2. `supervisor_optimized.py` → Route to order
3. `order_agent.py` → Tool selection
4. `order_tools.py` → Cart operation
5. `session_memory.py` → Update cart
6. `response_compiler.py` → Confirm

### Memory Learning
1. User interaction → Entity extraction
2. `graphiti_wrapper.py` → Process entities
3. `graphiti_memory_spanner.py` → Store relationships
4. Future queries → Retrieve context
5. Apply personalization

This comprehensive flow diagram shows how all components in the LeafLoaf codebase work together to provide a voice-native, personalized grocery shopping experience.