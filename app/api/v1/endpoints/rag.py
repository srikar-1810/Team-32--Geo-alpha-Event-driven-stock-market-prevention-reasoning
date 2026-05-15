from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.v1.schemas.rag import (
    HistoricalRAGCollectionStatsResponse,
    HistoricalRAGEventQueryRequest,
    HistoricalRAGEvaluationRequest,
    HistoricalRAGEvaluationResponse,
    HistoricalRAGFilterQueryRequest,
    HistoricalRAGIndexResponse,
    HistoricalRAGMarketReactions,
    HistoricalRAGQueryRequest,
    HistoricalRAGQueryResponse,
    HistoricalRAGSimilarityResult,
    RAGCollectionStats,
    RAGIndexDocumentRequest,
    RAGIndexDocumentResponse,
    RAGQueryRequest,
    RAGQueryResponse,
    RAGResultItem,
)
from app.core.dependencies import get_db_session, get_historical_rag, get_rag_engine
from app.logging_config import get_logger
from app.services.rag.engine import RAGEngine
from app.services.rag.evaluation import RetrievalEvaluator
from app.services.rag.historical_rag import HistoricalRAGService

logger = get_logger(__name__)
router = APIRouter()


# ═══════════════════════════════════════════════════════════════
# General RAG Endpoints
# ═══════════════════════════════════════════════════════════════

@router.post("/query", response_model=RAGQueryResponse)
async def query_rag(
    payload: RAGQueryRequest,
    rag: RAGEngine = Depends(get_rag_engine),
    db=Depends(get_db_session),
):
    start = time.perf_counter()
    try:
        result = await rag.query(
            query_text=payload.query,
            collections=[payload.collection] if payload.collection else None,
            top_k=payload.top_k,
            filters=payload.filters,
        )
        elapsed = (time.perf_counter() - start) * 1000

        results = []
        for r in result.get("results", []):
            results.append(RAGResultItem(
                id=r.get("id", ""),
                score=r.get("score", 0.0),
                content=r.get("content", ""),
                metadata=r.get("metadata", {}),
                collection=r.get("collection", payload.collection),
            ))

        return RAGQueryResponse(
            query=payload.query,
            answer=result.get("answer", ""),
            results=results,
            total_results=len(results),
            processing_time_ms=round(elapsed, 2),
            model_used=result.get("model_used", ""),
        )
    except Exception as e:
        logger.error("RAG query failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index", response_model=RAGIndexDocumentResponse)
async def index_document(
    payload: RAGIndexDocumentRequest,
    rag: HistoricalRAGService = Depends(get_historical_rag),
    db=Depends(get_db_session),
):
    from uuid import uuid4
    doc_id = str(uuid4())
    try:
        embedding = await rag.embeddings.embed_text(payload.content)
        await rag.chroma.add_documents(
            collection_name=payload.collection,
            ids=[doc_id],
            documents=[payload.content],
            metadatas=[payload.metadata],
            embeddings=[embedding],
        )
        return RAGIndexDocumentResponse(
            document_id=doc_id,
            collection=payload.collection,
            chunk_count=1,
            indexed_at=datetime.now(timezone.utc),
        )
    except Exception as e:
        logger.error("Indexing failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collections", response_model=List[RAGCollectionStats])
async def list_collections(
    rag: HistoricalRAGService = Depends(get_historical_rag),
    db=Depends(get_db_session),
):
    try:
        raw_collections = await rag.chroma.list_collections()
        stats = []
        for coll in raw_collections:
            count = await rag.chroma.count(coll["name"])
            stats.append(RAGCollectionStats(
                name=coll["name"],
                document_count=count,
                embedding_dimension=rag.embeddings.get_dimension(),
                created_at=str(coll.get("metadata", {}).get("created_at", "")),
            ))
        return stats
    except Exception as e:
        logger.error("List collections failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/collections/{collection_name}")
async def clear_collection(
    collection_name: str,
    rag: HistoricalRAGService = Depends(get_historical_rag),
    db=Depends(get_db_session),
):
    try:
        await rag.chroma.delete_collection(collection_name)
        return {"status": "ok", "collection": collection_name, "cleared": True}
    except Exception as e:
        logger.error("Clear collection failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════
# Historical RAG Endpoints
# ═══════════════════════════════════════════════════════════════

@router.post("/historical/query", response_model=HistoricalRAGQueryResponse)
async def query_historical(
    payload: HistoricalRAGQueryRequest,
    rag: HistoricalRAGService = Depends(get_historical_rag),
):
    start = time.perf_counter()
    try:
        results = await rag.retrieve_similar(
            query_text=payload.query,
            top_k=payload.top_k,
            filters=payload.filters,
            min_similarity=payload.min_similarity,
        )

        processed = []
        for r in results:
            meta = r.get("metadata", {})
            confidence = (
                rag.compute_confidence(r["similarity"], meta)
                if payload.include_confidence else {}
            )
            processed.append(HistoricalRAGSimilarityResult(
                event_id=r["event_id"],
                event_title=meta.get("event_title", ""),
                event_type=meta.get("event_type", ""),
                location=meta.get("location", ""),
                event_date=meta.get("event_date", ""),
                similarity=r["similarity"],
                distance=r.get("distance", 0.0),
                severity=meta.get("severity", 0.0),
                data_quality=meta.get("data_quality", "medium"),
                sectors=meta.get("sectors", ""),
                bullish_tickers=meta.get("bullish_tickers", ""),
                bearish_tickers=meta.get("bearish_tickers", ""),
                impact_summary=meta.get("impact_summary", ""),
                confidence=confidence,
            ))

        market_reactions = None
        if payload.include_market_reactions:
            reactions = rag.extract_market_reactions(results)
            market_reactions = HistoricalRAGMarketReactions(
                avg_volatility_change_pct=reactions["avg_volatility_change_pct"],
                avg_market_return_5d=reactions["avg_market_return_5d"],
                avg_market_return_30d=reactions["avg_market_return_30d"],
                sectors_by_impact=reactions["sectors_by_impact"],
                most_common_bullish=reactions["most_common_bullish"],
                most_common_bearish=reactions["most_common_bearish"],
                total_events_analyzed=reactions["total_events_analyzed"],
            )

        elapsed = (time.perf_counter() - start) * 1000
        return HistoricalRAGQueryResponse(
            query=payload.query,
            total_results=len(processed),
            processing_time_ms=round(elapsed, 2),
            results=processed,
            market_reactions=market_reactions,
        )
    except Exception as e:
        logger.error("Historical RAG query failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/historical/query-by-event", response_model=HistoricalRAGQueryResponse)
async def query_historical_by_event(
    payload: HistoricalRAGEventQueryRequest,
    rag: HistoricalRAGService = Depends(get_historical_rag),
):
    """Find historical analogues for a specific event by its event_id."""
    start = time.perf_counter()
    try:
        results = await rag.retrieve_by_filters(
            top_k=1,
            event_type=None,
        )

        target_event = None
        for r in results:
            if r.get("event_id") == payload.event_id:
                target_event = r
                break

        if not target_event:
            raise HTTPException(
                status_code=404,
                detail=f"Event {payload.event_id} not found in vector index",
            )

        from app.services.historical.models import HistoricalMarketImpact
        event_obj = HistoricalMarketImpact(event_id=payload.event_id)
        meta = target_event.get("metadata", {})
        for field in ["event_title", "event_type", "location", "severity", "confidence"]:
            if field in meta:
                setattr(event_obj, field, meta[field])

        analogues = await rag.retrieve_by_event(
            event=event_obj,
            top_k=payload.top_k,
            exclude_self=payload.exclude_self,
        )

        processed = []
        for r in analogues:
            m = r.get("metadata", {})
            processed.append(HistoricalRAGSimilarityResult(
                event_id=r["event_id"],
                event_title=m.get("event_title", ""),
                event_type=m.get("event_type", ""),
                location=m.get("location", ""),
                event_date=m.get("event_date", ""),
                similarity=r["similarity"],
                severity=m.get("severity", 0.0),
                sectors=m.get("sectors", ""),
                bullish_tickers=m.get("bullish_tickers", ""),
                bearish_tickers=m.get("bearish_tickers", ""),
                impact_summary=m.get("impact_summary", ""),
                confidence=rag.compute_confidence(r["similarity"], m),
            ))

        reactions = rag.extract_market_reactions(analogues)
        elapsed = (time.perf_counter() - start) * 1000
        return HistoricalRAGQueryResponse(
            query=f"analogues for event {payload.event_id}",
            total_results=len(processed),
            processing_time_ms=round(elapsed, 2),
            results=processed,
            market_reactions=HistoricalRAGMarketReactions(
                avg_volatility_change_pct=reactions["avg_volatility_change_pct"],
                avg_market_return_5d=reactions["avg_market_return_5d"],
                avg_market_return_30d=reactions["avg_market_return_30d"],
                sectors_by_impact=reactions["sectors_by_impact"],
                most_common_bullish=reactions["most_common_bullish"],
                most_common_bearish=reactions["most_common_bearish"],
                total_events_analyzed=reactions["total_events_analyzed"],
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Historical RAG by-event query failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/historical/filter", response_model=HistoricalRAGQueryResponse)
async def query_historical_filtered(
    payload: HistoricalRAGFilterQueryRequest,
    rag: HistoricalRAGService = Depends(get_historical_rag),
):
    """Retrieve historical events by structured filters."""
    start = time.perf_counter()
    try:
        results = await rag.retrieve_by_filters(
            top_k=payload.top_k,
            event_type=payload.event_type,
            location=payload.location,
            date_from=payload.date_from,
            date_to=payload.date_to,
            sector=payload.sector,
            min_severity=payload.min_severity,
        )

        processed = []
        for r in results:
            meta = r.get("metadata", {})
            processed.append(HistoricalRAGSimilarityResult(
                event_id=r["event_id"],
                event_title=meta.get("event_title", ""),
                event_type=meta.get("event_type", ""),
                location=meta.get("location", ""),
                event_date=meta.get("event_date", ""),
                similarity=r["similarity"],
                severity=meta.get("severity", 0.0),
                sectors=meta.get("sectors", ""),
                bullish_tickers=meta.get("bullish_tickers", ""),
                bearish_tickers=meta.get("bearish_tickers", ""),
                impact_summary=meta.get("impact_summary", ""),
            ))

        elapsed = (time.perf_counter() - start) * 1000
        return HistoricalRAGQueryResponse(
            query="filtered retrieval",
            total_results=len(processed),
            processing_time_ms=round(elapsed, 2),
            results=processed,
        )
    except Exception as e:
        logger.error("Historical RAG filter query failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/historical/stats", response_model=HistoricalRAGCollectionStatsResponse)
async def historical_collection_stats(
    rag: HistoricalRAGService = Depends(get_historical_rag),
):
    try:
        stats = await rag.get_collection_stats()
        return HistoricalRAGCollectionStatsResponse(
            collection=stats["collection"],
            document_count=stats["document_count"],
            embedding_dimension=stats["embedding_dimension"],
            cache_stats=stats.get("cache_stats", {}),
        )
    except Exception as e:
        logger.error("Historical RAG stats failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/historical/index", response_model=HistoricalRAGIndexResponse)
async def index_historical_events(
    rag: HistoricalRAGService = Depends(get_historical_rag),
    db=Depends(get_db_session),
):
    """Index all events from the latest historical dataset into ChromaDB."""
    start = time.perf_counter()
    try:
        from app.services.historical.orchestrator import HistoricalOrchestrator
        orchestrator = HistoricalOrchestrator()
        stats = await orchestrator.get_stats()

        dataset_path = stats.get("files", {}).get("json", "")
        if not dataset_path:
            raise HTTPException(status_code=404, detail="No historical dataset found")

        import json
        from pathlib import Path
        from app.services.historical.models import HistoricalMarketImpact

        data = json.loads(Path(dataset_path).read_text())
        events = []
        for item in data:
            try:
                event = HistoricalMarketImpact(
                    event_id=item.get("event_id", ""),
                    event_title=item.get("event_title", ""),
                    event_description=item.get("event_description", ""),
                    event_type=item.get("event_type", ""),
                    location=item.get("location", ""),
                    event_date=datetime.fromisoformat(item["event_date"]) if item.get("event_date") else datetime.now(timezone.utc),
                    severity=item.get("severity", 0.0),
                    confidence=item.get("confidence", 0.0),
                    source=item.get("source", "gdelt"),
                )
                events.append(event)
            except Exception:
                continue

        success, total = await rag.index_events_batch(events)
        elapsed = (time.perf_counter() - start) * 1000
        return HistoricalRAGIndexResponse(
            success=success,
            total=total,
            collection="historical_events",
            indexed_at=datetime.now(timezone.utc).isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Historical RAG index failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/historical/evaluate", response_model=HistoricalRAGEvaluationResponse)
async def evaluate_retrieval(
    payload: HistoricalRAGEvaluationRequest,
    rag: HistoricalRAGService = Depends(get_historical_rag),
):
    """Evaluate retrieval quality for a given query with known relevant events."""
    start = time.perf_counter()
    try:
        results = await rag.retrieve_similar(
            query_text=payload.query,
            top_k=20,
        )

        relevant_ids = set(payload.relevant_event_ids)
        retrieved_ids = {r["event_id"] for r in results}

        evaluator = RetrievalEvaluator()
        metrics = evaluator.evaluate_retrieval(results, relevant_ids)

        elapsed = (time.perf_counter() - start) * 1000
        return HistoricalRAGEvaluationResponse(
            query=payload.query,
            retrieved_count=len(results),
            relevant_count=len(relevant_ids),
            metrics=metrics,
        )
    except Exception as e:
        logger.error("Historical RAG evaluation failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/historical/event/{event_id}")
async def delete_historical_event(
    event_id: str,
    rag: HistoricalRAGService = Depends(get_historical_rag),
):
    success = await rag.delete_event(event_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
    return {"status": "ok", "event_id": event_id, "deleted": True}


@router.post("/historical/reindex")
async def reindex_historical_collection(
    rag: HistoricalRAGService = Depends(get_historical_rag),
):
    """Drop and rebuild the entire historical events collection."""
    from app.services.historical.orchestrator import HistoricalOrchestrator
    orchestrator = HistoricalOrchestrator()
    stats = await orchestrator.get_stats()
    dataset_path = stats.get("files", {}).get("json", "")
    if not dataset_path:
        raise HTTPException(status_code=404, detail="No historical dataset found")

    import json
    from pathlib import Path
    from app.services.historical.models import HistoricalMarketImpact

    data = json.loads(Path(dataset_path).read_text())
    events = []
    from uuid import uuid4
    for item in data:
        try:
            event = HistoricalMarketImpact(
                event_id=item.get("event_id", str(uuid4())),
                event_title=item.get("event_title", ""),
                event_description=item.get("event_description", ""),
                event_type=item.get("event_type", ""),
                location=item.get("location", ""),
                event_date=datetime.fromisoformat(item["event_date"]) if item.get("event_date") else datetime.now(timezone.utc),
                severity=item.get("severity", 0.0),
                confidence=item.get("confidence", 0.0),
            )
            events.append(event)
        except Exception:
            continue

    success, total = await rag.reindex_collection(events)
    return {
        "status": "ok",
        "collection": "historical_events",
        "success": success,
        "total": total,
        "reindexed_at": datetime.now(timezone.utc).isoformat(),
    }
