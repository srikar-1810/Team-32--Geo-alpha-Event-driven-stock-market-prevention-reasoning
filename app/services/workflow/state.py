from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TypedDict
from uuid import uuid4


class AgentMemory(TypedDict, total=False):
    role: str
    content: str
    timestamp: str
    metadata: Dict[str, Any]


class AgentContext(TypedDict, total=False):
    agent_id: str
    agent_name: str
    status: str
    started_at: str
    completed_at: str
    output: Optional[Dict[str, Any]]
    error: Optional[str]
    memory: List[AgentMemory]
    execution_time_ms: float
    model_used: str
    fallback_used: bool
    tokens_used: int


class WorkflowState(TypedDict, total=False):
    # ── Input ──
    workflow_id: str
    query: str
    tickers: List[str]
    sectors: List[str]
    event_ids: List[str]
    location: str
    parameters: Dict[str, Any]

    # ── News Intelligence ──
    news_events: List[Dict[str, Any]]
    news_analysis: Optional[Dict[str, Any]]

    # ── Social Sentiment ──
    sentiment_posts: List[Dict[str, Any]]
    sentiment_analysis: Optional[Dict[str, Any]]

    # ── Historical RAG ──
    historical_analogues: List[Dict[str, Any]]
    historical_analysis: Optional[Dict[str, Any]]

    # ── Market Strategy ──
    sector_data: Dict[str, Any]
    stock_data: Dict[str, Any]
    market_analysis: Optional[Dict[str, Any]]

    # ── Risk Analysis ──
    risk_assessment: Optional[Dict[str, Any]]
    confidence_analysis: Optional[Dict[str, Any]]

    # ── Report ──
    report: Optional[Dict[str, Any]]

    # ── Agent Contexts (execution metadata) ──
    agent_contexts: Dict[str, AgentContext]

    # ── Workflow Metadata ──
    errors: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    started_at: str
    completed_at: Optional[str]
    total_execution_time_ms: float


def create_initial_state(
    query: str,
    tickers: Optional[List[str]] = None,
    sectors: Optional[List[str]] = None,
    location: str = "",
    event_ids: Optional[List[str]] = None,
    parameters: Optional[Dict[str, Any]] = None,
) -> WorkflowState:
    return {
        "workflow_id": f"wf-{uuid4().hex[:12]}",
        "query": query,
        "tickers": tickers or [],
        "sectors": sectors or [],
        "location": location,
        "event_ids": event_ids or [],
        "parameters": parameters or {},
        "news_events": [],
        "news_analysis": None,
        "sentiment_posts": [],
        "sentiment_analysis": None,
        "historical_analogues": [],
        "historical_analysis": None,
        "sector_data": {},
        "stock_data": {},
        "market_analysis": None,
        "risk_assessment": None,
        "confidence_analysis": None,
        "report": None,
        "agent_contexts": {},
        "errors": [],
        "warnings": [],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "total_execution_time_ms": 0.0,
    }
