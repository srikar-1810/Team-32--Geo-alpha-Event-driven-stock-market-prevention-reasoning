from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class YahooQuote(BaseModel):
    ticker: str
    name: str = ""
    price: float = 0.0
    change: float = 0.0
    change_pct: float = 0.0
    volume: int = 0
    avg_volume: int = 0
    market_cap: float = 0.0
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    beta: Optional[float] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class YahooHistoricalPrice(BaseModel):
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    adj_close: Optional[float] = None


class YahooSectorPerformance(BaseModel):
    sector: str
    etf_ticker: str
    change_pct: float
    price: float = 0.0
    volume: int = 0


class YahooMarketSummary(BaseModel):
    top_gainers: List[YahooQuote] = Field(default_factory=list)
    top_losers: List[YahooQuote] = Field(default_factory=list)
    most_active: List[YahooQuote] = Field(default_factory=list)
    sector_performance: List[YahooSectorPerformance] = Field(default_factory=list)
    vix_level: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
