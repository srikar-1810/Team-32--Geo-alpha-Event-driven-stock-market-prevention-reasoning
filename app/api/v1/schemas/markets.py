from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class MarketQueryParams(BaseModel):
    tickers: str = Field(..., description="Comma-separated ticker symbols")
    start_date: date
    end_date: date
    frequency: str = Field(default="daily", pattern="^(daily|weekly|monthly)$")


class MarketDataPoint(BaseModel):
    ticker: str
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    adj_close: Optional[float] = None
    change_pct: Optional[float] = None


class SectorImpact(BaseModel):
    sector: str
    impact_score: float = Field(..., ge=-1.0, le=1.0)
    affected_tickers: List[str]
    reasoning: str


class MarketImpactResponse(BaseModel):
    event_id: str
    overall_impact_score: float
    affected_sectors: List[SectorImpact]
    top_impacted_stocks: List[dict]
    volatility_forecast: List[dict]
    confidence: float
    generated_at: datetime


class SectorPerformanceResponse(BaseModel):
    sector: str
    daily_change_pct: float
    weekly_change_pct: float
    monthly_change_pct: float
    ytd_change_pct: float
    volume_change_pct: float
    top_gainers: List[str]
    top_losers: List[str]


class PortfolioHolding(BaseModel):
    ticker: str
    name: str
    shares: int
    avg_cost: float


class PortfolioImpactRequest(BaseModel):
    portfolio_id: str
    holdings: List[PortfolioHolding]


class HoldingImpact(BaseModel):
    ticker: str
    current_price: float
    change_pct: float
    impact_score: float
    recommendation: str


class PortfolioImpactResponse(BaseModel):
    portfolio_id: str
    overall_risk_score: float
    holdings_impact: List[HoldingImpact]
    recommended_actions: List[str]
    assessed_at: datetime


class BacktestRequest(BaseModel):
    strategy: str = Field(..., description="Strategy name")
    tickers: List[str]
    start_date: date
    end_date: date
    initial_capital: float = Field(default=100000.0, gt=0)
    parameters: Optional[dict] = None


class BacktestResultPoint(BaseModel):
    date: date
    portfolio_value: float
    benchmark_value: float
    daily_return: float
    cumulative_return: float


class BacktestResponse(BaseModel):
    backtest_id: str
    strategy: str
    tickers: List[str]
    start_date: date
    end_date: date
    initial_capital: float
    final_value: float
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown: float
    results: List[BacktestResultPoint]
    completed_at: datetime
