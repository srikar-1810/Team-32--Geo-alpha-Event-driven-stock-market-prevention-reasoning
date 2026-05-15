from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from app.logging_config import get_logger

logger = get_logger(__name__)

try:
    from prometheus_client import Counter, Gauge, Histogram, generate_latest

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


@dataclass
class MetricRegistry:
    """Central registry for application metrics."""

    counters: Dict[str, Any] = field(default_factory=dict)
    histograms: Dict[str, Any] = field(default_factory=dict)
    gauges: Dict[str, Any] = field(default_factory=dict)

    def _get_or_create(self, registry: Dict, name: str, description: str, creator: Callable) -> Any:
        if name not in registry:
            registry[name] = creator(name, description)
        return registry[name]

    def increment_counter(self, name: str, description: str = "", value: int = 1) -> None:
        if PROMETHEUS_AVAILABLE:
            counter = self._get_or_create(self.counters, name, description, Counter)
            counter.inc(value)
        logger.debug("Counter %s += %d", name, value)

    def observe_histogram(self, name: str, description: str, value: float) -> None:
        if PROMETHEUS_AVAILABLE:
            histogram = self._get_or_create(self.histograms, name, description, Histogram)
            histogram.observe(value)
        logger.debug("Histogram %s = %.3f", name, value)

    def set_gauge(self, name: str, description: str, value: float) -> None:
        if PROMETHEUS_AVAILABLE:
            gauge = self._get_or_create(self.gauges, name, description, Gauge)
            gauge.set(value)
        logger.debug("Gauge %s = %.3f", name, value)


registry = MetricRegistry()


def track_execution_time(metric_name: str, description: str = ""):
    """Decorator to track function execution time as a histogram metric."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                elapsed = time.perf_counter() - start
                registry.observe_histogram(metric_name, description, elapsed)

        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed = time.perf_counter() - start
                registry.observe_histogram(metric_name, description, elapsed)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


@contextmanager
def timed_context(metric_name: str):
    """Context manager to measure execution time of a block."""
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        registry.observe_histogram(metric_name, "", elapsed)


def metrics_exposition() -> Optional[bytes]:
    if PROMETHEUS_AVAILABLE:
        return generate_latest()
    return None
