from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    agents,
    backtest,
    geopol,
    health,
    ingestion,
    markets,
    prediction,
    rag,
    reports,
    sentiment,
    simulation,
)

v1_router = APIRouter()

v1_router.include_router(health.router, prefix="/health", tags=["Health"])
v1_router.include_router(geopol.router, prefix="/geopol", tags=["Geopolitical Events"])
v1_router.include_router(sentiment.router, prefix="/sentiment", tags=["Sentiment Analysis"])
v1_router.include_router(markets.router, prefix="/markets", tags=["Market Data"])
v1_router.include_router(rag.router, prefix="/rag", tags=["RAG Retrieval"])
v1_router.include_router(agents.router, prefix="/agents", tags=["AI Agents"])
v1_router.include_router(reports.router, prefix="/reports", tags=["Report Generation"])
v1_router.include_router(simulation.router, prefix="/simulation", tags=["Scenario Simulation"])
v1_router.include_router(backtest.router, prefix="/backtest", tags=["Backtesting"])
v1_router.include_router(ingestion.router, prefix="/ingestion", tags=["Data Ingestion"])
v1_router.include_router(prediction.router, prefix="/prediction", tags=["Market Prediction"])
