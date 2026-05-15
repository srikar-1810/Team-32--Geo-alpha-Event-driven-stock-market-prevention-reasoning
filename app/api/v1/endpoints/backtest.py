from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.api.v1.schemas.markets import BacktestRequest, BacktestResponse, BacktestResultPoint
from app.api.v1.schemas.common import PaginatedResponse
from app.core.dependencies import get_db_session
from app.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/run", response_model=BacktestResponse)
async def run_backtest(payload: BacktestRequest, db=Depends(get_db_session)):
    return BacktestResponse(
        backtest_id="bt-new",
        strategy=payload.strategy,
        tickers=payload.tickers,
        start_date=payload.start_date,
        end_date=payload.end_date,
        initial_capital=payload.initial_capital,
        final_value=0.0,
        total_return_pct=0.0,
        sharpe_ratio=0.0,
        max_drawdown=0.0,
        results=[],
        completed_at=datetime.now(timezone.utc),
    )


@router.get("/history", response_model=PaginatedResponse[BacktestResponse])
async def list_backtests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db=Depends(get_db_session),
):
    return PaginatedResponse(items=[], total=0, page=page, page_size=page_size)


@router.get("/{backtest_id}", response_model=BacktestResponse)
async def get_backtest(backtest_id: str, db=Depends(get_db_session)):
    return BacktestResponse(
        backtest_id=backtest_id,
        strategy="example",
        tickers=[],
        start_date=datetime.now(timezone.utc).date(),
        end_date=datetime.now(timezone.utc).date(),
        initial_capital=100000.0,
        final_value=100000.0,
        total_return_pct=0.0,
        sharpe_ratio=0.0,
        max_drawdown=0.0,
        results=[],
        completed_at=datetime.now(timezone.utc),
    )
