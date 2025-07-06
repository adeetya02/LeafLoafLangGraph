# LeafLoaf Documentation Map 🗺️

## Quick Navigation Guide

```
📚 LeafLoaf Documentation Structure
│
├── 🎯 START HERE
│   ├── CLAUDE.md ................... Main AI context & project status
│   ├── README.md ................... Project overview
│   └── WORKING_DOCUMENT.md ......... Current work in progress
│
├── 🎤 VOICE & DEEPGRAM
│   ├── DEEPGRAM_IMPLEMENTATION_PLAN.md ... Complete implementation plan
│   ├── DEEPGRAM_INTEGRATION.md .......... Integration details & findings
│   ├── VOICE_IMPLEMENTATION_STATUS.md .... Current voice status
│   ├── HOLISTIC_VOICE_ANALYTICS.md ...... Voice analytics design
│   └── tests/implementation/deepgram/ .... Active testing work
│
├── 🏗️ ARCHITECTURE
│   ├── docs/SYSTEM_ARCHITECTURE.md ....... System design
│   ├── docs/DATA_FLOW_ARCHITECTURE.md .... Data flow patterns
│   ├── VOICE_NATIVE_ARCHITECTURE_PLAN.md . Voice architecture
│   └── GRAPHITI_COMPLETE_ARCHITECTURE.md . Memory system design
│
├── 🧪 TESTING
│   ├── tests/README.md ................... Test structure guide
│   ├── docs/TDD_SUCCESS_REPORT.md ........ Test results (103/103!)
│   ├── run_tests.py ...................... Test runner
│   └── tests/implementation/ ............. Work in progress
│
├── 🚀 DEPLOYMENT
│   ├── DEPLOYMENT.md ..................... Main deployment guide
│   ├── GCP_DEPLOYMENT_SECRETS.md ......... GCP configuration
│   ├── DEPLOYMENT_STATUS.md .............. Current status
│   └── docs/CICD_SETUP_GUIDE.md .......... CI/CD setup
│
├── 📊 DATA & ML
│   ├── docs/BIGQUERY_SCHEMA.md ........... Data schema
│   ├── docs/ML_DATA_SCHEMA.md ............ ML pipeline schema
│   ├── docs/GRAPHITI_PERSONALIZATION.md .. Personalization features
│   └── docs/LEARNING_LOOP_IMPLEMENTATION.md Learning system
│
└── 📁 ARCHIVES
    └── docs/archive/2025-06-28/ .......... Historical documentation
```

## 🔥 Most Important Files

### For Understanding the System
1. **CLAUDE.md** - Complete context, current status, architecture decisions
2. **docs/SYSTEM_ARCHITECTURE.md** - Technical architecture details
3. **VOICE_NATIVE_IMPLEMENTATION_GUIDE.md** - Voice implementation

### For Current Development
1. **WORKING_DOCUMENT.md** - Active work tracking
2. **DEEPGRAM_IMPLEMENTATION_PLAN.md** - Deepgram integration
3. **tests/implementation/** - Current test implementations

### For Testing
1. **tests/README.md** - How to organize and run tests
2. **run_tests.py** - Test runner with coverage
3. **docs/TDD_SUCCESS_REPORT.md** - Successful TDD implementation

### For Production
1. **DEPLOYMENT.md** - Deployment procedures
2. **GCP_DEPLOYMENT_SECRETS.md** - Production secrets
3. **docs/PRODUCTION_SUMMARY.md** - Production system overview

## 📍 Current Focus Areas

### 🎤 Voice Streaming (Active)
- Working implementation: `tests/implementation/deepgram/test_deepgram_streaming.html`
- Documentation: `DEEPGRAM_INTEGRATION.md`
- Next: Holistic voice analytics from `HOLISTIC_VOICE_ANALYTICS.md`

### 🧠 Graphiti Memory (Complete)
- Architecture: `GRAPHITI_COMPLETE_ARCHITECTURE.md`
- Status: `SPANNER_GRAPHITI_STATUS.md`
- Features: All 10 personalization features migrated

### 🧪 Testing Structure (New)
- Structure: `tests/README.md`
- Implementation folder for WIP: `tests/implementation/`
- Runner: `python run_tests.py`

## 🎯 Navigation Tips

1. **New to project?** Start with `CLAUDE.md`
2. **Working on voice?** Check `DEEPGRAM_*` files
3. **Need architecture?** Go to `docs/SYSTEM_ARCHITECTURE.md`
4. **Testing something?** Use `tests/implementation/`
5. **Deploying?** Follow `DEPLOYMENT.md`

## 📝 Documentation Updates

When updating documentation:
- **Active work**: Update `WORKING_DOCUMENT.md`
- **Feature complete**: Create/update in `docs/`
- **Context changes**: Update `CLAUDE.md`
- **Old docs**: Archive to `docs/archive/YYYY-MM-DD/`