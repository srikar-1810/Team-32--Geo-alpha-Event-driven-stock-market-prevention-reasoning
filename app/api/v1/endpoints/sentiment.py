from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.api.v1.schemas.sentiment import (
    SentimentAnalysisResponse,
    SentimentQueryParams,
    SentimentTrendResponse,
)
from app.api.v1.schemas.common import PaginatedResponse
from app.core.dependencies import get_db_session
from app.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/analysis", response_model=SentimentAnalysisResponse)
async def analyze_sentiment(
    query: str = Query(..., description="Query text to analyze sentiment for"),
    source: str = Query("reddit", description="Data source"),
    db=Depends(get_db_session),
):
    from app.services.chroma.client import ChromaClient
    chroma = ChromaClient()
    
    try:
        # Query sentiment data from ChromaDB
        results = await chroma.query(
            collection_name="sentiment_data",
            query_texts=[query],
            n_results=100,
            where={"source": source} if source != "all" else None
        )
        
        metadatas = results.get("metadatas", [[]])[0]
        if not metadatas:
            return SentimentAnalysisResponse(
                query=query, source=source, overall_score=0.0, confidence=0.0,
                distribution={"positive": 0, "negative": 0, "neutral": 0},
                volume=0, top_keywords=[], analyzed_at=datetime.now(timezone.utc)
            )

        # Calculate metrics
        scores = [m.get("sentiment_score", 0.0) for m in metadatas]
        avg_score = sum(scores) / len(scores)
        
        pos = len([s for s in scores if s > 0.1])
        neg = len([s for s in scores if s < -0.1])
        neu = len(scores) - pos - neg
        
        return SentimentAnalysisResponse(
            query=query,
            source=source,
            overall_score=round(avg_score, 3),
            confidence=round(min(1.0, len(scores) / 50), 2),
            distribution={
                "positive": round(pos / len(scores), 2),
                "negative": round(neg / len(scores), 2),
                "neutral": round(neu / len(scores), 2)
            },
            volume=len(scores),
            top_keywords=["market", "volatility", "growth"], # Simplified for now
            analyzed_at=datetime.now(timezone.utc),
        )
    except Exception as e:
        logger.error("Sentiment analysis failed: %s", e)
        return SentimentAnalysisResponse(
            query=query, source=source, overall_score=0.0, confidence=0.0,
            distribution={"positive": 0, "negative": 0, "neutral": 0},
            volume=0, top_keywords=[], analyzed_at=datetime.now(timezone.utc)
        )


@router.get("/trends", response_model=SentimentTrendResponse)
async def get_sentiment_trends(
    ticker: Optional[str] = Query(None, description="Stock ticker symbol"),
    sector: Optional[str] = Query(None, description="Sector name"),
    hours: int = Query(24, ge=1, le=720),
    db=Depends(get_db_session),
):
    return SentimentTrendResponse(
        ticker=ticker,
        sector=sector,
        period_hours=hours,
        data_points=[],
        trend_direction="neutral",
        volatility=0.0,
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/posts", response_model=PaginatedResponse)
async def list_sentiment_posts(
    subreddit: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    db=Depends(get_db_session),
):
    return PaginatedResponse(items=[], total=0, page=1, page_size=limit)
