from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.logging_config import get_logger
from app.services.historical.cleaning import HistoricalDataCleaner
from app.services.historical.dataset_builder import DatasetBuilder
from app.services.historical.enrichment import EventEnricher, MacroCollector
from app.services.historical.event_mapper import EventMapper
from app.services.historical.gdelt_collector import HistoricalGDELTCollector
from app.services.historical.market_collector import HistoricalMarketCollector
from app.services.historical.models import (
    HistoricalDatasetMetadata,
    HistoricalMarketImpact,
)

logger = get_logger(__name__)

DEFAULT_INCREMENTAL_DAYS = 7
DEFAULT_FULL_DAYS = 365
DATA_DIR = Path("data/historical")


class HistoricalOrchestrator:
    """Orchestrates the end-to-end historical dataset pipeline."""

    def __init__(
        self,
        builder: Optional[DatasetBuilder] = None,
    ) -> None:
        self.builder = builder or DatasetBuilder()
        self._pending_events: List[HistoricalMarketImpact] = []

    async def run_full_build(
        self,
        days: int = DEFAULT_FULL_DAYS,
        max_events: int = 500,
        export_formats: Optional[List[str]] = None,
    ) -> HistoricalDatasetMetadata:
        """Build a complete historical dataset covering N days back."""
        end = date.today()
        start = end - timedelta(days=days)

        logger.info("Full historical build: %s to %s (%d days)", start, end, days)
        metadata = await self.builder.build_dataset(
            start_date=start,
            end_date=end,
            max_events=max_events,
            export_formats=export_formats,
        )
        return metadata

    async def run_incremental_update(
        self,
        days: int = DEFAULT_INCREMENTAL_DAYS,
        max_events: int = 100,
    ) -> Optional[HistoricalDatasetMetadata]:
        """Run an incremental update for just the last N days."""
        metadata_path = DATA_DIR / "registry" / "latest.json"

        if not metadata_path.exists():
            logger.info("No existing dataset found; running full build")
            return await self.run_full_build(days=min(days * 4, 365), max_events=max_events)

        try:
            import json
            existing = json.loads(metadata_path.read_text())
            last_end = existing.get("date_range_end")
            if last_end:
                last_date = datetime.fromisoformat(last_end).date()
                start = last_date + timedelta(days=1)
            else:
                start = date.today() - timedelta(days=days)
        except Exception:
            start = date.today() - timedelta(days=days)

        end = date.today()

        if start >= end:
            logger.info("Dataset is already up to date (last: %s)", start)
            return None

        logger.info("Incremental update: %s to %s", start, end)
        metadata = await self.builder.build_dataset(
            start_date=start,
            end_date=end,
            max_events=max_events,
        )

        await self._merge_with_existing(metadata)
        return metadata

    async def _merge_with_existing(
        self,
        new_metadata: HistoricalDatasetMetadata,
    ) -> None:
        """Merge incremental dataset with the existing one."""
        latest_path = DATA_DIR / "registry" / "latest.json"
        if not latest_path.exists():
            logger.info("No existing dataset to merge with")
            return

        try:
            import json
            existing = json.loads(latest_path.read_text())

            new_version = new_metadata.version
            new_path = DATA_DIR / "exports" / f"dataset_{new_version}.json"
            existing_path_str = existing.get("file_paths", {}).get("json", "")

            if existing_path_str and Path(existing_path_str).exists():
                existing_data = json.loads(Path(existing_path_str).read_text())
                new_data = json.loads(new_path.read_text()) if new_path.exists() else []

                seen_ids = {e["event_id"] for e in existing_data}
                merged = list(existing_data)

                for event in new_data:
                    if event["event_id"] not in seen_ids:
                        merged.append(event)
                        seen_ids.add(event["event_id"])

                merged.sort(key=lambda e: e.get("event_date", ""), reverse=True)
                merged_path = DATA_DIR / "exports" / f"dataset_merged_{new_version}.json"
                merged_path.write_text(json.dumps(merged, indent=2, default=str))

                logger.info(
                    "Merged dataset: %d existing + %d new = %d total",
                    len(existing_data), len(new_data), len(merged),
                )
        except Exception as e:
            logger.warning("Merge failed (non-fatal): %s", e)

    async def query(
        self,
        event_type: Optional[str] = None,
        location: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        sector: Optional[str] = None,
        min_severity: float = 0.0,
        max_results: int = 50,
    ) -> List[HistoricalMarketImpact]:
        """Query the latest built dataset with filters."""
        latest_path = DATA_DIR / "registry" / "latest.json"
        if not latest_path.exists():
            logger.warning("No dataset found; run a build first")
            return []

        try:
            import json
            metadata = json.loads(latest_path.read_text())
            json_path = metadata.get("file_paths", {}).get("json", "")
            if not json_path or not Path(json_path).exists():
                return []

            data = json.loads(Path(json_path).read_text())
        except Exception as e:
            logger.error("Failed to load dataset: %s", e)
            return []

        results = []
        for item in data:
            if event_type and event_type.lower() not in item.get("event_type", "").lower():
                continue
            if location and location.lower() not in item.get("location", "").lower():
                continue
            if sector:
                sectors = [s["sector_name"].lower() for s in item.get("sectors_impacted", [])]
                if sector.lower() not in sectors:
                    continue
            if date_from:
                ed = item.get("event_date", "")
                if ed and datetime.fromisoformat(ed).date() < date_from:
                    continue
            if date_to:
                ed = item.get("event_date", "")
                if ed and datetime.fromisoformat(ed).date() > date_to:
                    continue
            if item.get("severity", 0) < min_severity:
                continue

            results.append(item)
            if len(results) >= max_results:
                break

        events = []
        for r in results:
            try:
                event = HistoricalMarketImpact(**{k: v for k, v in r.items() if k != "tone"})
                if "tone" in r:
                    from app.services.historical.models import EventTone
                    event.tone = EventTone(**r["tone"])
                events.append(event)
            except Exception:
                pass

        return events

    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the latest dataset."""
        latest_path = DATA_DIR / "registry" / "latest.json"
        if not latest_path.exists():
            return {"status": "no_dataset", "message": "No dataset has been built yet"}

        try:
            import json
            metadata = json.loads(latest_path.read_text())
            return {
                "status": "available",
                "dataset_id": metadata.get("dataset_id"),
                "version": metadata.get("version"),
                "event_count": metadata.get("event_count"),
                "date_range": {
                    "start": metadata.get("date_range_start"),
                    "end": metadata.get("date_range_end"),
                },
                "sectors_covered": metadata.get("sectors_covered", []),
                "quality_distribution": metadata.get("quality_distribution", {}),
                "files": metadata.get("file_paths", {}),
                "created_at": metadata.get("created_at"),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def close(self) -> None:
        await self.builder.close()
