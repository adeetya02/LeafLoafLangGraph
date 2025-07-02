"""
ML Module
Async recommendation engine and ML features
"""

from src.ml.recommendation_engine import (
    recommendation_engine,
    AsyncRecommendationEngine
)

__all__ = [
    "recommendation_engine",
    "AsyncRecommendationEngine"
]