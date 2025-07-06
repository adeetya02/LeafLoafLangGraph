"""
Pytest configuration and shared fixtures
"""
import pytest
import asyncio
import os
from unittest.mock import Mock, AsyncMock


# Configure async tests
pytest_plugins = ['pytest_asyncio']


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_env(monkeypatch):
    """Mock environment variables"""
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test_deepgram_key")
    monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key")
    monkeypatch.setenv("WEAVIATE_URL", "http://test-weaviate:8080")
    monkeypatch.setenv("WEAVIATE_API_KEY", "test_weaviate_key")
    monkeypatch.setenv("ENVIRONMENT", "test")


@pytest.fixture
def mock_llm():
    """Mock LLM for testing"""
    llm = Mock()
    llm.ainvoke = AsyncMock(return_value={
        "content": "Test response",
        "usage": {"total_tokens": 100}
    })
    return llm


@pytest.fixture
def sample_voice_metadata():
    """Sample voice metadata for testing"""
    return {
        "pace": "normal",
        "emotion": "neutral",
        "volume": "normal",
        "urgency": "medium",
        "background_noise": "quiet",
        "duration": 2.5,
        "hesitations": 0,
        "confidence": 0.9
    }


@pytest.fixture
def sample_search_state():
    """Sample search state for testing"""
    return {
        "query": "I need milk",
        "session_id": "test-session-123",
        "user_id": "test-user",
        "request_id": "req-123",
        "timestamp": "2025-07-04T10:00:00Z",
        "conversation_history": [],
        "voice_metadata": None,
        "trace_id": "trace-123"
    }


@pytest.fixture
def sample_products():
    """Sample product data for testing"""
    return [
        {
            "product_id": "milk-001",
            "name": "Organic Valley Whole Milk",
            "price": 4.99,
            "category": "Dairy",
            "brand": "Organic Valley",
            "unit": "gallon",
            "in_stock": True
        },
        {
            "product_id": "milk-002", 
            "name": "Horizon Organic 2% Milk",
            "price": 4.79,
            "category": "Dairy",
            "brand": "Horizon",
            "unit": "half gallon",
            "in_stock": True
        }
    ]


@pytest.fixture
def mock_weaviate_client():
    """Mock Weaviate client"""
    client = Mock()
    client.is_ready = Mock(return_value=True)
    client.query = Mock()
    return client


@pytest.fixture
def mock_graphiti():
    """Mock Graphiti memory"""
    graphiti = Mock()
    graphiti.get_memory_context = AsyncMock(return_value={
        "preferences": ["organic", "dairy-free"],
        "usual_quantities": {"milk": 2},
        "reorder_patterns": []
    })
    graphiti.add_episode = AsyncMock()
    return graphiti