from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.models.base import Entity


class GeoPolEvent(Entity):
    source: str
    title: str
    description: str
    event_date: datetime
    location: str = "Unknown"
    event_type: str
    severity: float = Field(default=0.5, ge=0.0, le=1.0)
    actors: List[str] = Field(default_factory=list)
    affected_sectors: List[str] = Field(default_factory=list)
    source_url: str = ""
    mentions: int = 0
    gdelt_raw: Optional[Dict[str, Any]] = None
    embedding: Optional[List[float]] = None
