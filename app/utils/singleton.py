from __future__ import annotations

from typing import Any, Dict, Optional

import redis.asyncio as aioredis

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


class SingletonMeta(type):
    _instances: Dict[Any, Any] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class RedisClient(metaclass=SingletonMeta):
    """Singleton async Redis client."""

    def __init__(self) -> None:
        self._pool: Optional[aioredis.Redis] = None

    async def _get_client(self) -> aioredis.Redis:
        if self._pool is None:
            self._pool = aioredis.from_url(
                settings.REDIS_URL,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                decode_responses=True,
            )
        return self._pool

    async def ping(self) -> bool:
        try:
            client = await self._get_client()
            return await client.ping()
        except Exception:
            return False

    async def set(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        client = await self._get_client()
        return await client.set(key, value, ex=expire)

    async def get(self, key: str) -> Optional[str]:
        client = await self._get_client()
        return await client.get(key)

    async def delete(self, key: str) -> bool:
        client = await self._get_client()
        return bool(await client.delete(key))

    async def exists(self, key: str) -> bool:
        client = await self._get_client()
        return await client.exists(key) > 0

    async def publish(self, channel: str, message: str) -> int:
        client = await self._get_client()
        return await client.publish(channel, message)

    async def hset(self, name: str, key: str, value: Any) -> int:
        client = await self._get_client()
        return await client.hset(name, key, value)

    async def hget(self, name: str, key: str) -> Optional[str]:
        client = await self._get_client()
        return await client.hget(name, key)

    async def hgetall(self, name: str) -> Dict[str, str]:
        client = await self._get_client()
        return await client.hgetall(name)

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def __aenter__(self) -> RedisClient:
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()


redis_client = RedisClient()
