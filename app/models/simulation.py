from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.models.base import Entity


class ScenarioParameter(Entity):
    name: str
    value: Any
    type: str = "string"
    description: Optional[str] = None


class Scenario(Entity):
    name: str
    description: Optional[str] = None
    parameters: List[Dict[str, Any]] = Field(default_factory=list)
    assumptions: Dict[str, Any] = Field(default_factory=dict)
    event_ids: List[str] = Field(default_factory=list)
    status: str = "draft"


class ScenarioRun(Entity):
    scenario_id: str
    status: str = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    projected_impacts: List[Dict[str, Any]] = Field(default_factory=list)
    confidence_interval: Optional[Dict[str, float]] = None
    error: Optional[str] = None
    parameters_used: Dict[str, Any] = Field(default_factory=dict)


class SensitivityResult(Entity):
    scenario_id: str
    analysis_id: str
    parameters_analyzed: List[str] = Field(default_factory=list)
    top_drivers: List[Dict[str, Any]] = Field(default_factory=list)
    correlation_matrix: Dict[str, Any] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)
