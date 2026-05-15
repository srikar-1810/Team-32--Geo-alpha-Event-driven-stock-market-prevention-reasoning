from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class SentimentQueryParams(BaseModel):
    query: str = Field(..., min_length=1)
    source: str = Field(default="reddit")
    hours_back: int = Field(default=24, ge=1, le=720)
    limit: int = Field(default=100, ge=1, le=1000)


class SentimentAnalysisResponse(BaseModel):
    query: str
    source: str
    overall_score: float = Field(..., ge=-1.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    distribution: dict = Field(default_factory=lambda: {"positive": 0.0, "negative": 0.0, "neutral": 0.0})
    volume: int
    top_keywords: List[str]
    analyzed_at: datetime


class SentimentTrendPoint(BaseModel):
    timestamp: datetime
    score: float
    volume: int
    volatility: float


class SentimentTrendResponse(BaseModel):
    ticker: Optional[str] = None
    sector: Optional[str] = None
    period_hours: int
    data_points: List[SentimentTrendPoint]
    trend_direction: str
    volatility: float
    generated_at: datetime


class RedditPostResponse(BaseModel):
    id: str
    subreddit: str
    title: str
    text: str
    score: int
    num_comments: int
    created_utc: datetime
    sentiment_score: float
    tickers_mentioned: List[str]
