from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter

from app.logging_config import get_logger
from app.services.ingestion.manager import ingestion_manager

logger = get_logger(__name__)
router = APIRouter()


@router.get("/status")
async def get_ingestion_status() -> Dict[str, Any]:
    return {
        "manager": ingestion_manager.status(),
        "scheduler": ingestion_manager.scheduler.status(),
        "gdelt": ingestion_manager.gdelt_ingestor.stats,
        "reddit": ingestion_manager.reddit_ingestor.stats,
        "market": ingestion_manager.market_ingestor.stats,
    }


@router.post("/trigger/all")
async def trigger_all_ingestion() -> Dict[str, Any]:
    results = await ingestion_manager.trigger_all()
    return {"status": "triggered", "results": results}


@router.post("/trigger/gdelt")
async def trigger_gdelt_ingestion() -> Dict[str, Any]:
    result = await ingestion_manager.trigger_gdelt()
    return {"status": "triggered", "result": result}


@router.post("/trigger/reddit")
async def trigger_reddit_ingestion() -> Dict[str, Any]:
    result = await ingestion_manager.trigger_reddit()
    return {"status": "triggered", "result": result}


@router.post("/trigger/market")
async def trigger_market_ingestion() -> Dict[str, Any]:
    result = await ingestion_manager.trigger_market()
    return {"status": "triggered", "result": result}


@router.post("/trigger/{source}")
async def trigger_source(source: str) -> Dict[str, Any]:
    result = await ingestion_manager.trigger_source(source)
    if result is None:
        return {"status": "error", "message": f"Unknown ingestion source: {source}"}
    return {"status": "triggered", "source": source, "result": result}


@router.get("/cache/stats")
async def get_cache_stats() -> Dict[str, Any]:
    try:
        gdelt_cache = await ingestion_manager.cache.get_cache_size("gdelt")
        reddit_cache = await ingestion_manager.cache.get_cache_size("reddit")
        market_cache = await ingestion_manager.cache.get_cache_size("tiingo")
        return {
            "gdelt_dedup_keys": gdelt_cache,
            "reddit_dedup_keys": reddit_cache,
            "market_dedup_keys": market_cache,
        }
    except Exception as e:
        return {"error": str(e), "available": False}
