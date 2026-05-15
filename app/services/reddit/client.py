from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import asyncpraw
import asyncpraw.models

from app.config import settings
from app.logging_config import get_logger
from app.models.sentiment import SentimentData
from app.services.base import BaseService

logger = get_logger(__name__)


class RedditClient(BaseService):
    """Async Reddit API client for fetching and analyzing financial sentiment."""

    def __init__(self) -> None:
        super().__init__("reddit")
        self._reddit: Optional[asyncpraw.Reddit] = None

    async def _get_client(self) -> asyncpraw.Reddit:
        if self._reddit is None:
            self.validate_config([
                "REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT"
            ])
            self._reddit = asyncpraw.Reddit(
                client_id=settings.REDDIT_CLIENT_ID,
                client_secret=settings.REDDIT_CLIENT_SECRET,
                user_agent=settings.REDDIT_USER_AGENT,
                timeout=30,
            )
        return self._reddit

    async def fetch_subreddit_posts(
        self,
        subreddit_name: str,
        limit: int = 100,
        sort: str = "hot",
    ) -> List[Dict[str, Any]]:
        reddit = await self._get_client()
        subreddit = await reddit.subreddit(subreddit_name)
        posts = []

        sort_methods = {
            "hot": subreddit.hot,
            "new": subreddit.new,
            "top": subreddit.top,
            "rising": subreddit.rising,
        }
        method = sort_methods.get(sort, subreddit.hot)

        async for submission in method(limit=limit):
            if submission.stickied:
                continue
            await submission.load()
            posts.append({
                "id": submission.id,
                "title": submission.title,
                "text": submission.selftext or "",
                "score": submission.score,
                "num_comments": submission.num_comments,
                "created_utc": datetime.fromtimestamp(submission.created_utc, tz=timezone.utc),
                "subreddit": subreddit_name,
                "url": submission.url,
                "upvote_ratio": submission.upvote_ratio,
            })

        return posts

    async def fetch_multiple_subreddits(
        self,
        subreddits: Optional[List[str]] = None,
        limit: int = 100,
        sort: str = "hot",
    ) -> List[Dict[str, Any]]:
        targets = subreddits or settings.reddit_subreddits_list
        tasks = [
            self.fetch_subreddit_posts(sr, limit=limit // len(targets), sort=sort)
            for sr in targets
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_posts = []
        for sr, result in zip(targets, results):
            if isinstance(result, Exception):
                logger.warning("Failed to fetch r/%s: %s", sr, result)
                continue
            all_posts.extend(result)
        return all_posts

    async def search_posts(
        self,
        query: str,
        subreddit: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        reddit = await self._get_client()
        posts = []
        search_sub = subreddit if subreddit else "all"
        sub = await reddit.subreddit(search_sub)

        async for submission in sub.search(query, limit=limit):
            await submission.load()
            posts.append({
                "id": submission.id,
                "title": submission.title,
                "text": submission.selftext or "",
                "score": submission.score,
                "num_comments": submission.num_comments,
                "created_utc": datetime.fromtimestamp(submission.created_utc, tz=timezone.utc),
                "subreddit": search_sub,
                "url": submission.url,
                "upvote_ratio": submission.upvote_ratio,
            })

        return posts

    async def to_sentiment_model(self, post: Dict[str, Any]) -> SentimentData:
        return SentimentData(
            source="reddit",
            platform="reddit",
            post_id=post["id"],
            subreddit=post["subreddit"],
            title=post["title"],
            text=post["text"],
            score=post["score"],
            num_comments=post["num_comments"],
            created_utc=post["created_utc"],
            sentiment_score=0.0,
            sentiment_label="neutral",
            confidence=0.0,
            tickers_mentioned=[],
            keywords=[],
        )

    async def close(self) -> None:
        if self._reddit:
            await self._reddit.close()

    async def __aenter__(self) -> RedditClient:
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()
