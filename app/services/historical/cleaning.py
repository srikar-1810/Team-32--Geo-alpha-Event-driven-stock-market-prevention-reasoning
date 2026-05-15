from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from app.logging_config import get_logger
from app.services.historical.models import (
    DataQuality,
    HistoricalMarketImpact,
    ImpactDirection,
)

logger = get_logger(__name__)

MIN_TITLE_LENGTH = 10
MAX_TITLE_LENGTH = 500
MIN_DESCRIPTION_LENGTH = 5
MAX_DESCRIPTION_LENGTH = 10000
MIN_SEVERITY = 0.0
MAX_SEVERITY = 100.0
MIN_CONFIDENCE = 0.0
MAX_CONFIDENCE = 1.0
MAX_RETURN_PCT = 500.0


class HistoricalDataCleaner:
    """Validates, cleans, and normalizes historical event records."""

    def __init__(self, strict: bool = False) -> None:
        self.strict = strict
        self.stats: Dict[str, int] = {
            "total": 0,
            "passed": 0,
            "failed_title": 0,
            "failed_description": 0,
            "failed_date": 0,
            "failed_severity": 0,
            "failed_confidence": 0,
            "failed_duplicate": 0,
            "failed_invalid_return": 0,
            "failed_sector": 0,
        }

    def validate_and_clean(
        self,
        events: List[HistoricalMarketImpact],
    ) -> Tuple[List[HistoricalMarketImpact], List[HistoricalMarketImpact]]:
        """Validate events, return (valid, rejected)."""
        self.stats["total"] = len(events)
        valid: List[HistoricalMarketImpact] = []
        rejected: List[HistoricalMarketImpact] = []
        seen_signatures: Set[str] = set()

        for event in events:
            issues = self._validate_event(event)
            sig = self._signature(event)

            if issues:
                self.stats["failed_" + issues[0]] = self.stats.get("failed_" + issues[0], 0) + 1
                rejected.append(event)
                continue

            if sig in seen_signatures:
                self.stats["failed_duplicate"] += 1
                rejected.append(event)
                continue

            seen_signatures.add(sig)
            cleaned = self._clean_event(event)
            valid.append(cleaned)
            self.stats["passed"] += 1

        logger.info(
            "Validation complete: %d valid, %d rejected out of %d",
            len(valid), len(rejected), len(events),
        )
        return valid, rejected

    def _validate_event(self, event: HistoricalMarketImpact) -> Optional[str]:
        if not event.event_title or len(event.event_title) < MIN_TITLE_LENGTH:
            return "title"
        if len(event.event_title) > MAX_TITLE_LENGTH:
            return "title"

        if not event.event_description or len(event.event_description) < MIN_DESCRIPTION_LENGTH:
            return "description"
        if len(event.event_description) > MAX_DESCRIPTION_LENGTH:
            return "description"

        if not event.event_date:
            return "date"
        if event.event_date > datetime.now(timezone.utc):
            return "date"
        if event.event_date.year < 1900:
            return "date"

        if event.severity < MIN_SEVERITY or event.severity > MAX_SEVERITY:
            return "severity"

        if event.confidence < MIN_CONFIDENCE or event.confidence > MAX_CONFIDENCE:
            return "confidence"

        for sector in event.sectors_impacted:
            for stock in sector.stocks:
                for ret in [stock.return_1d, stock.return_5d, stock.return_10d]:
                    if abs(ret) > MAX_RETURN_PCT:
                        return "invalid_return"

        return None

    def _signature(self, event: HistoricalMarketImpact) -> str:
        title = event.event_title.strip().lower()[:80]
        date_str = event.event_date.strftime("%Y%m%d") if event.event_date else "nodate"
        loc = event.location.lower()[:30] if event.location else "noloc"
        return f"{title}|{date_str}|{loc}"

    def _clean_event(self, event: HistoricalMarketImpact) -> HistoricalMarketImpact:
        event.event_title = self._clean_text(event.event_title)
        event.event_description = self._clean_text(event.event_description)
        event.location = event.location.strip() if event.location else "Unknown"

        event.severity = max(MIN_SEVERITY, min(MAX_SEVERITY, event.severity))
        event.confidence = max(MIN_CONFIDENCE, min(MAX_CONFIDENCE, event.confidence))

        event.countries = list(set(c.strip() for c in event.countries if c.strip()))
        event.actors = list(set(a.strip() for a in event.actors if a.strip()))

        event.sectors_impacted = [
            s for s in event.sectors_impacted
            if s.sector_name.strip()
        ]

        if event.top_bullish_stocks:
            event.top_bullish_stocks = sorted(
                [s for s in event.top_bullish_stocks if isinstance(s, dict) and s.get("ticker")],
                key=lambda x: abs(x.get("return_5d", 0)),
                reverse=True,
            )[:10]

        if event.top_bearish_stocks:
            event.top_bearish_stocks = sorted(
                [s for s in event.top_bearish_stocks if isinstance(s, dict) and s.get("ticker")],
                key=lambda x: abs(x.get("return_5d", 0)),
                reverse=True,
            )[:10]

        return event

    def _clean_text(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s\.,;:!?\'\"\-\(\)&/%$€£¥+#@]', '', text)
        return text.strip()

    def get_quality_stats(self) -> Dict[str, int]:
        return dict(self.stats)

    def estimate_quality(self, event: HistoricalMarketImpact) -> DataQuality:
        score = 0
        checks = 0

        if event.event_title and len(event.event_title) > 30:
            score += 1
        checks += 1

        if event.event_description and len(event.event_description) > 100:
            score += 1
        checks += 1

        if event.source_url:
            score += 1
        checks += 1

        if event.sectors_impacted:
            score += 1
        checks += 1

        if event.top_bullish_stocks or event.top_bearish_stocks:
            score += 1
        checks += 1

        if event.confidence > 0.7:
            score += 1
        checks += 1

        if event.num_mentions > 10:
            score += 1
        checks += 1

        if event.goldstein_scale != 0.0:
            score += 1
        checks += 1

        ratio = score / checks if checks > 0 else 0

        if ratio >= 0.8:
            return DataQuality.HIGH
        elif ratio >= 0.5:
            return DataQuality.MEDIUM
        else:
            return DataQuality.LOW


class HistoricalValidator:
    """Business-rule validation for historical events."""

    def __init__(self) -> None:
        self.rules: List[str] = []

    def validate_consistency(self, event: HistoricalMarketImpact) -> List[str]:
        errors: List[str] = []

        if event.top_bullish_stocks and event.top_bearish_stocks:
            seen_bullish = {s["ticker"] for s in event.top_bullish_stocks}
            seen_bearish = {s["ticker"] for s in event.top_bearish_stocks}
            overlap = seen_bullish & seen_bearish
            if overlap:
                errors.append(f"Stocks appear in both bullish and bearish: {overlap}")

        if event.sectors_impacted:
            for sector in event.sectors_impacted:
                if sector.direction == ImpactDirection.NEUTRAL and abs(sector.return_5d) > 5:
                    errors.append(
                        f"Sector {sector.sector_name} marked neutral but return={sector.return_5d:.2f}%"
                    )

        return errors
