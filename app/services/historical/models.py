from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class ImpactDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class DataQuality(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class AffectedStock:
    ticker: str
    name: str = ""
    sector: str = ""
    pre_event_price: float = 0.0
    post_event_price: float = 0.0
    return_1d: float = 0.0
    return_5d: float = 0.0
    return_10d: float = 0.0
    return_30d: float = 0.0
    volume_change_pct: float = 0.0
    volatility_before: float = 0.0
    volatility_after: float = 0.0
    impact_score: float = 0.0
    direction: ImpactDirection = ImpactDirection.NEUTRAL
    confidence: float = 0.0


@dataclass
class SectorImpact:
    sector_name: str
    etf_ticker: str = ""
    impact_score: float = 0.0
    direction: ImpactDirection = ImpactDirection.NEUTRAL
    return_1d: float = 0.0
    return_5d: float = 0.0
    return_10d: float = 0.0
    return_30d: float = 0.0
    volatility_impact: float = 0.0
    stocks: List[AffectedStock] = field(default_factory=list)


@dataclass
class EventTone:
    tone_score: float = 0.0
    positive_score: float = 0.0
    negative_score: float = 0.0
    polarity: float = 0.0
    activity_reference: float = 0.0
    self_reference: float = 0.0


@dataclass
class HistoricalMarketImpact:
    event_id: str = ""
    event_title: str = ""
    event_description: str = ""
    event_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str = ""
    location: str = ""
    countries: List[str] = field(default_factory=list)
    actors: List[str] = field(default_factory=list)
    goldstein_scale: float = 0.0
    num_mentions: int = 0
    source_url: str = ""

    tone: EventTone = field(default_factory=EventTone)
    severity: float = 0.0
    confidence: float = 0.0

    sectors_impacted: List[SectorImpact] = field(default_factory=list)
    top_bullish_stocks: List[Dict[str, Any]] = field(default_factory=list)
    top_bearish_stocks: List[Dict[str, Any]] = field(default_factory=list)

    market_volatility_before: float = 0.0
    market_volatility_after: float = 0.0
    volatility_change_pct: float = 0.0

    overall_market_return_5d: float = 0.0
    overall_market_return_30d: float = 0.0

    impact_summary: str = ""
    historical_analogues: List[str] = field(default_factory=list)
    data_quality: DataQuality = DataQuality.MEDIUM

    source: str = "gdelt"
    collected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    dataset_version: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_title": self.event_title,
            "event_description": self.event_description,
            "event_date": self.event_date.isoformat() if self.event_date else None,
            "event_type": self.event_type,
            "location": self.location,
            "countries": self.countries,
            "actors": self.actors,
            "goldstein_scale": self.goldstein_scale,
            "num_mentions": self.num_mentions,
            "source_url": self.source_url,
            "tone": {
                "tone_score": self.tone.tone_score,
                "positive_score": self.tone.positive_score,
                "negative_score": self.tone.negative_score,
                "polarity": self.tone.polarity,
            },
            "severity": self.severity,
            "confidence": self.confidence,
            "sectors_impacted": [
                {
                    "sector_name": s.sector_name,
                    "etf_ticker": s.etf_ticker,
                    "impact_score": s.impact_score,
                    "direction": s.direction.value,
                    "return_1d": s.return_1d,
                    "return_5d": s.return_5d,
                    "return_10d": s.return_10d,
                    "return_30d": s.return_30d,
                    "volatility_impact": s.volatility_impact,
                    "stocks": [
                        {
                            "ticker": st.ticker,
                            "return_1d": st.return_1d,
                            "return_5d": st.return_5d,
                            "return_10d": st.return_10d,
                            "impact_score": st.impact_score,
                            "direction": st.direction.value,
                            "confidence": st.confidence,
                        }
                        for st in s.stocks
                    ],
                }
                for s in self.sectors_impacted
            ],
            "top_bullish_stocks": self.top_bullish_stocks,
            "top_bearish_stocks": self.top_bearish_stocks,
            "market_volatility_before": self.market_volatility_before,
            "market_volatility_after": self.market_volatility_after,
            "volatility_change_pct": self.volatility_change_pct,
            "overall_market_return_5d": self.overall_market_return_5d,
            "overall_market_return_30d": self.overall_market_return_30d,
            "impact_summary": self.impact_summary,
            "historical_analogues": self.historical_analogues,
            "data_quality": self.data_quality.value,
            "source": self.source,
            "collected_at": self.collected_at.isoformat() if self.collected_at else None,
            "dataset_version": self.dataset_version,
        }


@dataclass
class HistoricalDatasetMetadata:
    dataset_id: str = field(default_factory=lambda: str(uuid4()))
    version: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_count: int = 0
    date_range_start: Optional[date] = None
    date_range_end: Optional[date] = None
    sectors_covered: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    total_collected: int = 0
    total_validated: int = 0
    total_rejected: int = 0
    quality_distribution: Dict[str, int] = field(default_factory=dict)
    enrichment_applied: List[str] = field(default_factory=list)
    file_paths: Dict[str, str] = field(default_factory=dict)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "event_count": self.event_count,
            "date_range_start": self.date_range_start.isoformat() if self.date_range_start else None,
            "date_range_end": self.date_range_end.isoformat() if self.date_range_end else None,
            "sectors_covered": self.sectors_covered,
            "sources": self.sources,
            "total_collected": self.total_collected,
            "total_validated": self.total_validated,
            "total_rejected": self.total_rejected,
            "quality_distribution": self.quality_distribution,
            "enrichment_applied": self.enrichment_applied,
            "file_paths": self.file_paths,
            "notes": self.notes,
        }


@dataclass
class HistoricalEventRaw:
    source: str
    raw_data: Dict[str, Any]
    collected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    parse_status: str = "pending"
    parse_error: Optional[str] = None
