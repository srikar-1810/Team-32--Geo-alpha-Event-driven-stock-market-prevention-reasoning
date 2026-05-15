from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.v1.schemas.agents import (
    AgentConfigResponse,
    AgentExecutionResponse,
    AgentListResponse,
    AgentRunRequest,
    AgentStatusResponse,
    OrchestratorRunRequest,
    OrchestratorRunResponse,
    WorkflowRunRequest,
    WorkflowRunResponse,
)
from app.core.dependencies import get_db_session, get_workflow_orchestrator
from app.logging_config import get_logger
from app.services.workflow.orchestrator import WorkflowOrchestrator

logger = get_logger(__name__)
router = APIRouter()

AGENTS_REGISTRY = [
    {"id": "news-intelligence", "name": "News Intelligence Agent", "type": "workflow", "model": "gpt-4o"},
    {"id": "social-sentiment", "name": "Social Sentiment Agent", "type": "workflow", "model": "gpt-4o"},
    {"id": "historical-analyst", "name": "Historical RAG Analyst Agent", "type": "workflow", "model": "gpt-4o"},
    {"id": "market-strategist", "name": "Market Strategist Agent", "type": "workflow", "model": "gpt-4o"},
    {"id": "risk-analysis", "name": "Risk Analysis Agent", "type": "workflow", "model": "gpt-4o"},
    {"id": "report-generation", "name": "Report Generation Agent", "type": "workflow", "model": "gpt-4o"},
]


@router.get("", response_model=List[AgentListResponse])
async def list_agents(db=Depends(get_db_session)):
    return [
        AgentListResponse(
            id=a["id"],
            name=a["name"],
            agent_type=a["type"],
            status="idle",
            model=a["model"],
        )
        for a in AGENTS_REGISTRY
    ]


@router.post("/run/{agent_id}", response_model=AgentExecutionResponse)
async def run_agent(agent_id: str, payload: AgentRunRequest, db=Depends(get_db_session)):
    agent_ids = {a["id"] for a in AGENTS_REGISTRY}
    if agent_id not in agent_ids:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_id}")
    return AgentExecutionResponse(
        execution_id=f"exec-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        agent_id=agent_id,
        status="started",
        input_params=payload.model_dump(),
        started_at=datetime.now(timezone.utc),
    )


@router.get("/status/{agent_id}", response_model=AgentStatusResponse)
async def get_agent_status(agent_id: str, db=Depends(get_db_session)):
    agent_ids = {a["id"] for a in AGENTS_REGISTRY}
    if agent_id not in agent_ids:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_id}")
    return AgentStatusResponse(
        agent_id=agent_id,
        status="idle",
        last_execution=None,
        uptime_hours=0.0,
        tasks_completed=0,
        error_count=0,
    )


@router.get("/config/{agent_id}", response_model=AgentConfigResponse)
async def get_agent_config(agent_id: str, db=Depends(get_db_session)):
    agent_ids = {a["id"] for a in AGENTS_REGISTRY}
    if agent_id not in agent_ids:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_id}")
    return AgentConfigResponse(
        agent_id=agent_id,
        model="gpt-4o",
        temperature=0.1,
        max_tokens=4096,
        tools=["gdelt", "reddit", "chromadb", "tiingo", "yahoo", "historical_rag"],
    )


@router.post("/orchestrate", response_model=OrchestratorRunResponse)
async def run_orchestrator(payload: OrchestratorRunRequest, db=Depends(get_db_session)):
    return OrchestratorRunResponse(
        orchestration_id=f"orch-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        status="started",
        agents_invoked=payload.agents,
        started_at=datetime.now(timezone.utc),
    )


# ═══════════════════════════════════════════════════════════════
# LangGraph Multi-Agent Workflow Endpoints
# ═══════════════════════════════════════════════════════════════

@router.post("/workflow", response_model=WorkflowRunResponse)
async def run_full_workflow(
    payload: WorkflowRunRequest,
    orchestrator: WorkflowOrchestrator = Depends(get_workflow_orchestrator),
):
    """Run the complete 6-agent intelligence pipeline using LangGraph."""
    try:
        result = await orchestrator.run_full_analysis(
            query=payload.query,
            tickers=payload.tickers,
            sectors=payload.sectors,
            location=payload.location,
            parameters=payload.parameters,
        )

        agent_summary = result.get("agent_summary", {})
        exec_details_raw = result.get("agent_execution_details", {})

        return WorkflowRunResponse(
            workflow_id=result.get("workflow_id", ""),
            status=result.get("status", "completed"),
            query=result.get("query", payload.query),
            tickers=result.get("tickers", payload.tickers),
            total_execution_time_ms=result.get("total_execution_time_ms", 0),
            started_at=result.get("started_at", ""),
            completed_at=result.get("completed_at", ""),
            agent_summary={
                "total": agent_summary.get("total", 0),
                "completed": agent_summary.get("completed", 0),
                "failed": agent_summary.get("failed", 0),
            },
            analyses=result.get("analyses", {}),
            report=result.get("report"),
            errors=result.get("errors", []),
            agent_execution_details=exec_details_raw,
        )
    except Exception as e:
        logger.error("Workflow execution failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflow/agents", response_model=List[str])
async def list_workflow_agents():
    """List the agent sequence in the LangGraph workflow."""
    from app.services.workflow.graph import AGENT_SEQUENCE
    return list(AGENT_SEQUENCE)
