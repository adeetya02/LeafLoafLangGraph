"""
Centralized configuration for all limits and constants
Production values should be loaded from environment variables
"""
import os
from datetime import datetime

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

# Feature Flags
FAST_MODE = os.getenv("FAST_MODE", "true" if not IS_PRODUCTION else "false").lower() == "true"
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"

# API Rate Limits
API_RATE_LIMIT_PER_MINUTE = int(os.getenv("API_RATE_LIMIT_PER_MINUTE", "100"))
API_RATE_LIMIT_PER_HOUR = int(os.getenv("API_RATE_LIMIT_PER_HOUR", "1000"))

# Weaviate Limits (expires 2025-06-28)
WEAVIATE_EXPIRY_DATE = datetime(2025, 6, 28)
WEAVIATE_MAX_SEARCHES_PER_MINUTE = int(os.getenv("WEAVIATE_MAX_SEARCHES_PER_MINUTE", "30"))
WEAVIATE_MAX_RESULTS_PER_SEARCH = int(os.getenv("WEAVIATE_MAX_RESULTS_PER_SEARCH", "10"))
WEAVIATE_RETRIEVAL_LIMIT = int(os.getenv("WEAVIATE_RETRIEVAL_LIMIT", "50"))  # How many to retrieve before filtering
WEAVIATE_MAX_BATCH_SIZE = int(os.getenv("WEAVIATE_MAX_BATCH_SIZE", "100"))
WEAVIATE_TIMEOUT_SECONDS = int(os.getenv("WEAVIATE_TIMEOUT_SECONDS", "10"))
WEAVIATE_MAX_RETRIES = int(os.getenv("WEAVIATE_MAX_RETRIES", "2"))

# LLM Limits
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "200"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "10.0"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))

# Search Configuration
SEARCH_DEFAULT_LIMIT = int(os.getenv("SEARCH_DEFAULT_LIMIT", "20"))  # Changed from 10 to 20 for better personalization visibility
SEARCH_MAX_LIMIT = int(os.getenv("SEARCH_MAX_LIMIT", "50"))
SEARCH_TIMEOUT_MS = int(os.getenv("SEARCH_TIMEOUT_MS", "5000"))
SEARCH_DEFAULT_ALPHA = float(os.getenv("SEARCH_DEFAULT_ALPHA", "0.75"))  # Favor vector search for better semantic understanding

# Supervisor Limits
SUPERVISOR_TIMEOUT_MS = int(os.getenv("SUPERVISOR_TIMEOUT_MS", "2000"))
SUPERVISOR_MAX_REASONING_STEPS = int(os.getenv("SUPERVISOR_MAX_REASONING_STEPS", "10"))

# Order Agent Limits
ORDER_MAX_ITEMS_PER_CART = int(os.getenv("ORDER_MAX_ITEMS_PER_CART", "50"))
ORDER_MAX_QUANTITY_PER_ITEM = int(os.getenv("ORDER_MAX_QUANTITY_PER_ITEM", "99"))
ORDER_SESSION_TIMEOUT_MINUTES = int(os.getenv("ORDER_SESSION_TIMEOUT_MINUTES", "30"))

# Memory/Cache Limits
MEMORY_MAX_CONVERSATION_LENGTH = int(os.getenv("MEMORY_MAX_CONVERSATION_LENGTH", "50"))
MEMORY_CACHE_TTL_SECONDS = int(os.getenv("MEMORY_CACHE_TTL_SECONDS", "3600"))
MEMORY_MAX_CACHE_SIZE_MB = int(os.getenv("MEMORY_MAX_CACHE_SIZE_MB", "100"))

# Personalization Limits
PERSONALIZATION_CACHE_TTL = int(os.getenv("PERSONALIZATION_CACHE_TTL", "3600"))
PERSONALIZATION_MAX_SIGNALS_PER_USER = int(os.getenv("PERSONALIZATION_MAX_SIGNALS_PER_USER", "1000"))
PERSONALIZATION_DECAY_FACTOR = float(os.getenv("PERSONALIZATION_DECAY_FACTOR", "0.95"))
PERSONALIZATION_UPDATE_TIMEOUT_MS = int(os.getenv("PERSONALIZATION_UPDATE_TIMEOUT_MS", "10"))
PERSONALIZATION_APPLY_TIMEOUT_MS = int(os.getenv("PERSONALIZATION_APPLY_TIMEOUT_MS", "50"))

# Personalization Signal Weights
PERSONALIZATION_WEIGHTS = {
    "signal_weights": {
        "purchase": 1.0,
        "add_to_cart": 0.5,
        "click": 0.2,
        "view_details": 0.3,
        "remove_from_cart": -0.4,
        "scroll_past": -0.05
    },
    "category_weight": 0.4,
    "brand_weight": 0.3,
    "attribute_weight": 0.3
}
MEMORY_MAX_PREFERENCES = int(os.getenv("MEMORY_MAX_PREFERENCES", "20"))
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))
CACHE_MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", "100"))

# Redis Cache TTLs
REDIS_SEARCH_TTL = int(os.getenv("REDIS_SEARCH_TTL", "3600"))  # 1 hour for search results
REDIS_ALPHA_TTL = int(os.getenv("REDIS_ALPHA_TTL", "86400"))  # 24 hours for alpha values
REDIS_PRODUCT_TTL = int(os.getenv("REDIS_PRODUCT_TTL", "21600"))  # 6 hours for product details
REDIS_SESSION_TTL = int(os.getenv("REDIS_SESSION_TTL", "7200"))  # 2 hours for session context
REDIS_POPULAR_TTL = int(os.getenv("REDIS_POPULAR_TTL", "604800"))  # 7 days for analytics

# Voice/11Labs Limits
VOICE_MAX_DURATION_SECONDS = int(os.getenv("VOICE_MAX_DURATION_SECONDS", "60"))
VOICE_MAX_TRANSCRIPT_LENGTH = int(os.getenv("VOICE_MAX_TRANSCRIPT_LENGTH", "1000"))

# LLM-First Mode - Patterns are only last line of defense!
# All intent recognition and alpha calculation is done by LLM first
# Patterns only used when LLM fails or times out

# Minimal patterns for emergency fallback only
BRAND_PATTERNS = ["oatly", "horizon", "silk", "organic valley"]  # Just top brands

PRODUCT_KEYWORDS = ["milk", "bread", "eggs", "cheese"]  # Just essentials

DIETARY_ATTRIBUTES = ["organic", "gluten-free", "vegan"]  # Just common ones

# Minimal regex patterns - only for emergency fallback
import re
ORDER_INTENT_PATTERNS = {
    "add_to_order": re.compile(r'\b(add|put)\b.*\b(cart|order)\b', re.I),
    "remove_from_order": re.compile(r'\b(remove|delete)\b.*\b(cart|order)\b', re.I),
}
SEARCH_TYPE_PATTERNS = {}

# Alpha calculation is LLM-driven, patterns only for ultimate fallback
ALPHA_RULES = {
    "default": SEARCH_DEFAULT_ALPHA  # Uses the configurable default
}

# Graphiti Search Integration Configuration
GRAPHITI_SEARCH_MODE = os.getenv("GRAPHITI_SEARCH_MODE", "supplement")  # enhance | supplement | both | off
GRAPHITI_ENHANCE_STRENGTH = float(os.getenv("GRAPHITI_ENHANCE_STRENGTH", "0.5"))  # 0.0-1.0
GRAPHITI_MAX_RECOMMENDATIONS = int(os.getenv("GRAPHITI_MAX_RECOMMENDATIONS", "5"))
GRAPHITI_RECOMMENDATION_SECTIONS = ["recommended_for_you", "frequently_bought", "based_on_preferences"]

# Personalization control options
PERSONALIZATION_CONTROL = {
    "explicit_disable_param": "show_all",  # API param: ?show_all=true
    "preserve_original_query": True,  # Always run base query too
    "toggle_response_format": "dual",  # dual | single
    "ui_controls": {
        "show_toggle": True,  # "Show all milk" vs "Show my usual"
        "default_state": "personalized",
        "toggle_labels": {
            "personalized": "My Usual",
            "all": "Show All Options"
        }
    }
}