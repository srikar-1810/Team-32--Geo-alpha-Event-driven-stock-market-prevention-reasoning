from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings
from app.logging_config import get_logger
from app.services.base import BaseService, default_retry

logger = get_logger(__name__)


class GDELTClient(BaseService):
    """Async client for GDELT 2.0 API — Doc/Event/GKG queries with full extraction."""

    BASE_URL: str = settings.GDELT_BASE_URL

    def __init__(self) -> None:
        super().__init__("gdelt")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                timeout=settings.GDELT_TIMEOUT,
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=50),
            )
        return self._client

    @default_retry(max_attempts=settings.GDELT_MAX_RETRIES)
    async def fetch_article_list(
        self,
        query: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        max_records: int = 250,
        source_country: Optional[str] = None,
        source_lang: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch enriched article list with themes, entities, locations, tone, persons, orgs."""
        client = await self._get_client()
        params: Dict[str, Any] = {
            "query": query,
            "mode": "ArtList",
            "format": "json",
            "maxrecords": min(max_records, 500),
        }
        if start_date:
            params["startdatetime"] = start_date.strftime("%Y%m%d%H%M%S")
        if end_date:
            params["enddatetime"] = end_date.strftime("%Y%m%d%H%M%S")
        if source_country:
            params["sourcecountry"] = source_country
        if source_lang:
            params["sourcelang"] = source_lang

        response = await client.get("/doc/doc", params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("articles", data.get("results", []))

    @default_retry(max_attempts=settings.GDELT_MAX_RETRIES)
    async def fetch_event_list(
        self,
        query: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        max_records: int = 250,
    ) -> List[Dict[str, Any]]:
        """Fetch CAMEO-coded events with actor pairs, goldstein scale, event codes."""
        client = await self._get_client()
        params: Dict[str, Any] = {
            "query": query,
            "mode": "EventList",
            "format": "json",
            "maxrecords": min(max_records, 500),
        }
        if start_date:
            params["startdatetime"] = start_date.strftime("%Y%m%d%H%M%S")
        if end_date:
            params["enddatetime"] = end_date.strftime("%Y%m%d%H%M%S")

        response = await client.get("/doc/doc", params=params)
        response.raise_for_status()
        data = response.json()
        # GDELT EventList returns "results" or "events"
        return data.get("results", data.get("events", []))

    # Alias for background tasks
    async def fetch_events(self, *args, **kwargs) -> List[Dict[str, Any]]:
        return await self.fetch_event_list(*args, **kwargs)

    @default_retry(max_attempts=settings.GDELT_MAX_RETRIES)
    async def fetch_gkg(
        self,
        query: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        max_records: int = 250,
    ) -> List[Dict[str, Any]]:
        """Fetch Global Knowledge Graph data with rich entity extraction."""
        client = await self._get_client()
        params: Dict[str, Any] = {
            "query": query,
            "mode": "Gkg",
            "format": "json",
            "maxrecords": min(max_records, 500),
        }
        if start_date:
            params["startdatetime"] = start_date.strftime("%Y%m%d%H%M%S")
        if end_date:
            params["enddatetime"] = end_date.strftime("%Y%m%d%H%M%S")

        response = await client.get("/doc/gkg", params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("results", data.get("gkg", []))

    @default_retry(max_attempts=settings.GDELT_MAX_RETRIES)
    async def fetch_timeline(
        self,
        query: str,
        timeline_type: str = "timelinevol",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch volume/tone timeline data for trend analysis."""
        client = await self._get_client()
        valid_types = {"timelinevol", "timelinelang", "timelinesourcecountry", "tone", "timelinetone"}
        tl_type = timeline_type if timeline_type in valid_types else "timelinevol"

        params: Dict[str, Any] = {
            "query": query,
            "mode": tl_type,
            "format": "json",
        }
        if start_date:
            params["startdatetime"] = start_date.strftime("%Y%m%d%H%M%S")
        if end_date:
            params["enddatetime"] = end_date.strftime("%Y%m%d%H%M%S")

        response = await client.get("/doc/doc", params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("timeline", data.get("results", []))

    async def fetch_articles_by_time_window(
        self,
        queries: List[str],
        minutes_back: int = 20,
        max_per_query: int = 50,
    ) -> List[Dict[str, Any]]:
        """Fetch articles across multiple queries within a time window (for scheduled polling)."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(minutes=minutes_back)

        all_articles: List[Dict[str, Any]] = []
        seen_urls: set = set()

        for query in queries:
            try:
                articles = await self.fetch_article_list(
                    query=query,
                    start_date=start,
                    end_date=now,
                    max_records=max_per_query,
                )
                for article in articles:
                    url = article.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_articles.append(article)
            except Exception as e:
                logger.warning("GDELT query '%s' failed: %s", query, e)

        logger.info("GDELT fetched %d unique articles from %d queries", len(all_articles), len(queries))
        return all_articles

    async def fetch_events_by_time_window(
        self,
        queries: List[str],
        minutes_back: int = 20,
        max_per_query: int = 50,
    ) -> List[Dict[str, Any]]:
        """Fetch CAMEO events across multiple queries within a time window."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(minutes=minutes_back)

        all_events: List[Dict[str, Any]] = []
        seen_event_ids: set = set()

        for query in queries:
            try:
                events = await self.fetch_event_list(
                    query=query,
                    start_date=start,
                    end_date=now,
                    max_records=max_per_query,
                )
                for event in events:
                    eid = event.get("eventid", event.get("url", ""))
                    if eid and eid not in seen_event_ids:
                        seen_event_ids.add(eid)
                        all_events.append(event)
            except Exception as e:
                logger.warning("GDELT event query '%s' failed: %s", query, e)

        logger.info("GDELT fetched %d unique events from %d queries", len(all_events), len(queries))
        return all_events

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self) -> GDELTClient:
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()
