from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from app.logging_config import get_logger
from app.services.gdelt.client import GDELTClient
from app.services.gdelt.parser import GDELTParser
from app.services.historical.models import (
    EventTone,
    HistoricalEventRaw,
    HistoricalMarketImpact,
)
from app.utils.rate_limiter import RateLimiter

logger = get_logger(__name__)

HISTORICAL_GDELT_QUERIES: List[str] = [
    "conflict", "war", "sanctions", "election", "crisis", "protest",
    "military", "trade", "terrorism", "diplomacy", "oil", "inflation",
    "interest rates", "central bank", "tariff", "treaty", "summit",
    "nuclear", "cyberattack", "pandemic", "natural disaster", "earthquake",
    "hurricane", "flood", "recession", "debt crisis", "currency crisis",
    "government collapse", "ceasefire", "peace treaty", "trade agreement",
    "tariff", "embargo", "military exercise", "troop deployment",
    "assassination", "riot", "coup", "independence", "referendum",
]

MAX_RECORDS_PER_QUERY = 500


class HistoricalGDELTCollector:
    """Collects historical geopolitical events from GDELT across date ranges."""

    def __init__(
        self,
        gdelt_client: Optional[GDELTClient] = None,
        parser: Optional[GDELTParser] = None,
    ) -> None:
        self.client = gdelt_client or GDELTClient()
        self.parser = parser or GDELTParser()
        self._rate_limiter = RateLimiter(max_calls=10, period=60.0, name="historical_gdelt")

    async def collect_by_date_range(
        self,
        start_date: date,
        end_date: date,
        queries: Optional[List[str]] = None,
        max_per_query: int = 250,
        include_gkg: bool = False,
    ) -> List[HistoricalMarketImpact]:
        """Collect all events between two dates across multiple query dimensions."""
        target_queries = queries or HISTORICAL_GDELT_QUERIES
        start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(end_date, datetime.min.time()).replace(tzinfo=timezone.utc)

        logger.info(
            "Historical GDELT collection: %s to %s, %d queries",
            start_date.isoformat(), end_date.isoformat(), len(target_queries),
        )

        all_events: List[HistoricalMarketImpact] = []
        seen_signatures: set = set()

        chunk_size = 3
        for i in range(0, len(target_queries), chunk_size):
            chunk = target_queries[i:i + chunk_size]
            tasks = [
                self._collect_single_query(
                    query=q, start_dt=start_dt, end_dt=end_dt, max_records=max_per_query,
                )
                for q in chunk
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    logger.warning("Query chunk failed: %s", result)
                    continue
                for event in result:
                    sig = f"{event.event_title[:50]}|{event.event_date.strftime('%Y%m%d')}|{event.location}"
                    if sig not in seen_signatures:
                        seen_signatures.add(sig)
                        all_events.append(event)

            logger.info(
                "Processed queries %d-%d of %d, %d unique events so far",
                i + 1, min(i + chunk_size, len(target_queries)),
                len(target_queries), len(all_events),
            )

        logger.info(
            "Historical GDELT collection complete: %d unique events from %s to %s",
            len(all_events), start_date.isoformat(), end_date.isoformat(),
        )
        return all_events

    async def collect_last_n_days(
        self,
        days: int = 30,
        queries: Optional[List[str]] = None,
        max_per_query: int = 250,
    ) -> List[HistoricalMarketImpact]:
        end = date.today()
        start = end - timedelta(days=days)
        return await self.collect_by_date_range(
            start_date=start,
            end_date=end,
            queries=queries,
            max_per_query=max_per_query,
        )

    async def _collect_single_query(
        self,
        query: str,
        start_dt: datetime,
        end_dt: datetime,
        max_records: int = 250,
    ) -> List[HistoricalMarketImpact]:
        try:
            async with self._rate_limiter:
                articles = await self.client.fetch_article_list(
                    query=query,
                    start_date=start_dt,
                    end_date=end_dt,
                    max_records=max_records,
                )
        except Exception as e:
            logger.warning("GDELT query '%s' failed: %s", query, e)
            return []

        events: List[HistoricalMarketImpact] = []
        for article in articles:
            try:
                impact = self._article_to_impact(article)
                if impact:
                    events.append(impact)
            except Exception as e:
                logger.debug("Failed to parse article for '%s': %s", query, e)

        logger.debug("Query '%s': %d articles -> %d impacts", query, len(articles), len(events))
        return events

    def _article_to_impact(self, article: Dict[str, Any]) -> Optional[HistoricalMarketImpact]:
        parsed = self.parser.parse_article(article)
        if not parsed:
            return None

        raw = parsed.gdelt_raw or {}
        tone_data = raw.get("tone", {}) if isinstance(raw, dict) else {}
        countries = raw.get("countries", []) if isinstance(raw, dict) else []
        tickers = raw.get("tickers", []) if isinstance(raw, dict) else []
        categories = raw.get("categories", {}) if isinstance(raw, dict) else {}

        tone = EventTone(
            tone_score=tone_data.get("tone_score", 0.0),
            positive_score=tone_data.get("positive_score", 0.0),
            negative_score=tone_data.get("negative_score", 0.0),
            polarity=tone_data.get("polarity", 0.0),
            activity_reference=tone_data.get("activity_reference", 0.0),
            self_reference=tone_data.get("self_reference", 0.0),
        )

        signal = self.parser.compute_signal_strength(parsed)

        return HistoricalMarketImpact(
            event_id=str(uuid4()),
            event_title=parsed.title,
            event_description=parsed.description,
            event_date=parsed.event_date or datetime.now(timezone.utc),
            event_type=parsed.event_type,
            location=parsed.location,
            countries=countries if isinstance(countries, list) else [parsed.location] if parsed.location != "Unknown" else [],
            actors=parsed.actors,
            num_mentions=parsed.mentions,
            source_url=parsed.source_url,
            tone=tone,
            severity=parsed.severity,
            confidence=signal.get("signal_strength", 0.5),
            source="gdelt",
            collected_at=datetime.now(timezone.utc),
            top_bullish_stocks=[{"ticker": t, "direction": "neutral"} for t in (tickers or [])[:5]],
            top_bearish_stocks=[],
        )

    async def close(self) -> None:
        await self.client.close()
