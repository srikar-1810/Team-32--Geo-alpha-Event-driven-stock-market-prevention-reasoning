from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ScenarioParameter(BaseModel):
    name: str
    value: Any
    type: str = Field(default="string")
    description: Optional[str] = None


class CreateScenarioRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    parameters: List[ScenarioParameter] = Field(default_factory=list)
    assumptions: Optional[Dict[str, Any]] = None
    event_ids: List[str] = Field(default_factory=list)


class CreateScenarioResponse(BaseModel):
    scenario_id: str
    name: str
    status: str
    created_at: datetime


class ScenarioListResponse(BaseModel):
    scenario_id: str
    name: str
    status: str
    created_at: datetime


class ScenarioDetailResponse(BaseModel):
    scenario_id: str
    name: str
    description: Optional[str] = None
    assumptions: Optional[Dict[str, Any]] = None
    parameters: List[ScenarioParameter]
    status: str
    created_at: datetime
    updated_at: datetime


class ProjectedImpact(BaseModel):
    sector: str
    ticker: str
    projected_change_pct: float
    confidence: float
    time_horizon: str
    reasoning: str


class ScenarioResultResponse(BaseModel):
    scenario_id: str
    run_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    projected_impacts: List[ProjectedImpact]
    confidence_interval: Optional[Dict[str, float]] = None


class SensitivityAnalysisRequest(BaseModel):
    scenario_id: str
    parameters: List[str] = Field(..., min_length=1)
    ranges: Dict[str, List[float]]
    iterations: int = Field(default=100, ge=10, le=10000)


class SensitivityAnalysisResponse(BaseModel):
    analysis_id: str
    parameters_analyzed: List[str]
    top_drivers: List[dict]
    correlation_matrix: Dict[str, Any]
    recommendations: List[str]
class RunSimulationRequest(BaseModel):
    query: str = Field(..., min_length=5, max_length=1000)


class RunSimulationResponse(BaseModel):
    execution_time_ms: float
    overall_confidence: float
    parsed_scenario: Dict[str, Any]
    sectors: List[Dict[str, Any]]
    top_bullish: List[Dict[str, Any]]
    top_bearish: List[Dict[str, Any]]
    supply_chain_impacts: List[Dict[str, Any]]
    analogies: List[Dict[str, Any]]
    outcomes: List[Dict[str, Any]]
    risk_factors: List[Dict[str, Any]]
    volatility_outlook: Dict[str, Any]
    report: Dict[str, Any]
