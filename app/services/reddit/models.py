from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RedditCredentials(BaseModel):
    client_id: str
    client_secret: str
    user_agent: str = "GeoMarketGPT/0.1.0"


class RedditFetchConfig(BaseModel):
    subreddits: List[str] = Field(
        default=["wallstreetbets", "stocks", "investing", "geopolitics"]
    )
    limit: int = 100
    sort: str = "hot"
    fetch_comments: bool = False
    comment_limit: int = 50


class RedditPostRaw(BaseModel):
    id: str
    title: str
    text: str
    score: int
    num_comments: int
    created_utc: datetime
    subreddit: str
    url: str
    upvote_ratio: float = 1.0
    edited: bool = False
    is_original_content: bool = False
    spoiler: bool = False
    stickied: bool = False


class RedditSearchParams(BaseModel):
    query: str
    subreddit: Optional[str] = None
    limit: int = 50
    sort: str = "relevance"
    time_filter: str = "all"
