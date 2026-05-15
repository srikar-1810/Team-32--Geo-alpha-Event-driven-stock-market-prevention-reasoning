from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.api.v1.schemas.simulation import (
    CreateScenarioRequest,
    CreateScenarioResponse,
    ScenarioDetailResponse,
    ScenarioListResponse,
    ScenarioResultResponse,
    SensitivityAnalysisRequest,
    SensitivityAnalysisResponse,
    RunSimulationRequest,
    RunSimulationResponse,
)
from app.api.v1.schemas.common import PaginatedResponse
from app.core.dependencies import get_db_session, get_simulation_engine
from app.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/run", response_model=RunSimulationResponse)
async def run_simulation(
    payload: RunSimulationRequest,
    engine=Depends(get_simulation_engine),
    db=Depends(get_db_session),
):
    """Run a full geopolitical simulation based on a query."""
    logger.info("Running simulation for query: %s", payload.query)
    result = await engine.run(payload.query)
    return result.to_dict()





@router.post("/scenarios", response_model=CreateScenarioResponse)
async def create_scenario(payload: CreateScenarioRequest, db=Depends(get_db_session)):
    return CreateScenarioResponse(
        scenario_id="scenario-new",
        name=payload.name,
        status="created",
        created_at=datetime.now(timezone.utc),
    )


@router.get("/scenarios", response_model=PaginatedResponse[ScenarioListResponse])
async def list_scenarios(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db=Depends(get_db_session),
):
    return PaginatedResponse(items=[], total=0, page=page, page_size=page_size)


@router.post("/scenarios/{scenario_id}/run", response_model=ScenarioResultResponse)
async def run_scenario(scenario_id: str, db=Depends(get_db_session)):
    return ScenarioResultResponse(
        scenario_id=scenario_id,
        run_id="run-new",
        status="running",
        started_at=datetime.now(timezone.utc),
        projected_impacts=[],
        confidence_interval=None,
    )


@router.get("/scenarios/{scenario_id}", response_model=ScenarioDetailResponse)
async def get_scenario(scenario_id: str, db=Depends(get_db_session)):
    return ScenarioDetailResponse(
        scenario_id=scenario_id,
        name="Example Scenario",
        description="Scenario description",
        assumptions={},
        parameters={},
        status="draft",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@router.post("/sensitivity", response_model=SensitivityAnalysisResponse)
async def sensitivity_analysis(payload: SensitivityAnalysisRequest, db=Depends(get_db_session)):
    return SensitivityAnalysisResponse(
        analysis_id="sens-new",
        parameters_analyzed=payload.parameters,
        top_drivers=[],
        correlation_matrix={},
        recommendations=[],
        generated_at=datetime.now(timezone.utc),
    )
