"""
Metrics utility for production monitoring

Provides lightweight metrics tracking without external dependencies.
In production, these would integrate with your monitoring system (Datadog, Prometheus, etc.)
"""

import time
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()


def track_timing(metric_name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None):
    """
    Track timing metrics.
    
    In production, this would send to your metrics backend.
    For now, just logs for debugging.
    """
    log_data = {
        "metric": metric_name,
        "duration_ms": round(duration_ms, 2),
        "metric_type": "timing"
    }
    
    if tags:
        log_data["tags"] = tags
        
    logger.debug("metric.timing", **log_data)


def track_counter(metric_name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
    """
    Track counter metrics.
    
    In production, this would send to your metrics backend.
    For now, just logs for debugging.
    """
    log_data = {
        "metric": metric_name,
        "value": value,
        "metric_type": "counter"
    }
    
    if tags:
        log_data["tags"] = tags
        
    logger.debug("metric.counter", **log_data)


def track_gauge(metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
    """
    Track gauge metrics.
    
    In production, this would send to your metrics backend.
    For now, just logs for debugging.
    """
    log_data = {
        "metric": metric_name,
        "value": value,
        "metric_type": "gauge"
    }
    
    if tags:
        log_data["tags"] = tags
        
    logger.debug("metric.gauge", **log_data)


class Timer:
    """Context manager for timing operations"""
    
    def __init__(self, metric_name: str, tags: Optional[Dict[str, str]] = None):
        self.metric_name = metric_name
        self.tags = tags
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration_ms = (time.time() - self.start_time) * 1000
            track_timing(self.metric_name, duration_ms, self.tags)