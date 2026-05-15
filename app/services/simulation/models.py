from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class ScenarioDirection(str, Enum):
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
    IMMEDIATE = "immediate"
    SHORT_TERM = "short_term"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"


class SupplyChainImpactSeverity(str, Enum):
    CRITICAL = "critical"
    SEVERE = "severe"
    MODERATE = "moderate"
    MINOR = "minor"
    NONE = "none"


@dataclass
class ParsedScenario:
    event_type: str
    title: str
    description: str
    location: str
    countries: List[str]
    actors: List[str]
    severity_estimate: float
    estimated_timeline: str
    economic_scope: str
    uncertainty_factors: List[str]
    original_query: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "countries": self.countries,
            "actors": self.actors,
            "severity_estimate": self.severity_estimate,
            "estimated_timeline": self.estimated_timeline,
            "economic_scope": self.economic_scope,
            "uncertainty_factors": self.uncertainty_factors,
        }


@dataclass
class InferredStock:
    ticker: str
    company_name: str
    sector: str
    etf_ticker: str
    relevance_score: float
    exposure_type: str
    reasoning: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "sector": self.sector,
            "etf_ticker": self.etf_ticker,
            "relevance_score": round(self.relevance_score, 4),
            "exposure_type": self.exposure_type,
            "reasoning": self.reasoning,
        }


@dataclass
class InferredSector:
    sector_name: str
    etf_ticker: str
    impact_direction: str
    impact_magnitude: float
    confidence: float
    reasoning: str
    stocks: List[InferredStock] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sector_name": self.sector_name,
            "etf_ticker": self.etf_ticker,
            "impact_direction": self.impact_direction,
            "impact_magnitude": round(self.impact_magnitude, 4),
            "confidence": round(self.confidence, 4),
            "reasoning": self.reasoning,
            "stocks": [s.to_dict() for s in self.stocks],
        }


@dataclass
class SupplyChainImpact:
    node: str
    impact_severity: SupplyChainImpactSeverity
    description: str
    affected_companies: List[str]
    estimated_disruption_days: int
    geographic_spread: List[str]
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": self.node,
            "impact_severity": self.impact_severity.value,
            "description": self.description,
            "affected_companies": self.affected_companies,
            "estimated_disruption_days": self.estimated_disruption_days,
            "geographic_spread": self.geographic_spread,
            "confidence": round(self.confidence, 4),
        }


@dataclass
class AnalogicalMatch:
    event_title: str
    event_date: str
    event_type: str
    similarity_score: float
    key_similarities: List[str]
    key_differences: List[str]
    market_impact_description: str
    sectors_affected: List[str]
    return_5d: float
    return_30d: float
    volatility_change: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_title": self.event_title,
            "event_date": self.event_date,
            "event_type": self.event_type,
            "similarity_score": round(self.similarity_score, 4),
            "key_similarities": self.key_similarities,
            "key_differences": self.key_differences,
            "market_impact_description": self.market_impact_description,
            "sectors_affected": self.sectors_affected,
            "return_5d": round(self.return_5d, 2),
            "return_30d": round(self.return_30d, 2),
            "volatility_change": round(self.volatility_change, 2),
        }


@dataclass
class RiskFactor:
    risk_factor: str
    severity: float
    probability: float
    impact_description: str
    scenario_amplification: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_factor": self.risk_factor,
            "severity": round(self.severity, 4),
            "probability": round(self.probability, 4),
            "impact_description": self.impact_description,
            "scenario_amplification": self.scenario_amplification,
        }


@dataclass
class VolatilityOutlook:
    expected_regime: str
    vix_implication: str
    sector_divergences: List[str]
    estimated_vol_expansion: float
    tail_risk_assessment: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "expected_regime": self.expected_regime,
            "vix_implication": self.vix_implication,
            "sector_divergences": self.sector_divergences,
            "estimated_vol_expansion": round(self.estimated_vol_expansion, 4),
            "tail_risk_assessment": self.tail_risk_assessment,
        }


@dataclass
class OutcomeScenario:
    scenario_label: str
    probability: float
    direction: ScenarioDirection
    market_return_5d: float
    market_return_30d: float
    sector_impacts: List[Dict[str, Any]]
    narrative: str
    key_catalysts: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_label": self.scenario_label,
            "probability": round(self.probability, 4),
            "direction": self.direction.value,
            "market_return_5d": round(self.market_return_5d, 2),
            "market_return_30d": round(self.market_return_30d, 2),
            "sector_impacts": self.sector_impacts,
            "narrative": self.narrative,
            "key_catalysts": self.key_catalysts,
        }


@dataclass
class SimulationReport:
    title: str
    executive_summary: str
    scenario_context: str
    key_judgments: List[Dict[str, Any]]
    sector_analysis: str
    stock_picks: List[Dict[str, Any]]
    supply_chain_risks: str
    historical_context: str
    risk_assessment: str
    outcome_scenarios: str
    recommendations: List[str]
    confidence_assessment: str
    disclaimers: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "executive_summary": self.executive_summary,
            "scenario_context": self.scenario_context,
            "key_judgments": self.key_judgments,
            "sector_analysis": self.sector_analysis,
            "stock_picks": self.stock_picks,
            "supply_chain_risks": self.supply_chain_risks,
            "historical_context": self.historical_context,
            "risk_assessment": self.risk_assessment,
            "outcome_scenarios": self.outcome_scenarios,
            "recommendations": self.recommendations,
            "confidence_assessment": self.confidence_assessment,
            "disclaimers": self.disclaimers,
        }


@dataclass
class SimulationResult:
    simulation_id: str
    query: str
    created_at: str
    execution_time_ms: float

    parsed_scenario: ParsedScenario
    sectors: List[InferredSector]
    stocks: List[InferredStock]
    supply_chain_impacts: List[SupplyChainImpact]
    analogies: List[AnalogicalMatch]
    risk_factors: List[RiskFactor]
    volatility_outlook: VolatilityOutlook
    outcomes: List[OutcomeScenario]
    report: SimulationReport

    top_bullish: List[Dict[str, Any]] = field(default_factory=list)
    top_bearish: List[Dict[str, Any]] = field(default_factory=list)
    overall_confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "query": self.query,
            "created_at": self.created_at,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "parsed_scenario": self.parsed_scenario.to_dict(),
            "sectors": [s.to_dict() for s in self.sectors],
            "stocks": [s.to_dict() for s in self.stocks],
            "supply_chain_impacts": [s.to_dict() for s in self.supply_chain_impacts],
            "analogies": [a.to_dict() for a in self.analogies],
            "risk_factors": [r.to_dict() for r in self.risk_factors],
            "volatility_outlook": self.volatility_outlook.to_dict(),
            "outcomes": [o.to_dict() for o in self.outcomes],
            "report": self.report.to_dict(),
            "top_bullish": self.top_bullish,
            "top_bearish": self.top_bearish,
            "overall_confidence": round(self.overall_confidence, 4),
        }
