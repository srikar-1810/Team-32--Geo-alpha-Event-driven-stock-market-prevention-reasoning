from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.config import settings
from app.logging_config import get_logger
from app.services.gdelt.ingestor import GDELTIngestor
from app.services.ingestion.cache import ingestion_cache
from app.services.ingestion.normalizer import IngestionNormalizer
from app.services.ingestion.scheduler import IngestionScheduler
from app.services.reddit.ingestor import RedditIngestor
from app.services.tiingo.ingestor import MarketDataIngestor

logger = get_logger(__name__)


class IngestionManager:
    """Central orchestrator for all data ingestion sources with scheduling, caching, and storage."""

    def __init__(self) -> None:
        self.scheduler = IngestionScheduler()
        self.normalizer = IngestionNormalizer()
        self.cache = ingestion_cache

        self.gdelt_ingestor = GDELTIngestor()
        self.reddit_ingestor = RedditIngestor()
        self.market_ingestor = MarketDataIngestor()

        self._storage_callbacks: Dict[str, List[callable]] = {
            "geopol": [],
            "sentiment": [],
            "market": [],
        }
        self._is_initialized: bool = False

    def register_storage_callback(self, data_type: str, callback: callable) -> None:
        if data_type in self._storage_callbacks:
            self._storage_callbacks[data_type].append(callback)
            logger.info("Registered storage callback for %s", data_type)

    async def initialize(self) -> None:
        if self._is_initialized:
            return
        logger.info("Initializing ingestion manager...")

        self.scheduler.register(
            name="gdelt_articles",
            interval_seconds=settings.GDELT_POLL_INTERVAL,
            callback=self._ingest_gdelt_articles,
            description="GDELT article ingestion every 20 minutes",
        )
        self.scheduler.register(
            name="gdelt_events",
            interval_seconds=settings.GDELT_POLL_INTERVAL,
            callback=self._ingest_gdelt_events,
            description="GDELT CAMEO event ingestion every 20 minutes",
        )
        self.scheduler.register(
            name="reddit_sentiment",
            interval_seconds=settings.REDDIT_POLL_INTERVAL,
            callback=self._ingest_reddit,
            description="Reddit sentiment ingestion every 5 minutes",
        )
        self.scheduler.register(
            name="market_data_daily",
            interval_seconds=3600,
            callback=self._ingest_market_data,
            description="Market sector ETF data every hour",
        )
        self.scheduler.register(
            name="market_realtime",
            interval_seconds=900,
            callback=self._ingest_market_realtime,
            description="Market real-time prices every 15 minutes",
        )
        self.scheduler.register(
            name="market_volatility",
            interval_seconds=3600,
            callback=self._ingest_market_volatility,
            description="Market volatility and momentum every hour",
        )

        self._is_initialized = True
        logger.info("Ingestion manager initialized with %d tasks", self.scheduler.task_count)

    async def start(self) -> None:
        await self.initialize()
        await self.scheduler.start()
        logger.info("Ingestion manager started.")

    async def stop(self) -> None:
        await self.scheduler.stop()
        await self.gdelt_ingestor.close()
        await self.reddit_ingestor.close()
        await self.market_ingestor.close()
        logger.info("Ingestion manager stopped.")

    async def trigger_all(self) -> Dict[str, Any]:
        return await self.scheduler.trigger_all()

    async def trigger_source(self, source: str) -> Optional[Dict[str, Any]]:
        return await self.scheduler.trigger_now(source)

    async def trigger_gdelt(self) -> Dict[str, Any]:
        return await self.scheduler.trigger_now("gdelt_articles") or {}

    async def trigger_reddit(self) -> Dict[str, Any]:
        return await self.scheduler.trigger_now("reddit_sentiment") or {}

    async def trigger_market(self) -> Dict[str, Any]:
        return await self.scheduler.trigger_now("market_data_daily") or {}

    async def _ingest_gdelt_articles(self) -> Dict[str, Any]:
        logger.info("Ingestion cycle: GDELT articles starting...")
        result = await self.gdelt_ingestor.ingest_articles(
            minutes_back=20,
            max_per_query=50,
        )

        if result.get("status") == "success":
            await self._store_geopol_events(result.get("events", []))
            await ingestion_cache.update_last_run("gdelt_articles", "success")
            await ingestion_cache.increment_stat("gdelt", "articles_ingested", len(result.get("events", [])))

        return result

    async def _ingest_gdelt_events(self) -> Dict[str, Any]:
        logger.info("Ingestion cycle: GDELT events starting...")
        result = await self.gdelt_ingestor.ingest_events(
            minutes_back=20,
            max_per_query=25,
        )

        if result.get("status") == "success":
            await self._store_geopol_events(result.get("events", []))
            await ingestion_cache.update_last_run("gdelt_events", "success")

        return result

    async def _ingest_reddit(self) -> Dict[str, Any]:
        logger.info("Ingestion cycle: Reddit sentiment starting...")
        result = await self.reddit_ingestor.ingest_multi_subreddit(
            limit_per_sub=50,
            sort_strategy="balanced",
            max_age_hours=24.0,
            concurrency=3,
        )

        if result.get("status") == "success":
            analyzed = result.get("analyzed_posts", [])
            if analyzed:
                await self._store_sentiment_data(analyzed)
                await ingestion_cache.increment_stat("reddit", "posts_ingested", len(analyzed))

                ticker_agg = result.get("ticker_aggregation", {})
                for entry in ticker_agg.get("most_mentioned", [])[:10]:
                    await ingestion_cache.increment_stat(
                        "reddit", f"ticker:{entry['ticker']}", entry["mentions"]
                    )

            await ingestion_cache.update_last_run("reddit", "success")

        return result

    async def _ingest_market_data(self) -> Dict[str, Any]:
        logger.info("Ingestion cycle: Market data starting...")
        result = await self.market_ingestor.ingest_sector_etfs(
            days_back=30,
        )

        if result.get("status") == "success":
            perf = result.get("sector_performance", {})
            await ingestion_cache.increment_stat("tiingo", "sector_fetched", len(perf))
            await ingestion_cache.update_last_run("market_data", "success")

        return result

    async def _ingest_market_realtime(self) -> Dict[str, Any]:
        from app.services.tiingo.ingestor import _is_market_open
        if not _is_market_open():
            return {"status": "skipped", "reason": "market_closed"}

        logger.info("Ingestion cycle: Market real-time starting...")
        result = await self.market_ingestor.ingest_realtime_prices()

        if result.get("status") == "success":
            await ingestion_cache.update_last_run("market_realtime", "success")

        return result

    async def _ingest_market_volatility(self) -> Dict[str, Any]:
        logger.info("Ingestion cycle: Market volatility starting...")
        result = await self.market_ingestor.ingest_volatility_momentum()

        if result.get("status") == "success":
            await ingestion_cache.update_last_run("market_volatility", "success")

        return result

    async def _store_geopol_events(self, events: List) -> None:
        for callback in self._storage_callbacks.get("geopol", []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(events)
                else:
                    callback(events)
            except Exception as e:
                logger.warning("Geopol storage callback failed: %s", e)

    async def _store_sentiment_data(self, posts: List) -> None:
        for callback in self._storage_callbacks.get("sentiment", []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(posts)
                else:
                    callback(posts)
            except Exception as e:
                logger.warning("Sentiment storage callback failed: %s", e)

    def status(self) -> Dict[str, Any]:
        return {
            "is_running": self.scheduler.is_running,
            "is_initialized": self._is_initialized,
            "task_count": self.scheduler.task_count,
            "scheduler": self.scheduler.status(),
            "gdelt": self.gdelt_ingestor.stats,
            "reddit": self.reddit_ingestor.stats,
            "market": self.market_ingestor.stats,
            "cache": {
                "available": True,
            },
        }


ingestion_manager = IngestionManager()
