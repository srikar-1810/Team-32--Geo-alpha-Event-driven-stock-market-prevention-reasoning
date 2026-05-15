from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import Callable, Optional


class RateLimiter:
    """Token-bucket rate limiter for API calls."""

    def __init__(
        self,
        max_calls: int,
        period: float = 60.0,
        name: str = "default",
    ) -> None:
        self.max_calls = max_calls
        self.period = period
        self.name = name
        self._calls: deque = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> float:
        async with self._lock:
            now = time.monotonic()
            while self._calls and now - self._calls[0] > self.period:
                self._calls.popleft()

            if len(self._calls) >= self.max_calls:
                wait_time = self._calls[0] + self.period - now
                await asyncio.sleep(wait_time)
                now = time.monotonic()

            self._calls.append(now)
            return 0.0

    async def __aenter__(self) -> RateLimiter:
        await self.acquire()
        return self

    async def __aexit__(self, *args) -> None:
        pass


class RateLimitedClient:
    """Wrapper that applies rate limiting to async client methods."""

    def __init__(self, client: any, limiter: RateLimiter) -> None:
        self._client = client
        self._limiter = limiter

    def __getattr__(self, name: str) -> Callable:
        attr = getattr(self._client, name)

        async def rate_limited_method(*args, **kwargs):
            async with self._limiter:
                if asyncio.iscoroutinefunction(attr):
                    return await attr(*args, **kwargs)
                return attr(*args, **kwargs)

        return rate_limited_method
