from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SignalContributionSchema(BaseModel):
    signal_name: str
    direction: str
    contribution_score: float
    weight: float
    signal_strength: float
    confidence: float
    description: str


class ContributionBreakdownSchema(BaseModel):
    news_signal: SignalContributionSchema
    social_signal: SignalContributionSchema
    historical_signal: SignalContributionSchema
    momentum_signal: SignalContributionSchema
    volatility_signal: SignalContributionSchema


class ConfidenceDecompositionSchema(BaseModel):
    overall_confidence: float
    confidence_level: str
    signal_agreement: float
    data_quality_score: float
    historical_precedent_strength: float
    prediction_stability: float
    uncertainty_range: Dict[str, float]


class NaturalLanguageReasoningSchema(BaseModel):
    short_summary: str
    detailed_reasoning: str
    key_drivers: List[str]
    risk_factors: List[str]
    what_if_scenarios: List[str]


class SectorPredictionSchema(BaseModel):
    sector_name: str
    etf_ticker: str
    direction: str
    predicted_return_5d: float
    predicted_return_30d: float
    confidence: float
    confidence_decomposition: ConfidenceDecompositionSchema
    contributions: ContributionBreakdownSchema
    volatility_warning: str
    reasoning: NaturalLanguageReasoningSchema
    key_levels: List[float]


class StockPredictionSchema(BaseModel):
    ticker: str
    company_name: str
    sector: str
    direction: str
    predicted_return_5d: float
    predicted_return_30d: float
    confidence: float
    confidence_decomposition: ConfidenceDecompositionSchema
    contributions: ContributionBreakdownSchema
    volatility_warning: str
    reasoning: NaturalLanguageReasoningSchema
    price_targets: Dict[str, float]


class VolatilityWarningSchema(BaseModel):
    type: str
    name: str
    ticker: str
    warning: str
    reasoning: str


class PredictionRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000, description="Geopolitical event or market query")
    tickers: List[str] = Field(default_factory=list, description="Stock tickers to predict")
    sectors: List[str] = Field(default_factory=list, description="Sectors to predict")


class PredictionResponse(BaseModel):
    query: str
    tickers: List[str]
    sectors: List[str]
    generated_at: str
    execution_time_ms: float
    sector_predictions: List[SectorPredictionSchema] = Field(default_factory=list)
    stock_predictions: List[StockPredictionSchema] = Field(default_factory=list)
    top_bullish: List[Dict[str, Any]] = Field(default_factory=list)
    top_bearish: List[Dict[str, Any]] = Field(default_factory=list)
    high_volatility_warnings: List[VolatilityWarningSchema] = Field(default_factory=list)
    overall_market_outlook: str = ""
    overall_confidence: float = 0.0


class PredictionExplainRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000)
    ticker: str = Field(..., min_length=1, max_length=10)


class PredictionExplainResponse(BaseModel):
    ticker: str
    contributions: ContributionBreakdownSchema
    confidence_decomposition: ConfidenceDecompositionSchema
    reasoning: NaturalLanguageReasoningSchema
    volatility_warning: str
