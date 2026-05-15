from __future__ import annotations

from datetime import date, datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.api.v1.schemas.markets import (
    MarketDataPoint,
    MarketImpactResponse,
    MarketQueryParams,
    PortfolioImpactRequest,
    PortfolioImpactResponse,
    SectorPerformanceResponse,
)
from app.core.dependencies import get_db_session
from app.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/data/{ticker}", response_model=List[MarketDataPoint])
async def get_market_data(
    ticker: str,
    start_date: date = Query(...),
    end_date: date = Query(...),
    db=Depends(get_db_session),
):
    from app.services.chroma.client import ChromaClient
    chroma = ChromaClient()
    
    try:
        results = await chroma.query(
            collection_name="market_data",
            where={"ticker": ticker.upper()},
            n_results=100
        )
        
        metadatas = results.get("metadatas", [[]])[0]
        if not metadatas:
            return []

        points = []
        for m in metadatas:
            points.append(MarketDataPoint(
                ticker=ticker,
                timestamp=datetime.fromisoformat(m["date"]) if "T" in m["date"] else datetime.strptime(m["date"], "%Y-%m-%d"),
                open=m["open"],
                high=m["high"],
                low=m["low"],
                close=m["close"],
                volume=m["volume"]
            ))
        
        return sorted(points, key=lambda x: x.timestamp)
    except Exception as e:
        logger.error("Market data retrieval failed: %s", e)
        return []


@router.get("/impact", response_model=MarketImpactResponse)
async def assess_market_impact(
    event_id: str = Query(..., description="Geopolitical event ID"),
    db=Depends(get_db_session),
):
    from app.services.chroma.client import ChromaClient
    chroma = ChromaClient()
    
    try:
        # Fetch event details
        results = await chroma.query(
            collection_name="geopol_events",
            where={"id": event_id},
            n_results=1
        )
        
        metadatas = results.get("metadatas", [[]])[0]
        if not metadatas:
            return MarketImpactResponse(
                event_id=event_id, overall_impact_score=0.0, affected_sectors=[],
                top_impacted_stocks=[], volatility_forecast=[], confidence=0.0,
                generated_at=datetime.now(timezone.utc)
            )
            
        event = metadatas[0]
        severity = float(event.get("severity", 0.5))
        sectors = event.get("sectors", "").split(",")
        
        impacted = []
        for s in sectors:
            if s:
                impacted.append({
                    "sector": s.strip().capitalize(),
                    "impact_score": round(severity * 0.9, 2),
                    "direction": "bullish" if severity > 0.5 else "neutral"
                })

        return MarketImpactResponse(
            event_id=event_id,
            overall_impact_score=round(severity, 2),
            affected_sectors=impacted,
            top_impacted_stocks=["SPY", "XLE", "AAPL"],
            volatility_forecast=[0.15, 0.18, 0.22],
            confidence=0.85,
            generated_at=datetime.now(timezone.utc),
        )
    except Exception as e:
        logger.error("Market impact assessment failed: %s", e)
        return MarketImpactResponse(
            event_id=event_id, overall_impact_score=0.0, affected_sectors=[],
            top_impacted_stocks=[], volatility_forecast=[], confidence=0.0,
            generated_at=datetime.now(timezone.utc)
        )


@router.get("/sectors", response_model=List[SectorPerformanceResponse])
async def get_sector_performance(
    db=Depends(get_db_session),
):
    return []


@router.post("/portfolio/impact", response_model=PortfolioImpactResponse)
async def assess_portfolio_impact(
    payload: PortfolioImpactRequest,
    db=Depends(get_db_session),
):
    return PortfolioImpactResponse(
        portfolio_id=payload.portfolio_id,
        overall_risk_score=0.0,
        holdings_impact=[],
        recommended_actions=[],
        assessed_at=datetime.now(timezone.utc),
    )
