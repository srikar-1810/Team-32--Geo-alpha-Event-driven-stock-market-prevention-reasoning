from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.api.v1.schemas.geopol import (
    GeopolEventCreate,
    GeopolEventResponse,
    GeopolQueryParams,
    GeopolSummaryResponse,
)
from app.api.v1.schemas.common import PaginatedResponse
from app.core.dependencies import get_db_session
from app.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/events", response_model=PaginatedResponse[GeopolEventResponse])
async def list_events(
    query: GeopolQueryParams = Depends(),
    db=Depends(get_db_session),
):
    logger.info("Fetching geopolitical events with query: %s", query.model_dump())
    
    from app.services.chroma.client import ChromaClient
    from app.services.chroma.collections import CollectionManager
    
    chroma = ChromaClient()
    manager = CollectionManager(chroma)
    
    # In a real app, we would query ChromaDB with filters
    # For now, we get all events from the 'geopol_events' collection
    try:
        client = await chroma._get_client()
        collection = await client.get_collection("geopol_events")
        results = await collection.get(
            limit=query.page_size,
            include=["documents", "metadatas"]
        )
        
        events = []
        if results and results.get("ids"):
            for i in range(len(results["ids"])):
                meta = results["metadatas"][i]
                doc = results["documents"][i]
                events.append(GeopolEventResponse(
                    id=results["ids"][i],
                    source=meta.get("source", "unknown"),
                    title=doc.split(". ")[0],
                    description=doc.split(". ")[1] if ". " in doc else doc,
                    event_date=datetime.fromisoformat(meta.get("event_date").replace("Z", "+00:00")),
                    location=meta.get("location", "Unknown"),
                    event_type=meta.get("event_type", "conflict"),
                    severity=float(meta.get("severity", 0.5)),
                    actors=meta.get("actors", "").split(","),
                    affected_sectors=meta.get("sectors", "").split(","),
                    source_url=meta.get("source_url", ""),
                    mentions=0
                ))
        
        return PaginatedResponse(
            items=events,
            total=len(events),
            page=query.page,
            page_size=query.page_size,
        )
    except Exception as e:
        logger.error("Failed to fetch events from ChromaDB: %s", e)
        return PaginatedResponse(
            items=[],
            total=0,
            page=query.page,
            page_size=query.page_size,
        )


@router.get("/events/{event_id}", response_model=GeopolEventResponse)
async def get_event(event_id: str, db=Depends(get_db_session)):
    return GeopolEventResponse(
        id=event_id,
        source="gdelt",
        title="Example Event",
        description="Detailed description",
        event_date=datetime.now(timezone.utc),
        location="Unknown",
        event_type="conflict",
        severity=0.5,
        actors=[],
        affected_sectors=[],
        source_url="",
        mentions=0,
    )


@router.post("/events/ingest", response_model=GeopolEventResponse)
async def ingest_event(payload: GeopolEventCreate, db=Depends(get_db_session)):
    return GeopolEventResponse(
        id="new-id",
        source=payload.source,
        title=payload.title,
        description=payload.description,
        event_date=payload.event_date,
        location=payload.location,
        event_type=payload.event_type,
        severity=payload.severity,
        actors=payload.actors,
        affected_sectors=payload.affected_sectors,
        source_url=payload.source_url,
        mentions=0,
    )


@router.get("/summary", response_model=GeopolSummaryResponse)
async def get_geopol_summary(db=Depends(get_db_session)):
    from app.services.chroma.client import ChromaClient
    chroma = ChromaClient()
    
    try:
        count = await chroma.count("geopol_events")
        return GeopolSummaryResponse(
            total_events=count,
            active_conflicts=int(count * 0.4), # Mock distribution for now
            high_severity_count=int(count * 0.2),
            top_regions=["Europe", "Middle East", "Asia"],
            top_sectors_affected=["Energy", "Defense", "Technology"],
            last_updated=datetime.now(timezone.utc),
        )
    except Exception:
        return GeopolSummaryResponse(
            total_events=0,
            active_conflicts=0,
            high_severity_count=0,
            top_regions=[],
            top_sectors_affected=[],
            last_updated=datetime.now(timezone.utc),
        )
