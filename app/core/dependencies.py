from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── RAG Service Dependencies ──────────────────────────────────

_rag_engine_instance = None
_historical_rag_instance = None


def get_rag_engine():
    global _rag_engine_instance
    if _rag_engine_instance is None:
        from app.services.rag.engine import RAGEngine
        _rag_engine_instance = RAGEngine()
    return _rag_engine_instance


def get_historical_rag():
    global _historical_rag_instance
    if _historical_rag_instance is None:
        from app.services.rag.historical_rag import HistoricalRAGService
        _historical_rag_instance = HistoricalRAGService()
    return _historical_rag_instance


async def get_chroma_client():
    from app.services.chroma.client import ChromaClient
    return ChromaClient()


async def get_embedding_service():
    from app.services.chroma.embeddings import EmbeddingService
    return EmbeddingService()


# ── Prediction Engine Dependency ─────────────────────────────

_prediction_engine_instance = None


def get_prediction_engine():
    global _prediction_engine_instance
    if _prediction_engine_instance is None:
        from app.services.prediction.predictor import PredictionEngine
        _prediction_engine_instance = PredictionEngine()
    return _prediction_engine_instance


# ── Workflow Orchestrator Dependency ─────────────────────────

_workflow_orchestrator_instance = None


def get_workflow_orchestrator():
    global _workflow_orchestrator_instance
    if _workflow_orchestrator_instance is None:
        from app.services.workflow.orchestrator import WorkflowOrchestrator
        _workflow_orchestrator_instance = WorkflowOrchestrator()
    return _workflow_orchestrator_instance

# ── Simulation Engine Dependency ──────────────────────────────

_simulation_engine_instance = None


def get_simulation_engine():
    global _simulation_engine_instance
    if _simulation_engine_instance is None:
        from app.services.simulation.engine import SimulationEngine
        _simulation_engine_instance = SimulationEngine()
    return _simulation_engine_instance
