from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set

from app.logging_config import get_logger
from app.utils.singleton import redis_client

logger = get_logger(__name__)


class IngestionCache:
    """Redis-backed ingestion cache for deduplication and TTL-based expiry."""

    DEDUP_PREFIX = "ingest:dedup:"
    CONTENT_PREFIX = "ingest:content:"
    STATS_PREFIX = "ingest:stats:"
    LAST_RUN_PREFIX = "ingest:last_run:"

    def __init__(self, default_ttl_seconds: int = 86400) -> None:
        self.default_ttl = default_ttl_seconds

    @staticmethod
    def _content_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _url_hash(url: str) -> str:
        return hashlib.md5(url.encode("utf-8")).hexdigest()

    async def is_duplicate_url(self, url: str, source: str = "gdelt") -> bool:
        key = f"{self.DEDUP_PREFIX}{source}:url:{self._url_hash(url)}"
        return await redis_client.exists(key)

    async def mark_url_seen(self, url: str, source: str = "gdelt", ttl: Optional[int] = None) -> None:
        key = f"{self.DEDUP_PREFIX}{source}:url:{self._url_hash(url)}"
        await redis_client.set(key, "1", expire=ttl or self.default_ttl)

    async def is_duplicate_content(self, text: str, source: str = "gdelt") -> bool:
        key = f"{self.DEDUP_PREFIX}{source}:content:{self._content_hash(text)}"
        return await redis_client.exists(key)

    async def mark_content_seen(
        self,
        text: str,
        source: str = "gdelt",
        metadata: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
    ) -> None:
        key = f"{self.DEDUP_PREFIX}{source}:content:{self._content_hash(text)}"
        await redis_client.set(key, json.dumps(metadata or {}), expire=ttl or self.default_ttl)

    async def is_duplicate_id(self, item_id: str, source: str = "reddit") -> bool:
        key = f"{self.DEDUP_PREFIX}{source}:id:{item_id}"
        return await redis_client.exists(key)

    async def mark_id_seen(self, item_id: str, source: str = "reddit", ttl: Optional[int] = None) -> None:
        key = f"{self.DEDUP_PREFIX}{source}:id:{item_id}"
        await redis_client.set(key, "1", expire=ttl or self.default_ttl)

    async def bulk_check_urls(self, urls: List[str], source: str = "gdelt") -> Dict[str, bool]:
        results = {}
        for url in urls:
            results[url] = await self.is_duplicate_url(url, source)
        return results

    async def cache_content(
        self,
        key: str,
        data: Any,
        source: str = "default",
        ttl: Optional[int] = None,
    ) -> None:
        full_key = f"{self.CONTENT_PREFIX}{source}:{key}"
        await redis_client.set(full_key, json.dumps(data, default=str), expire=ttl or 3600)

    async def get_cached_content(self, key: str, source: str = "default") -> Optional[Any]:
        full_key = f"{self.CONTENT_PREFIX}{source}:{key}"
        raw = await redis_client.get(full_key)
        if raw:
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return raw
        return None

    async def update_last_run(self, source: str, status: str = "success") -> None:
        key = f"{self.LAST_RUN_PREFIX}{source}"
        data = {
            "last_run": datetime.now(timezone.utc).isoformat(),
            "status": status,
        }
        await redis_client.set(key, json.dumps(data))

    async def get_last_run(self, source: str) -> Optional[Dict[str, Any]]:
        key = f"{self.LAST_RUN_PREFIX}{source}"
        raw = await redis_client.get(key)
        if raw:
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return {"last_run": raw}
        return None

    async def increment_stat(self, source: str, stat: str, amount: int = 1) -> None:
        key = f"{self.STATS_PREFIX}{source}"
        await redis_client.hset(key, stat, amount)
        existing = await redis_client.hget(key, stat)
        if existing:
            await redis_client.hset(key, stat, int(existing) + amount)
        else:
            await redis_client.hset(key, stat, amount)

    async def get_stats(self, source: str) -> Dict[str, str]:
        key = f"{self.STATS_PREFIX}{source}"
        return await redis_client.hgetall(key)

    async def clear_source_cache(self, source: str) -> None:
        logger.warning("Clearing ingestion cache for source: %s", source)
        for prefix in (self.DEDUP_PREFIX, self.CONTENT_PREFIX, self.STATS_PREFIX, self.LAST_RUN_PREFIX):
            pattern = f"{prefix}{source}:*"
            keys = await redis_client._get_client().keys(pattern)
            if keys:
                for key in keys:
                    await redis_client.delete(key)

    async def get_cache_size(self, source: str) -> int:
        count = 0
        for prefix in (self.DEDUP_PREFIX, self.CONTENT_PREFIX):
            pattern = f"{prefix}{source}:*"
            keys = await redis_client._get_client().keys(pattern)
            count += len(keys or [])
        return count


ingestion_cache = IngestionCache()
