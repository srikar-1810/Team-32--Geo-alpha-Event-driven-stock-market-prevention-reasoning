from __future__ import annotations

import json
import os
from collections import OrderedDict
from hashlib import sha256
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


class EmbeddingCache:
    """LRU cache for computed embeddings with optional file persistence."""

    def __init__(
        self,
        capacity: int = 10000,
        persist_path: Optional[str] = None,
    ) -> None:
        self.capacity = capacity
        self.persist_path = Path(persist_path or settings.CHROMA_EMBEDDING_CACHE_PATH)
        self._cache: OrderedDict[str, List[float]] = OrderedDict()
        self._hit_count: int = 0
        self._miss_count: int = 0
        self._loaded: bool = False

    def _make_key(self, text: str) -> str:
        return sha256(text.encode("utf-8")).hexdigest()

    def get(self, text: str) -> Optional[List[float]]:
        key = self._make_key(text)
        if key in self._cache:
            self._cache.move_to_end(key)
            self._hit_count += 1
            return self._cache[key]
        self._miss_count += 1
        return None

    def get_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        return [self.get(t) for t in texts]

    def put(self, text: str, embedding: List[float]) -> None:
        key = self._make_key(text)
        self._cache[key] = embedding
        self._cache.move_to_end(key)
        if len(self._cache) > self.capacity:
            self._cache.popitem(last=False)

    def put_batch(self, texts: List[str], embeddings: List[List[float]]) -> None:
        for t, e in zip(texts, embeddings):
            self.put(t, e)

    def has(self, text: str) -> bool:
        return self._make_key(text) in self._cache

    def size(self) -> int:
        return len(self._cache)

    def stats(self) -> Dict[str, int]:
        total = self._hit_count + self._miss_count
        return {
            "size": len(self._cache),
            "capacity": self.capacity,
            "hit_count": self._hit_count,
            "miss_count": self._miss_count,
            "hit_rate": round(self._hit_count / total, 4) if total > 0 else 0.0,
        }

    async def load_from_disk(self) -> None:
        if self._loaded:
            return
        try:
            if self.persist_path.exists():
                data = json.loads(self.persist_path.read_text())
                self._cache.update(data)
                logger.info(
                    "Loaded %d cached embeddings from %s", len(data), self.persist_path,
                )
        except Exception as e:
            logger.warning("Failed to load embedding cache: %s", e)
        self._loaded = True

    async def save_to_disk(self) -> None:
        try:
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            data = dict(self._cache)
            self.persist_path.write_text(json.dumps(data))
            logger.debug("Saved %d cached embeddings to %s", len(data), self.persist_path)
        except Exception as e:
            logger.warning("Failed to save embedding cache: %s", e)

    def clear(self) -> None:
        self._cache.clear()
        self._hit_count = 0
        self._miss_count = 0
        logger.info("Embedding cache cleared")

    def remove_oldest(self, n: int) -> int:
        removed = 0
        while len(self._cache) > self.capacity - n and self._cache:
            self._cache.popitem(last=False)
            removed += 1
        return removed
