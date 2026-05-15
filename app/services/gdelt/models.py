from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GDELTMode(str, Enum):
    EVENT_LIST = "EventList"
    EVENT_LIST_ADV = "EventListAdvanced"
    SUMMARY = "Summary"
    TIMELINE = "Timeline"
    TIMELINE_TONE = "TimelineTone"
    TIMELINE_VOL = "TimelineVol"
    ART_LIST = "ArtList"


class GDELTFormat(str, Enum):
    JSON = "json"
    HTML = "html"
    CSV = "csv"


class GDELTQueryParams(BaseModel):
    query: str = Field(..., description="Search query using GDELT syntax")
    mode: GDELTMode = GDELTMode.EVENT_LIST
    format: GDELTFormat = GDELTFormat.JSON
    max_records: int = Field(default=250, ge=1, le=500)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    source_country: Optional[str] = None
    source_lang: Optional[str] = None


class GDELTLocation(BaseModel):
    name: str = ""
    lat: Optional[float] = None
    lon: Optional[float] = None
    country: Optional[str] = None
    type: Optional[str] = None


class GDELTArticle(BaseModel):
    title: str
    url: str
    source: str = ""
    seendate: str = ""
    domain: str = ""
    language: str = ""
    sentiment: Optional[float] = None
    tone: Optional[str] = None
    social_image: Optional[str] = None


class GDELTEvent(BaseModel):
    event_id: str = ""
    date: str = ""
    actor1: str = ""
    actor2: str = ""
    event_code: str = ""
    event_base_code: str = ""
    root_code: str = ""
    goldstein_scale: float = 0.0
    num_mentions: int = 0
    num_sources: int = 0
    num_articles: int = 0
    avg_tone: float = 0.0
    location: Optional[GDELTLocation] = None
    actors: List[str] = Field(default_factory=list)
    raw_data: Dict[str, Any] = Field(default_factory=dict)
