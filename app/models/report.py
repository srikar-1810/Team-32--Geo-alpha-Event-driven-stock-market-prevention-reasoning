from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.models.base import Entity


class ReportSection(Entity):
    title: str
    content: str
    section_type: str = "text"
    order: int = 0
    data: Optional[Dict[str, Any]] = None


class Report(Entity):
    title: str
    description: Optional[str] = None
    status: str = "draft"
    format: str = "pdf"
    sections: List[Dict[str, Any]] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    generated_by: Optional[str] = None
    file_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    scheduled: bool = False
    cron_expression: Optional[str] = None


class ReportSchedule(Entity):
    report_id: str
    active: bool = True
    cron_expression: str
    format: str = "pdf"
    recipients: List[str] = Field(default_factory=list)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
