from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.config import settings
from app.logging_config import get_logger
from app.services.chroma.client import ChromaClient

logger = get_logger(__name__)


class CollectionManager:
    """Manages ChromaDB collections for different data domains."""

    def __init__(self, chroma_client: ChromaClient) -> None:
        self.client = chroma_client
        self.collections = {
            "events": settings.CHROMA_COLLECTION_EVENTS,
            "sentiment": settings.CHROMA_COLLECTION_SENTIMENT,
            "markets": settings.CHROMA_COLLECTION_MARKETS,
            "reports": settings.CHROMA_COLLECTION_REPORTS,
            "historical": settings.CHROMA_COLLECTION_HISTORICAL,
        }

    async def initialize(self) -> None:
        for name, collection_name in self.collections.items():
            try:
                await self.client.get_or_create_collection(
                    collection_name,
                    metadata={"domain": name, "description": f"GeoMarketGPT {name} collection"},
                )
                logger.info("Ensured collection: %s (%s)", collection_name, name)
            except Exception as e:
                logger.error("Failed to initialize collection %s: %s", collection_name, e)

    async def store_event(self, event_id: str, text: str, metadata: dict) -> bool:
        return await self.client.add_documents(
            collection_name=self.collections["events"],
            ids=[event_id],
            documents=[text],
            metadatas=[metadata],
        )

    async def store_sentiment(self, post_id: str, text: str, metadata: dict) -> bool:
        return await self.client.add_documents(
            collection_name=self.collections["sentiment"],
            ids=[post_id],
            documents=[text],
            metadatas=[metadata],
        )

    async def store_market_data(self, data_id: str, summary: str, metadata: dict) -> bool:
        return await self.client.add_documents(
            collection_name=self.collections["markets"],
            ids=[data_id],
            documents=[summary],
            metadatas=[metadata],
        )

    async def store_report(self, report_id: str, content: str, metadata: dict) -> bool:
        return await self.client.add_documents(
            collection_name=self.collections["reports"],
            ids=[report_id],
            documents=[content],
            metadatas=[metadata],
        )

    async def search_events(
        self,
        query: str,
        n_results: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return await self.client.query(
            collection_name=self.collections["events"],
            query_texts=[query],
            n_results=n_results,
            where=filters,
        )

    async def search_sentiment(
        self,
        query: str,
        n_results: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return await self.client.query(
            collection_name=self.collections["sentiment"],
            query_texts=[query],
            n_results=n_results,
            where=filters,
        )

    async def get_collection_stats(self) -> Dict[str, int]:
        stats = {}
        for name, collection_name in self.collections.items():
            try:
                stats[name] = await self.client.count(collection_name)
            except Exception:
                stats[name] = 0
        return stats
