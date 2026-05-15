from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReportSection(BaseModel):
    title: str
    content: str
    section_type: str = Field(default="text")
    data: Optional[Dict[str, Any]] = None


class ReportGenerateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    format: str = Field(default="pdf", pattern="^(pdf|html|markdown|json)$")
    sections: List[str] = Field(default_factory=list)
    include_charts: bool = True
    parameters: Optional[Dict[str, Any]] = None


class ReportGenerateResponse(BaseModel):
    report_id: str
    title: str
    status: str
    format: str
    sections: List[ReportSection]
    generated_at: datetime
    estimated_completion: datetime


class ReportListResponse(BaseModel):
    report_id: str
    title: str
    status: str
    format: str
    created_at: datetime


class ReportMetadataResponse(BaseModel):
    report_id: str
    title: str
    status: str
    format: str
    sections: List[ReportSection]
    created_at: datetime
    updated_at: datetime


class ReportScheduleRequest(BaseModel):
    title: str
    cron_expression: str = Field(..., description="Cron schedule expression")
    format: str = Field(default="pdf")
    recipients: List[str] = Field(default_factory=list)
    parameters: Optional[Dict[str, Any]] = None


class ReportScheduleResponse(BaseModel):
    schedule_id: str
    active: bool
    cron_expression: str
    next_run: datetime
