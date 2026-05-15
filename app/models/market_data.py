from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.models.base import Entity


class MarketDataPoint(Entity):
    ticker: str
    date: date
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    adj_close: Optional[float] = None
    change_pct: Optional[float] = None
    source: str = "tiingo"
    raw_data: Optional[Dict[str, Any]] = None


class SectorExposure(Entity):
    sector: str
    tickers: List[str]
    exposure_pct: float = Field(default=0.0, ge=0.0, le=1.0)
    volatility: float = 0.0
    beta: float = 1.0
    last_updated: datetime


class MarketImpactAssessment(Entity):
    model_config = {"protected_namespaces": ()}
    event_id: str
    overall_impact_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    affected_sectors: List[Dict[str, Any]] = Field(default_factory=list)
    top_impacted_stocks: List[Dict[str, Any]] = Field(default_factory=list)
    volatility_forecast: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    model_used: str = ""
    generated_at: datetime
