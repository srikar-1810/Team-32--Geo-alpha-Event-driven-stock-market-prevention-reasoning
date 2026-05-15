"""API endpoints for the autonomous report generation system."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from app.api.v1.schemas.reports import (
    ReportGenerateRequest,
    ReportGenerateResponse,
    ReportListResponse,
    ReportMetadataResponse,
    ReportScheduleRequest,
    ReportScheduleResponse,
)
from app.api.v1.schemas.common import PaginatedResponse
from app.core.dependencies import get_db_session
from app.logging_config import get_logger
from app.services.report.auto_scheduler import report_scheduler

logger = get_logger(__name__)
router = APIRouter()

REPORT_DIR = Path("data/reports")
PDF_DIR = REPORT_DIR / "pdf"
JSON_DIR = REPORT_DIR / "json"


class AutoBriefResponse(BaseModel):
    status: str
    brief: Optional[Dict[str, Any]] = None
    history: Optional[List[Dict[str, Any]]] = None


class BriefListItem(BaseModel):
    report_id: str
    generated_at: str
    event_count: int
    sector_count: int
    severity_estimate: float
    overall_confidence: float
    pdf_path: str
    json_path: str
    elapsed_seconds: float


@router.get("/brief/status")
async def get_brief_status():
    status = await report_scheduler.get_status()
    return {
        "running": status["running"],
        "interval_seconds": status["interval_seconds"],
        "total_briefs_generated": status["total_briefs_generated"],
        "last_brief": status["last_brief"],
    }


@router.post("/brief/trigger", response_model=AutoBriefResponse)
async def trigger_brief():
    result = await report_scheduler.trigger_now()
    return AutoBriefResponse(status=result["status"], brief=result["brief"])


@router.get("/brief/list")
async def list_briefs(limit: int = Query(20, ge=1, le=100)):
    status = await report_scheduler.get_status()
    briefs = status.get("recent_briefs", [])
    items = []
    for b in briefs:
        items.append(BriefListItem(
            report_id=b.get("report_id", ""),
            generated_at=b.get("generated_at", ""),
            event_count=b.get("event_count", 0),
            sector_count=b.get("sector_count", 0),
            severity_estimate=b.get("severity_estimate", 0),
            overall_confidence=b.get("overall_confidence", 0),
            pdf_path=b.get("pdf_path", ""),
            json_path=b.get("json_path", ""),
            elapsed_seconds=b.get("elapsed_seconds", 0),
        ))
    return {"items": items[:limit], "total": len(briefs)}


@router.get("/brief/latest")
async def get_latest_brief():
    status = await report_scheduler.get_status()
    last = status.get("last_brief")
    if not last:
        raise HTTPException(status_code=404, detail="No briefs generated yet")
    pdf_path = last.get("pdf_path", "")
    json_path = last.get("json_path", "")
    data = {"metadata": last}
    if json_path and Path(json_path).exists():
        data["data"] = json.loads(Path(json_path).read_text())
    return data


@router.get("/brief/{brief_id}")
async def get_brief(brief_id: str):
    status = await report_scheduler.get_status()
    for b in status.get("recent_briefs", []):
        if b.get("report_id") == brief_id:
            pdf_path = b.get("pdf_path", "")
            json_path = b.get("json_path", "")
            data = {"metadata": b}
            if json_path and Path(json_path).exists():
                data["data"] = json.loads(Path(json_path).read_text())
            return data
    raise HTTPException(status_code=404, detail=f"Brief {brief_id} not found")


@router.get("/brief/{brief_id}/pdf")
async def download_brief_pdf(brief_id: str):
    status = await report_scheduler.get_status()
    for b in status.get("recent_briefs", []):
        if b.get("report_id") == brief_id:
            pdf_path = b.get("pdf_path", "")
            if pdf_path and Path(pdf_path).exists():
                return FileResponse(
                    pdf_path,
                    media_type="application/pdf",
                    filename=f"geopol_brief_{brief_id}.pdf",
                )
    raise HTTPException(status_code=404, detail=f"PDF for brief {brief_id} not found")


@router.get("/brief/{brief_id}/json")
async def download_brief_json(brief_id: str):
    status = await report_scheduler.get_status()
    for b in status.get("recent_briefs", []):
        if b.get("report_id") == brief_id:
            json_path = b.get("json_path", "")
            if json_path and Path(json_path).exists():
                return JSONResponse(
                    content=json.loads(Path(json_path).read_text()),
                    media_type="application/json",
                    headers={"Content-Disposition": f"attachment; filename=geopol_brief_{brief_id}.json"},
                )
    raise HTTPException(status_code=404, detail=f"JSON for brief {brief_id} not found")


@router.post("/generate", response_model=ReportGenerateResponse)
async def generate_report(payload: ReportGenerateRequest, db=Depends(get_db_session)):
    return ReportGenerateResponse(
        report_id="report-new",
        title=payload.title,
        status="queued",
        format=payload.format,
        sections=[],
        generated_at=datetime.now(timezone.utc),
        estimated_completion=datetime.now(timezone.utc),
    )


@router.get("", response_model=PaginatedResponse[ReportListResponse])
async def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db=Depends(get_db_session),
):
    status = await report_scheduler.get_status()
    briefs = status.get("recent_briefs", [])
    items = [
        ReportListResponse(
            report_id=b.get("report_id", ""),
            title=f"Intelligence Brief {b.get('generated_at', '')[:10]}",
            status="completed",
            format="pdf",
            created_at=b.get("generated_at", ""),
        )
        for b in briefs
    ]
    return PaginatedResponse(items=items[:page_size], total=len(items), page=page, page_size=page_size)


@router.get("/{report_id}", response_model=ReportMetadataResponse)
async def get_report(report_id: str, db=Depends(get_db_session)):
    return ReportMetadataResponse(
        report_id=report_id,
        title="Intelligence Brief",
        status="completed",
        format="pdf",
        sections=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@router.post("/schedule", response_model=ReportScheduleResponse)
async def schedule_report(payload: ReportScheduleRequest, db=Depends(get_db_session)):
    return ReportScheduleResponse(
        schedule_id="sched-auto",
        active=True,
        cron_expression=payload.cron_expression,
        next_run=datetime.now(timezone.utc),
    )
