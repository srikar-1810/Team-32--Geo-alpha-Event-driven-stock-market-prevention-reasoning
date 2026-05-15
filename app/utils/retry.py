from __future__ import annotations

import asyncio
from functools import wraps
from typing import Any, Callable, Optional, Type, Union

from app.logging_config import get_logger

logger = get_logger(__name__)


async def async_retry(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Any:
    last_exception = None
    delay = base_delay

    for attempt in range(max_retries + 1):
        try:
            return await func()
        except exceptions as e:
            last_exception = e
            if attempt < max_retries:
                jitter = delay * (0.5 + hash(str(e)) % 50 / 100.0)
                logger.warning(
                    "Retry %d/%d for %s failed: %s. Waiting %.2fs",
                    attempt + 1, max_retries, func.__name__, e, jitter,
                )
                await asyncio.sleep(jitter)
                delay = min(delay * backoff, max_delay)
            else:
                logger.error(
                    "All %d retries exhausted for %s",
                    max_retries, func.__name__,
                )

    raise last_exception


def retry_decorator(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: tuple = (Exception,),
):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async def call():
                return await func(*args, **kwargs)
            return await async_retry(
                call,
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                exceptions=exceptions,
            )
        return wrapper
    return decorator
