from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class PredictionDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class ConfidenceLevel(str, Enum):
    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"


class TimeHorizon(str, Enum):
    SHORT_TERM = "short_term"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"


class VolatilityWarning(str, Enum):
    EXTREME = "extreme"
    HIGH = "high"
    ELEVATED = "elevated"
    NORMAL = "normal"
    LOW = "low"


@dataclass
class SignalContribution:
    signal_name: str
    direction: PredictionDirection
    contribution_score: float
    weight: float
    signal_strength: float
    confidence: float
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_name": self.signal_name,
            "direction": self.direction.value,
            "contribution_score": round(self.contribution_score, 4),
            "weight": round(self.weight, 4),
            "signal_strength": round(self.signal_strength, 4),
            "confidence": round(self.confidence, 4),
            "description": self.description,
        }


@dataclass
class ContributionBreakdown:
    news_signal: SignalContribution = field(default_factory=lambda: SignalContribution("news", PredictionDirection.NEUTRAL, 0.0, 0.25, 0.0, 0.0, ""))
    social_signal: SignalContribution = field(default_factory=lambda: SignalContribution("social_sentiment", PredictionDirection.NEUTRAL, 0.0, 0.20, 0.0, 0.0, ""))
    historical_signal: SignalContribution = field(default_factory=lambda: SignalContribution("historical_analogy", PredictionDirection.NEUTRAL, 0.0, 0.20, 0.0, 0.0, ""))
    momentum_signal: SignalContribution = field(default_factory=lambda: SignalContribution("market_momentum", PredictionDirection.NEUTRAL, 0.0, 0.15, 0.0, 0.0, ""))
    volatility_signal: SignalContribution = field(default_factory=lambda: SignalContribution("volatility_regime", PredictionDirection.NEUTRAL, 0.0, 0.20, 0.0, 0.0, ""))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "news_signal": self.news_signal.to_dict(),
            "social_signal": self.social_signal.to_dict(),
            "historical_signal": self.historical_signal.to_dict(),
            "momentum_signal": self.momentum_signal.to_dict(),
            "volatility_signal": self.volatility_signal.to_dict(),
        }

    def get_all_signals(self) -> List[SignalContribution]:
        return [self.news_signal, self.social_signal, self.historical_signal, self.momentum_signal, self.volatility_signal]

    def net_score(self) -> float:
        return sum(s.contribution_score for s in self.get_all_signals())


@dataclass
class ConfidenceDecomposition:
    overall_confidence: float
    confidence_level: ConfidenceLevel
    signal_agreement: float
    data_quality_score: float
    historical_precedent_strength: float
    prediction_stability: float
    uncertainty_range: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_confidence": round(self.overall_confidence, 4),
            "confidence_level": self.confidence_level.value,
            "signal_agreement": round(self.signal_agreement, 4),
            "data_quality_score": round(self.data_quality_score, 4),
            "historical_precedent_strength": round(self.historical_precedent_strength, 4),
            "prediction_stability": round(self.prediction_stability, 4),
            "uncertainty_range": {k: round(v, 4) for k, v in self.uncertainty_range.items()},
        }


@dataclass
class NaturalLanguageReasoning:
    short_summary: str
    detailed_reasoning: str
    key_drivers: List[str]
    risk_factors: List[str]
    what_if_scenarios: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "short_summary": self.short_summary,
            "detailed_reasoning": self.detailed_reasoning,
            "key_drivers": self.key_drivers,
            "risk_factors": self.risk_factors,
            "what_if_scenarios": self.what_if_scenarios,
        }


@dataclass
class SectorPrediction:
    sector_name: str
    etf_ticker: str
    direction: PredictionDirection
    predicted_return_5d: float
    predicted_return_30d: float
    confidence: float
    confidence_decomposition: ConfidenceDecomposition
    contributions: ContributionBreakdown
    volatility_warning: VolatilityWarning
    reasoning: NaturalLanguageReasoning
    key_levels: List[float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sector_name": self.sector_name,
            "etf_ticker": self.etf_ticker,
            "direction": self.direction.value,
            "predicted_return_5d": round(self.predicted_return_5d, 2),
            "predicted_return_30d": round(self.predicted_return_30d, 2),
            "confidence": round(self.confidence, 4),
            "confidence_decomposition": self.confidence_decomposition.to_dict(),
            "contributions": self.contributions.to_dict(),
            "volatility_warning": self.volatility_warning.value,
            "reasoning": self.reasoning.to_dict(),
            "key_levels": [round(k, 2) for k in self.key_levels],
        }


@dataclass
class StockPrediction:
    ticker: str
    company_name: str
    sector: str
    direction: PredictionDirection
    predicted_return_5d: float
    predicted_return_30d: float
    confidence: float
    confidence_decomposition: ConfidenceDecomposition
    contributions: ContributionBreakdown
    volatility_warning: VolatilityWarning
    reasoning: NaturalLanguageReasoning
    price_targets: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "sector": self.sector,
            "direction": self.direction.value,
            "predicted_return_5d": round(self.predicted_return_5d, 2),
            "predicted_return_30d": round(self.predicted_return_30d, 2),
            "confidence": round(self.confidence, 4),
            "confidence_decomposition": self.confidence_decomposition.to_dict(),
            "contributions": self.contributions.to_dict(),
            "volatility_warning": self.volatility_warning.value,
            "reasoning": self.reasoning.to_dict(),
            "price_targets": {k: round(v, 2) for k, v in self.price_targets.items()},
        }


@dataclass
class PredictionResult:
    query: str
    tickers: List[str]
    sectors: List[str]
    generated_at: str
    execution_time_ms: float
    sector_predictions: List[SectorPrediction] = field(default_factory=list)
    stock_predictions: List[StockPrediction] = field(default_factory=list)
    top_bullish: List[Dict[str, Any]] = field(default_factory=list)
    top_bearish: List[Dict[str, Any]] = field(default_factory=list)
    high_volatility_warnings: List[Dict[str, Any]] = field(default_factory=list)
    overall_market_outlook: str = ""
    overall_confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "tickers": self.tickers,
            "sectors": self.sectors,
            "generated_at": self.generated_at,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "sector_predictions": [s.to_dict() for s in self.sector_predictions],
            "stock_predictions": [s.to_dict() for s in self.stock_predictions],
            "top_bullish": self.top_bullish,
            "top_bearish": self.top_bearish,
            "high_volatility_warnings": self.high_volatility_warnings,
            "overall_market_outlook": self.overall_market_outlook,
            "overall_confidence": round(self.overall_confidence, 4),
        }
