from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from app.config import settings
from app.logging_config import get_logger
from app.models.sentiment import SentimentData
from app.services.base import default_retry
from app.services.reddit.analyzer import SentimentAnalyzer
from app.services.reddit.client import RedditClient
from app.utils.rate_limiter import RateLimiter

logger = get_logger(__name__)

TARGET_SUBREDDITS: List[str] = [
    "wallstreetbets",
    "investing",
    "stocks",
    "geopolitics",
    "worldnews",
    "economics",
    "trade",
    "StockMarket",
    "options",
    "MarketSentiment",
]

SORT_STRATEGIES: Dict[str, List[str]] = {
    "hot": ["hot", "hot", "hot"],
    "balanced": ["hot", "new", "rising"],
    "deep": ["new", "rising", "controversial"],
}


class RedditIngestor:
    """Scheduled Reddit ingestor with concurrent subreddit scraping, hype/fear extraction, dedup."""

    def __init__(
        self,
        client: Optional[RedditClient] = None,
        analyzer: Optional[SentimentAnalyzer] = None,
    ) -> None:
        self.client = client or RedditClient()
        self.analyzer = analyzer or SentimentAnalyzer()
        self._seen_post_ids: Set[str] = set()
        self._last_run: Optional[datetime] = None
        self._run_count: int = 0
        self._total_ingested: int = 0
        self._total_skipped: int = 0
        self._errors: int = 0
        self._rate_limiter = RateLimiter(
            max_calls=30,
            period=60.0,
            name="reddit_ingestor",
        )

    @default_retry(max_attempts=2)
    async def ingest_subreddit(
        self,
        subreddit: str,
        limit: int = 50,
        sort: str = "hot",
        max_age_hours: float = 24.0,
    ) -> List[Dict[str, Any]]:
        """Fetch and analyze posts from a single subreddit."""
        async with self._rate_limiter:
            try:
                raw_posts = await self.client.fetch_subreddit_posts(
                    subreddit_name=subreddit,
                    limit=limit,
                    sort=sort,
                )
            except Exception as e:
                logger.warning("Reddit fetch failed for r/%s: %s", subreddit, e)
                return []

        now = datetime.now(timezone.utc)
        analyzed: List[Dict[str, Any]] = []

        for post in raw_posts:
            post_id = post.get("id", "")
            if post_id in self._seen_post_ids:
                continue

            created = post.get("created_utc")
            if isinstance(created, datetime):
                age_hours = (now - created).total_seconds() / 3600
                if age_hours > max_age_hours:
                    continue

            self._seen_post_ids.add(post_id)

            analyzed_post = self.analyzer.analyze_post(post, current_time=now)
            analyzed.append({
                "raw": post,
                "analyzed": analyzed_post,
            })
            self._total_ingested += 1

        self._total_skipped += len(raw_posts) - len(analyzed)
        logger.debug("r/%s: %d posts -> %d analyzed", subreddit, len(raw_posts), len(analyzed))
        return analyzed

    async def ingest_multi_subreddit(
        self,
        subreddits: Optional[List[str]] = None,
        limit_per_sub: int = 50,
        sort_strategy: str = "balanced",
        max_age_hours: float = 24.0,
        concurrency: int = 3,
    ) -> Dict[str, Any]:
        """Concurrently scrape multiple subreddits and aggregate results."""
        targets = subreddits or TARGET_SUBREDDITS
        sorts = SORT_STRATEGIES.get(sort_strategy, SORT_STRATEGIES["balanced"])
        logger.info(
            "Reddit multi-ingestion: %d subreddits, limit=%d, strategy=%s",
            len(targets), limit_per_sub, sort_strategy,
        )

        semaphore = asyncio.Semaphore(concurrency)

        async def ingest_with_semaphore(sr: str, sort_method: str) -> List[Dict[str, Any]]:
            async with semaphore:
                return await self.ingest_subreddit(
                    subreddit=sr,
                    limit=limit_per_sub,
                    sort=sort_method,
                    max_age_hours=max_age_hours,
                )

        sort_cycle = [sorts[i % len(sorts)] for i in range(len(targets))]
        tasks = [
            ingest_with_semaphore(sr, sort_method)
            for sr, sort_method in zip(targets, sort_cycle)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_analyzed: List[SentimentData] = []
        subreddit_stats: Dict[str, Dict[str, Any]] = {}
        total_fetched = 0
        total_errors = 0

        for sr_index, result in enumerate(results):
            sr_name = targets[sr_index] if sr_index < len(targets) else "unknown"
            if isinstance(result, Exception):
                logger.error("Subreddit %s failed: %s", sr_name, result)
                subreddit_stats[sr_name] = {"status": "error", "error": str(result)}
                total_errors += 1
                continue

            analyzed_posts = result
            subreddit_stats[sr_name] = {
                "status": "success",
                "fetched": len(analyzed_posts),
            }
            total_fetched += len(analyzed_posts)

            for ap in analyzed_posts:
                data = ap.get("analyzed")
                if data:
                    all_analyzed.append(data)

        hype_fear = self.analyzer.compute_hype_fear_index(all_analyzed)
        ticker_aggregation = self._aggregate_tickers(all_analyzed)
        aggregate = self.analyzer.aggregate(all_analyzed)

        self._run_count += 1
        self._last_run = datetime.now(timezone.utc)

        logger.info(
            "Reddit ingestion: %d subreddits, %d analyzed posts, hype=%.3f, fear=%.3f, signal=%s",
            len(targets), len(all_analyzed),
            hype_fear["hype_index"], hype_fear["fear_index"], hype_fear["signal"],
        )

        return {
            "status": "success",
            "source": "reddit",
            "run_count": self._run_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "subreddits_targeted": len(targets),
            "subreddits_errored": total_errors,
            "total_posts_fetched": total_fetched,
            "analyzed_posts_count": len(all_analyzed),
            "total_ingested_cumulative": self._total_ingested,
            "aggregate": aggregate.model_dump(),
            "hype_fear_index": hype_fear,
            "ticker_aggregation": ticker_aggregation,
            "analyzed_posts": all_analyzed,
            "subreddit_stats": subreddit_stats,
        }

    def _aggregate_tickers(self, posts: List[SentimentData]) -> Dict[str, Any]:
        ticker_data: Dict[str, Dict[str, Any]] = {}

        for post in posts:
            for ticker in post.tickers_mentioned:
                if ticker not in ticker_data:
                    ticker_data[ticker] = {
                        "mentions": 0,
                        "total_score": 0.0,
                        "avg_sentiment": 0.0,
                        "posts": [],
                    }
                ticker_data[ticker]["mentions"] += 1
                ticker_data[ticker]["total_score"] += post.sentiment_score
                ticker_data[ticker]["posts"].append(post.post_id)

        for ticker, data in ticker_data.items():
            data["avg_sentiment"] = round(data["total_score"] / data["mentions"], 4)
            data.pop("total_score")
            data["posts"] = data["posts"][:5]

        sorted_tickers = sorted(
            ticker_data.items(),
            key=lambda x: x[1]["mentions"],
            reverse=True,
        )

        return {
            "total_tickers_mentioned": len(ticker_data),
            "most_mentioned": [
                {"ticker": t, **d} for t, d in sorted_tickers[:20]
            ],
        }

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "source": "reddit",
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "run_count": self._run_count,
            "total_ingested": self._total_ingested,
            "total_skipped": self._total_skipped,
            "errors": self._errors,
            "seen_post_ids": len(self._seen_post_ids),
        }

    async def close(self) -> None:
        await self.client.close()
