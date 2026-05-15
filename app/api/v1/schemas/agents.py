from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentListResponse(BaseModel):
    id: str
    name: str
    agent_type: str
    status: str
    model: str


class AgentRunRequest(BaseModel):
    input_data: Dict[str, Any] = Field(default_factory=dict)
    parameters: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None


class AgentExecutionResponse(BaseModel):
    execution_id: str
    agent_id: str
    status: str
    input_params: Dict[str, Any]
    started_at: datetime
    output: Optional[Dict[str, Any]] = None


class AgentStatusResponse(BaseModel):
    agent_id: str
    status: str
    last_execution: Optional[datetime] = None
    uptime_hours: float
    tasks_completed: int
    error_count: int


class AgentConfigResponse(BaseModel):
    agent_id: str
    model: str
    temperature: float
    max_tokens: int
    tools: List[str]


class OrchestratorRunRequest(BaseModel):
    agents: List[str] = Field(..., min_length=1)
    input_data: Dict[str, Any]
    workflow_type: str = Field(default="sequential", pattern="^(sequential|parallel|conditional)$")
    parameters: Optional[Dict[str, Any]] = None


class OrchestratorRunResponse(BaseModel):
    orchestration_id: str
    status: str
    agents_invoked: List[str]
    started_at: datetime


# ── LangGraph Multi-Agent Workflow Schemas ────────────────────

class WorkflowRunRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000, description="Geopolitical event or query to analyze")
    tickers: List[str] = Field(default_factory=list, description="Stock tickers of interest")
    sectors: List[str] = Field(default_factory=list, description="Sectors of interest")
    location: str = Field(default="", description="Geographic location or region")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Additional workflow parameters")


class WorkflowAgentSummary(BaseModel):
    total: int = 0
    completed: int = 0
    failed: int = 0


class WorkflowAgentExecutionDetail(BaseModel):
    model_config = {"protected_namespaces": ()}
    status: str = ""
    execution_time_ms: float = 0.0
    model_used: str = ""
    fallback_used: bool = False
    tokens_used: int = 0


class WorkflowRunResponse(BaseModel):
    workflow_id: str
    status: str
    query: str
    tickers: List[str] = Field(default_factory=list)
    total_execution_time_ms: float = 0.0
    started_at: str = ""
    completed_at: str = ""
    agent_summary: WorkflowAgentSummary = Field(default_factory=WorkflowAgentSummary)
    analyses: Dict[str, Any] = Field(default_factory=dict)
    report: Optional[Dict[str, Any]] = None
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    agent_execution_details: Dict[str, WorkflowAgentExecutionDetail] = Field(default_factory=dict)
