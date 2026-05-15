from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.models.base import Entity


class SentimentData(Entity):
    source: str = "reddit"
    platform: str
    post_id: str
    subreddit: str
    title: str
    text: str
    score: int = 0
    num_comments: int = 0
    created_utc: datetime
    sentiment_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    sentiment_label: str = "neutral"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    tickers_mentioned: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    embedding: Optional[List[float]] = None
    raw_data: Optional[Dict[str, Any]] = None


class SentimentAggregate(Entity):
    query: str
    source: str
    overall_score: float
    confidence: float
    distribution: Dict[str, float] = Field(
        default_factory=lambda: {"positive": 0.0, "negative": 0.0, "neutral": 0.0}
    )
    volume: int
    top_keywords: List[str] = Field(default_factory=list)
    top_posts: List[str] = Field(default_factory=list)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
