"""
Data Capture Module
Flexible data collection for ML and analytics
"""

from src.data_capture.capture_strategy import (
    data_capture,
    HybridDataCapture,
    RedisBackend,
    CloudStorageBackend,
    BigQueryBackend
)

__all__ = [
    "data_capture",
    "HybridDataCapture",
    "RedisBackend",
    "CloudStorageBackend",
    "BigQueryBackend"
]