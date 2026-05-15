from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field


class GeopolEventCreate(BaseModel):
    source: str = Field(..., description="Source of the event (gdelt, manual, etc.)")
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1, max_length=10000)
    event_date: datetime
    location: str = Field(default="Unknown")
    event_type: str = Field(..., description="Type: conflict, election, disaster, policy, etc.")
    severity: float = Field(default=0.5, ge=0.0, le=1.0)
    actors: List[str] = Field(default_factory=list)
    affected_sectors: List[str] = Field(default_factory=list)
    source_url: str = Field(default="")
    metadata: Optional[dict] = None


class GeopolEventResponse(BaseModel):
    id: str
    source: str
    title: str
    description: str
    event_date: datetime
    location: str
    event_type: str
    severity: float
    actors: List[str]
    affected_sectors: List[str]
    source_url: str
    mentions: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GeopolQueryParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=500)
    event_type: Optional[str] = None
    location: Optional[str] = None
    min_severity: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    sector: Optional[str] = None


class GeopolSummaryResponse(BaseModel):
    total_events: int
    active_conflicts: int
    high_severity_count: int
    top_regions: List[str]
    top_sectors_affected: List[str]
    last_updated: datetime
