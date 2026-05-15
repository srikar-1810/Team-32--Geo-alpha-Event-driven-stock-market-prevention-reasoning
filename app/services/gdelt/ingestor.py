from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from app.config import settings
from app.logging_config import get_logger
from app.models.geopol_event import GeoPolEvent
from app.services.base import default_retry
from app.services.gdelt.client import GDELTClient
from app.services.gdelt.parser import GDELTParser

logger = get_logger(__name__)

GDELT_QUERIES: List[str] = [
    "conflict",
    "war",
    "sanctions",
    "election",
    "crisis",
    "protest",
    "military",
    "trade",
    "terrorism",
    "diplomacy",
    "oil",
    "inflation",
    "interest rates",
    "central bank",
    "tariff",
    "treaty",
    "summit",
    "weapon",
    "nuclear",
    "cyberattack",
]


class GDELTIngestor:
    """Scheduled GDELT ingestor with 20-min polling, dedup, and entity enrichment."""

    def __init__(
        self,
        client: Optional[GDELTClient] = None,
        parser: Optional[GDELTParser] = None,
    ) -> None:
        self.client = client or GDELTClient()
        self.parser = parser or GDELTParser()
        self._seen_urls: Set[str] = set()
        self._seen_event_ids: Set[str] = set()
        self._last_run: Optional[datetime] = None
        self._run_count: int = 0
        self._total_ingested: int = 0
        self._total_skipped: int = 0
        self._errors: int = 0

    @default_retry(max_attempts=3)
    async def ingest_articles(
        self,
        minutes_back: int = 20,
        max_per_query: int = 50,
        queries: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Fetch and parse GDELT articles from the time window, deduplicate, return normalized events."""
        target_queries = queries or GDELT_QUERIES
        logger.info(
            "GDELT article ingestion: %d queries, %d min window",
            len(target_queries), minutes_back,
        )

        try:
            raw_articles = await self.client.fetch_articles_by_time_window(
                queries=target_queries,
                minutes_back=minutes_back,
                max_per_query=max_per_query,
            )
        except Exception as e:
            self._errors += 1
            logger.error("GDELT article fetch failed: %s", e)
            return {"status": "error", "error": str(e), "ingested": 0, "skipped": 0}

        parsed: List[GeoPolEvent] = []
        skipped = 0
        for article in raw_articles:
            url = article.get("url", "")
            if url and url in self._seen_urls:
                skipped += 1
                continue

            event = self.parser.parse_article(article)
            if event:
                if url:
                    self._seen_urls.add(url)
                parsed.append(event)
                self._total_ingested += 1
            else:
                skipped += 1

        if parsed:
            signal_report = self._compute_signal_report(parsed)
        else:
            signal_report = {"high_signal": 0, "medium_signal": 0, "low_signal": 0}

        self._run_count += 1
        self._last_run = datetime.now(timezone.utc)
        self._total_skipped += skipped

        logger.info(
            "GDELT ingestion: %d articles -> %d events parsed, %d skipped (cumulative: %d total)",
            len(raw_articles), len(parsed), skipped, self._total_ingested,
        )

        return {
            "status": "success",
            "source": "gdelt_articles",
            "run_count": self._run_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "raw_fetched": len(raw_articles),
            "events_parsed": len(parsed),
            "skipped_dedup": skipped,
            "total_ingested_cumulative": self._total_ingested,
            "queries_used": len(target_queries),
            "signal_report": signal_report,
            "events": parsed,
            "time_window_minutes": minutes_back,
        }

    @default_retry(max_attempts=3)
    async def ingest_events(
        self,
        minutes_back: int = 20,
        max_per_query: int = 50,
        queries: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Fetch CAMEO-coded events for structured geopolitical event data."""
        target_queries = queries or GDELT_QUERIES[:10]

        try:
            raw_events = await self.client.fetch_events_by_time_window(
                queries=target_queries,
                minutes_back=minutes_back,
                max_per_query=max_per_query,
            )
        except Exception as e:
            self._errors += 1
            logger.error("GDELT event fetch failed: %s", e)
            return {"status": "error", "error": str(e), "ingested": 0}

        parsed: List[GeoPolEvent] = []
        skipped = 0
        for raw in raw_events:
            eid = raw.get("eventid", raw.get("url", ""))
            if eid and eid in self._seen_event_ids:
                skipped += 1
                continue
            event = self.parser.parse_event(raw)
            if event:
                if eid:
                    self._seen_event_ids.add(eid)
                parsed.append(event)
            else:
                skipped += 1

        self._run_count += 1
        self._last_run = datetime.now(timezone.utc)

        return {
            "status": "success",
            "source": "gdelt_events",
            "run_count": self._run_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "raw_fetched": len(raw_events),
            "events_parsed": len(parsed),
            "skipped_dedup": skipped,
            "events": parsed,
        }

    async def ingest_full(
        self,
        minutes_back: int = 20,
        max_per_query: int = 50,
    ) -> Dict[str, Any]:
        """Combined ingestion of both article list and event list data."""
        articles_result = await self.ingest_articles(
            minutes_back=minutes_back, max_per_query=max_per_query,
        )
        events_result = await self.ingest_events(
            minutes_back=minutes_back, max_per_query=max_per_query // 2,
        )

        all_events: List[GeoPolEvent] = []
        all_events.extend(articles_result.get("events", []))
        all_events.extend(events_result.get("events", []))

        seen_ids = set()
        deduped = []
        for e in all_events:
            dedup_key = f"{e.title}|{e.event_date.isoformat() if e.event_date else ''}|{e.location}"
            if dedup_key not in seen_ids:
                seen_ids.add(dedup_key)
                deduped.append(e)

        logger.info(
            "GDELT full ingestion: %d total events after cross-source dedup",
            len(deduped),
        )

        enrichment = self._compute_signal_report(deduped) if deduped else {}

        return {
            "status": "success",
            "source": "gdelt_full",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "articles_result": articles_result,
            "events_result": events_result,
            "total_unique_events": len(deduped),
            "events": deduped,
            "signal_report": enrichment,
        }

    def _compute_signal_report(self, events: List[GeoPolEvent]) -> Dict[str, Any]:
        high = sum(1 for e in events if self.parser.compute_signal_strength(e)["is_high_signal"])
        medium = sum(1 for e in events if self.parser.compute_signal_strength(e)["is_medium_signal"])
        low = sum(1 for e in events if self.parser.compute_signal_strength(e)["is_low_signal"])

        sectors: Dict[str, int] = {}
        countries: Dict[str, int] = {}
        event_types: Dict[str, int] = {}

        for e in events:
            for s in e.affected_sectors:
                sectors[s] = sectors.get(s, 0) + 1
            loc = e.location
            if loc and loc != "Unknown":
                countries[loc] = countries.get(loc, 0) + 1
            et = e.event_type
            event_types[et] = event_types.get(et, 0) + 1

        return {
            "high_signal": high,
            "medium_signal": medium,
            "low_signal": low,
            "top_sectors": sorted(sectors.items(), key=lambda x: x[1], reverse=True)[:5],
            "top_countries": sorted(countries.items(), key=lambda x: x[1], reverse=True)[:5],
            "event_type_distribution": event_types,
        }

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "source": "gdelt",
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "run_count": self._run_count,
            "total_ingested": self._total_ingested,
            "total_skipped": self._total_skipped,
            "errors": self._errors,
            "seen_urls": len(self._seen_urls),
            "seen_event_ids": len(self._seen_event_ids),
        }

    async def close(self) -> None:
        await self.client.close()
