# 🚀 LeafLoaf Production Demo - Quick Start Guide

## Tonight's Demo Setup (< 2 minutes)

### 1. Start the Demo
```bash
python3 run_production_demo.py
```

This will:
- ✅ Start the enhanced API with full logging
- ✅ Open the interactive UI in your browser
- ✅ Begin real-time performance monitoring
- ✅ Create demo scenarios file

### 2. Demo Features

#### 🎯 What's Included:
- **Interactive UI** with real-time logging
- **10 Personalization Features** all active
- **Live Performance Metrics** (latency tracking)
- **Complete Request/Response Logging**
- **Multiple User Personas** for testing
- **Visual Performance Charts**

#### 📊 Key Metrics Tracked:
- Every API call with timestamp
- Request/Response payloads
- Latency for each operation
- Component-level timing
- Personalization scoring
- Cache hit rates

### 3. Demo Scenarios

The system creates `demo_scenarios.json` with 8 key scenarios:

1. **Basic Search** - Baseline performance
2. **Dietary Intelligence** - Auto-filtering
3. **My Usual** - Personalized frequent items
4. **Reorder Intelligence** - Predictive restocking
5. **Budget Shopping** - Price-aware results
6. **Family Pack** - Quantity memory
7. **Cultural Intelligence** - "sambar ingredients"
8. **Complementary Products** - Smart pairings

### 4. User Personas

Switch between users in the UI dropdown:
- **Demo User** - Default profile
- **Health Conscious** - Gluten-free, organic preferences
- **Budget Shopper** - Value-focused, bulk buying
- **Family Shopper** - Large quantities, family packs

### 5. Live Monitoring

#### In the UI:
- **API Logs Panel** - Every request/response with latency
- **Performance Metrics** - Real-time charts
- **Cart Tracking** - User behavior logging

#### In the Terminal:
- Live performance dashboard (updates every 5s)
- Average latencies
- Feature status
- Recent requests

### 6. Log Files

All activity is logged to:
- `demo_api_detailed.log` - Complete API logs
- `demo_session_*.json` - Session summary
- `demo_performance_report_*.json` - Performance analysis

## 🎮 Demo Flow for Tonight

1. **Start with Basic Search**
   - Search "milk" to show baseline
   - Point out <300ms latency

2. **Show Personalization**
   - Switch to "Health Conscious User"
   - Search "bread" - see gluten-free filtering
   - Show logs proving personalization

3. **Demonstrate My Usual**
   - Click "My Usual" button
   - Show personalized frequent items
   - Highlight Graphiti learning

4. **Reorder Intelligence**
   - Click "Reorders Due"
   - Show predictive restocking
   - Explain purchase cycle detection

5. **Budget Awareness**
   - Switch to "Budget Shopper"
   - Search "pasta"
   - Show value optimization

6. **Cultural Intelligence**
   - Search "sambar ingredients"
   - Demonstrate understanding
   - No hardcoded rules!

7. **Review Performance**
   - Show average latency <300ms
   - 103/103 tests passing
   - Pure Graphiti Learning

## 🛠️ Troubleshooting

If API doesn't start:
```bash
# Check if port 8000 is in use
lsof -i :8000

# Kill existing process
kill -9 <PID>

# Restart demo
python3 run_production_demo.py
```

If browser doesn't open:
- Manually open: `leafloaf_interactive_demo.html`
- Ensure API is running at `http://localhost:8000`

## 📝 Key Talking Points

1. **Pure Graphiti Learning**
   - Zero hardcoded rules
   - Self-improving system
   - Learns from every interaction

2. **Production Ready**
   - 103/103 tests passing
   - <300ms response time
   - BigQuery streaming active

3. **10 Personalization Features**
   - All implemented with TDD
   - User-controlled privacy
   - Real-time adaptation

4. **Architecture**
   - Multi-agent system
   - Spanner-backed GraphRAG
   - Fire-and-forget analytics

## 🎉 Success Metrics

- ✅ All features working
- ✅ Latency under target
- ✅ Complete logging
- ✅ Visual demonstration
- ✅ Production code running

---

**Ready for tonight's demo! 🚀**