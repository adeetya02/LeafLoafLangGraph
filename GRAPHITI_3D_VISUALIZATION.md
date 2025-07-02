# Graphiti 3D Architecture Visualization

## 🎨 3D System Overview

```
                            ┌─────────────────┐
                            │   USER LAYER    │
                            │  (Frontend)     │
                            └────────┬────────┘
                                     │
                          ┌──────────▼──────────┐
                          │    API GATEWAY     │
                          │   (Entry Point)    │
                          └──────────┬──────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │                                 │
         ┌──────────▼──────────┐          ┌──────────▼──────────┐
         │   REAL-TIME PATH    │          │   ANALYTICS PATH    │
         │   (Milliseconds)    │          │     (Seconds)       │
         └──────────┬──────────┘          └──────────┬──────────┘
                    │                                 │
         ┌──────────▼──────────┐          ┌──────────▼──────────┐
         │  AGENT ORCHESTRATOR │          │   EVENT STREAMING   │
         │   (LangGraph)       │          │    (BigQuery)       │
         └──────────┬──────────┘          └──────────┬──────────┘
                    │                                 │
         ┌──────────▼──────────┐          ┌──────────▼──────────┐
         │   GRAPHITI MEMORY   │◄─────────┤  PATTERN EXTRACTOR  │
         │    (Spanner)        │ FEEDBACK │   (Scheduled Jobs)  │
         └─────────────────────┘   LOOP   └─────────────────────┘
```

## 🏗️ Layer-by-Layer Breakdown

### Layer 1: User Interface (Z = 100)
```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   🖥️  Web App    📱 Mobile    🎤 Voice    🔌 API      │
│                                                         │
│   All requests flow down through the API Gateway       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Layer 2: API Gateway (Z = 80)
```
┌─────────────────────────────────────────────────────────┐
│                    API GATEWAY                          │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │
│  │ /search │  │  /cart  │  │ /track  │  │/dashboard│  │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  │
│       └─────────────┴──────┬──────┴─────────────┘      │
│                            ▼                            │
│                    Route Decision                       │
└─────────────────────────────────────────────────────────┘
```

### Layer 3: Processing Split (Z = 60)
```
                    REQUEST ROUTER
                         │
        ┌────────────────┴────────────────┐
        │                                 │
        ▼                                 ▼
┌──────────────┐                ┌──────────────┐
│  SYNC PATH   │                │  ASYNC PATH  │
│              │                │              │
│ • Search     │                │ • Tracking   │
│ • Cart Ops   │                │ • Analytics  │
│ • Real-time  │                │ • Learning   │
└──────────────┘                └──────────────┘
```

### Layer 4: Agent Orchestra (Z = 40)
```
┌─────────────────────────────────────────────────────────┐
│                   AGENT ORCHESTRA                       │
│                                                         │
│  Supervisor ──▶ Product Search ──▶ Order ──▶ Compiler  │
│      │               │              │           │       │
│      └───────────────┴──────────────┴───────────┘       │
│                          │                              │
│                 MEMORY CONTEXT LAYER                    │
│                    (Graphiti Access)                    │
└─────────────────────────────────────────────────────────┘
```

### Layer 5: Data Storage (Z = 20)
```
┌─────────────────────┬─────────────────────┬─────────────────────┐
│     SPANNER         │     BIGQUERY        │     WEAVIATE        │
├─────────────────────┼─────────────────────┼─────────────────────┤
│ • Graph Nodes       │ • Event Streams     │ • Product Vectors   │
│ • Graph Edges       │ • User History      │ • Semantic Search   │
│ • Session State     │ • Materialized Views│ • Product Catalog   │
│ • Real-time Prefs  │ • ML Features       │                     │
└─────────────────────┴─────────────────────┴─────────────────────┘
```

### Layer 6: Feedback Loop (Z = 0)
```
┌─────────────────────────────────────────────────────────┐
│                    FEEDBACK LOOP                        │
│                                                         │
│  BigQuery ──▶ Pattern Extraction ──▶ Quality Check     │
│                                           │             │
│                                           ▼             │
│  Spanner/Graphiti ◀── Pattern Sync ◀── Filter          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## 🔄 Data Flow Animation (Time-based)

### T=0ms: Request Arrives
```
USER ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━▶
     "Find organic milk"
```

### T=10ms: API Gateway
```
     ┌─────────┐
USER─▶│   API   │─▶ Parse request
     └─────────┘    Validate auth
                    Route to agent
```

### T=30ms: Supervisor Agent
```
         ┌──────────┐
API ────▶│Supervisor│────▶ Analyze intent
         └──────────┘      Fetch memory context
                          Route to search
```

### T=50ms: Parallel Execution
```
                    ┌─────────────┐
                 ┌─▶│  Graphiti   │─▶ User preferences
                 │  └─────────────┘
    Supervisor ──┤
                 │  ┌─────────────┐
                 └─▶│  Weaviate   │─▶ Product search
                    └─────────────┘
```

### T=200ms: Response Assembly
```
┌──────────┐     ┌──────────┐     ┌──────────┐
│ Search   │────▶│ Ranker   │────▶│ Compiler │────▶ USER
│ Results  │     │          │     │          │
└──────────┘     └──────────┘     └──────────┘
```

### T=201ms+: Async Learning
```
                    ┌─────────────┐
    Event ─────────▶│  BigQuery   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
    Later ─────────▶│  Pattern    │
                    │ Extraction  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
    Sync ──────────▶│  Graphiti   │
                    │   Update    │
                    └─────────────┘
```

## 🎯 Quick Reference Diagram

### For Your Terminal:
```
Search Flow:
============
User → API → Supervisor → Search → Results
              ↓            ↓
           Graphiti    Weaviate
              ↓            ↓
          Preferences  Products
              ↓            ↓
              └────┬───────┘
                   ↓
              Personalized
               Results

Learning Flow:
==============
User Action → BigQuery → Pattern Extract → Graphiti
                ↓                            ↑
            Analytics                        │
                ↓                            │
          Materialized ──────────────────────┘
             Views         (Daily Sync)
```

## 📊 Performance View

```
LATENCY BUDGET (300ms Total)
============================
│
├─ API Gateway        [████░░░░░░] 20ms
├─ Supervisor         [████░░░░░░] 20ms
├─ Memory Fetch       [████████░░] 40ms
├─ Product Search     [████████████████░░] 100ms
├─ Personalization    [████████░░] 40ms
├─ Response Compile   [████░░░░░░] 20ms
└─ Network/Buffer     [████████░░] 60ms
                      └─────────────────┘
                         Total: 300ms
```

## 🚦 Decision Points

### Real-time vs Analytics Path
```
                  Request
                     │
                     ▼
            ┌─────────────────┐
            │ Is it a search? │
            └────┬───────┬────┘
                YES      NO
                 │        │
                 ▼        ▼
            Real-time  Analytics
            (Graphiti) (BigQuery)
```

### Pattern Sync Decision
```
              Pattern Found
                    │
                    ▼
           ┌─────────────────┐
           │ Confidence > 0.8?│
           └────┬───────┬────┘
               YES      NO
                │        │
                ▼        ▼
           Sync to    Keep in
           Graphiti   BigQuery
```

## 🎮 Interactive Elements

### What Happens When...

**User searches "milk":**
1. API → Supervisor (20ms)
2. Parallel: Graphiti preferences + Weaviate search (100ms)
3. Merge results with personalization (40ms)
4. Return response (total: 200ms)
5. Async: Log to BigQuery

**Pattern extraction runs:**
1. Query BigQuery views (30s)
2. Extract high-confidence patterns (10s)
3. Batch update Graphiti (5s)
4. Invalidate caches (1s)
5. Agents see new patterns immediately

**User changes preference:**
1. Update Graphiti edge (10ms)
2. Invalidate user cache (5ms)
3. Log event to BigQuery (async)
4. Next search uses new preference

## 🔧 For Your Next Session

### Quick Commands:
```bash
# Check pattern sync status
gcloud scheduler jobs list --filter="name:pattern-sync"

# View recent extractions
bq query --use_legacy_sql=false '
SELECT pattern_type, COUNT(*) as count 
FROM leafloaf_analytics.pattern_extraction_log
WHERE DATE(extracted_at) = CURRENT_DATE()
GROUP BY pattern_type'

# Monitor Graphiti updates
gcloud spanner databases execute-sql leafloaf-graphiti \
  --sql="SELECT edge_type, COUNT(*) FROM graphiti_edges 
         WHERE last_updated > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
         GROUP BY edge_type"
```

### Key Questions for Brainstorming:
1. Should we sync ALL patterns or just stable ones?
2. How often should pattern extraction run?
3. What's our cache invalidation strategy?
4. How do we handle conflicting patterns?
5. Should users see/control their patterns?

### Architecture Options:
```
Option A: Full Sync
==================
BigQuery → ALL patterns → Graphiti
Pro: Simple, consistent
Con: Expensive, potentially stale

Option B: Selective Sync
=======================
BigQuery → High-confidence only → Graphiti
           Low-confidence → Cache only
Pro: Cost-effective, fresh
Con: Complex, two data sources

Option C: Lazy Loading
=====================
BigQuery → On-demand fetch → Temp cache
Pro: Always fresh, minimal storage
Con: Higher latency, complex
```

---

Ready for your brainstorming session! 🚀