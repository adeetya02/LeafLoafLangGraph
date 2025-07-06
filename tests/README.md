# LeafLoaf LangGraph Test Suite

## Overview
This directory contains all tests for the LeafLoaf LangGraph system. Tests are organized by component and should be run before integrating any new features into the main `src` folder.

## Directory Structure

```
tests/
├── agents/         # Agent-specific tests (supervisor, search, order, etc.)
├── deepgram/       # Deepgram integration tests (STT, TTS, streaming)
├── voice/          # Voice processing and metadata tests
├── memory/         # Memory system tests (Graphiti, session, etc.)
├── integration/    # End-to-end integration tests
├── tools/          # Tool tests (search tools, order tools)
├── api/            # API endpoint tests
└── implementation/ # Working implementations before src integration
```

## Testing Strategy

### 1. Component Tests
Test individual components in isolation:
- Agent behavior
- Tool functionality
- Memory operations
- Voice processing

### 2. Integration Tests
Test how components work together:
- Voice → Supervisor → Search flow
- Memory → Personalization
- End-to-end scenarios

### 3. Implementation Folder
When developing new features:
1. Create working implementation in `tests/implementation/`
2. Test thoroughly
3. Once verified, move to appropriate location in `src/`

## Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific component tests
python -m pytest tests/agents/
python -m pytest tests/deepgram/

# Run with coverage
python -m pytest tests/ --cov=src/

# Run specific test file
python -m pytest tests/deepgram/test_streaming.py
```

## Test Guidelines

1. **Isolation**: Each test should be independent
2. **Mocking**: Mock external services (Deepgram, LLMs, etc.)
3. **Fixtures**: Use pytest fixtures for common setup
4. **Async Tests**: Use `pytest-asyncio` for async functions
5. **Performance**: Include performance benchmarks for critical paths

## Current Test Coverage

- [x] Personalization features (103/103 tests passing)
- [x] Voice scenarios
- [ ] Deepgram streaming
- [ ] Holistic voice analytics
- [ ] Multi-agent flows
- [ ] Memory systems

## Adding New Tests

When adding a new feature:
1. Create test file in appropriate directory
2. Write tests for happy path and edge cases
3. Include performance tests if applicable
4. Document any special setup required
5. Run tests locally before PR

## Test Data

Test data and fixtures should be placed in `tests/fixtures/`:
- Audio files for voice tests
- Sample product data
- Mock API responses
- Test user profiles