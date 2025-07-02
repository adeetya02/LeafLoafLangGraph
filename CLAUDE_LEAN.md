# LeafLoaf LangGraph - AI Assistant Context

## 📚 Primary Reference
**See `KNOWLEDGE_BASE.md` for all technical details** - single source of truth

## Quick Context
- **What**: Production-grade grocery shopping with real-time personalization
- **Architecture**: Multi-agent (Supervisor → Search → Order → Response)
- **Status**: Demo ready, personalization working, <350ms responses

## Current Focus
- Real-time personalization demo working ✅
- Category filtering implemented ✅
- Interactive UI complete ✅
- BigQuery/Graphiti ready but not connected (for demo)

## Key Commands
```bash
# Start server
PORT=8000 python3 run.py

# Open demo
open demo_realtime_personalization.html
```

## Important Files
- `KNOWLEDGE_BASE.md` - Everything you need to know
- `src/personalization/instant_personalizer.py` - Real-time magic
- `src/agents/` - Agent implementations
- `demo_realtime_personalization.html` - Interactive demo

## Design Principles
1. Agents make all decisions (API is just a messenger)
2. Performance <350ms is non-negotiable
3. Privacy first - user owns their data
4. Graceful degradation - each tier fails independently
5. Test-driven development

## Token Efficiency
- Read from KNOWLEDGE_BASE.md for details
- This file is just quick context
- Old docs archived in docs/archive/