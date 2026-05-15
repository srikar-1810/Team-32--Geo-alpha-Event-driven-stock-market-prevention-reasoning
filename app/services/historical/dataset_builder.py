from __future__ import annotations

import asyncio
import csv
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from app.logging_config import get_logger
from app.services.historical.cleaning import HistoricalDataCleaner
from app.services.historical.enrichment import EventEnricher, MacroCollector
from app.services.historical.event_mapper import EventMapper
from app.services.historical.gdelt_collector import HistoricalGDELTCollector
from app.services.historical.market_collector import HistoricalMarketCollector
from app.services.historical.models import (
    DataQuality,
    HistoricalDatasetMetadata,
    HistoricalMarketImpact,
)

logger = get_logger(__name__)

HISTORICAL_DATA_DIR = Path("data/historical")
RAW_DIR = HISTORICAL_DATA_DIR / "raw"
PROCESSED_DIR = HISTORICAL_DATA_DIR / "processed"
EXPORTS_DIR = HISTORICAL_DATA_DIR / "exports"
REGISTRY_DIR = HISTORICAL_DATA_DIR / "registry"


class DatasetBuilder:
    """Builds complete historical geopolitical market datasets."""

    def __init__(
        self,
        gdelt_collector: Optional[HistoricalGDELTCollector] = None,
        market_collector: Optional[HistoricalMarketCollector] = None,
        event_mapper: Optional[EventMapper] = None,
        enricher: Optional[EventEnricher] = None,
        macro_collector: Optional[MacroCollector] = None,
        cleaner: Optional[HistoricalDataCleaner] = None,
    ) -> None:
        self.gdelt = gdelt_collector or HistoricalGDELTCollector()
        self.market = market_collector or HistoricalMarketCollector()
        self.mapper = event_mapper or EventMapper(market_collector=self.market)
        self.enricher = enricher or EventEnricher()
        self.macro = macro_collector or MacroCollector()
        self.cleaner = cleaner or HistoricalDataCleaner()

        for d in [RAW_DIR, PROCESSED_DIR, EXPORTS_DIR, REGISTRY_DIR]:
            d.mkdir(parents=True, exist_ok=True)

    async def build_dataset(
        self,
        start_date: date,
        end_date: date,
        version: str = "",
        max_events: int = 500,
        export_formats: Optional[List[str]] = None,
    ) -> HistoricalDatasetMetadata:
        """Build a full dataset: collect, map, enrich, validate, export."""
        dataset_id = str(uuid4())
        version = version or f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        formats = export_formats or ["json", "csv", "parquet"]

        logger.info(
            "Building dataset %s (%s): %s to %s, max %d events",
            dataset_id, version, start_date.isoformat(), end_date.isoformat(), max_events,
        )

        # Step 1: Collect
        raw_events = await self.gdelt.collect_by_date_range(
            start_date=start_date,
            end_date=end_date,
            max_per_query=min(250, max_events // 5 + 1),
        )
        logger.info("Collected %d raw events", len(raw_events))

        raw_path = RAW_DIR / f"raw_{version}.json"
        self._save_raw(raw_events, raw_path)

        # Step 2: Map to sectors/stocks
        mapped: List[HistoricalMarketImpact] = []
        chunk_size = 10
        for i in range(0, min(len(raw_events), max_events), chunk_size):
            chunk = raw_events[i:i + chunk_size]
            tasks = [self.mapper.enrich_with_market_data(e) for e in chunk]
            results = await self._gather_with_limit(tasks, concurrency=3)
            mapped.extend([r for r in results if r is not None])

        logger.info("Mapped %d events with market data", len(mapped))

        # Step 3: Enrich
        enriched: List[HistoricalMarketImpact] = []
        for event in mapped:
            macro = await self.macro.collect_macro_context(event.event_date.date())
            event = await self.enricher.enrich_event(event, macro_data=macro)
            enriched.append(event)

        logger.info("Enriched %d events", len(enriched))

        # Step 4: Clean & validate
        valid, rejected = self.cleaner.validate_and_clean(enriched)
        logger.info("Validation: %d valid, %d rejected", len(valid), len(rejected))

        # Step 5: Quality classification
        for event in valid:
            event.data_quality = self.cleaner.estimate_quality(event)
            event.dataset_version = version

        processed_path = PROCESSED_DIR / f"processed_{version}.json"
        self._save_processed(valid, rejected, processed_path)

        # Step 6: Compute market volatility
        self._compute_market_volatility(valid)

        # Step 7: Export
        export_paths = await self._export_dataset(valid, version, formats)

        # Step 8: Build metadata
        quality_dist: Dict[str, int] = {}
        for q in DataQuality:
            quality_dist[q.value] = 0
        for event in valid:
            quality_dist[event.data_quality.value] = quality_dist.get(event.data_quality.value, 0) + 1

        sectors_covered: List[str] = []
        for event in valid:
            for s in event.sectors_impacted:
                if s.sector_name not in sectors_covered:
                    sectors_covered.append(s.sector_name)

        metadata = HistoricalDatasetMetadata(
            dataset_id=dataset_id,
            version=version,
            created_at=datetime.now(timezone.utc),
            event_count=len(valid),
            date_range_start=start_date,
            date_range_end=end_date,
            sectors_covered=sectors_covered,
            sources=["gdelt", "tiingo", "yahoo"],
            total_collected=len(raw_events),
            total_validated=len(valid),
            total_rejected=len(rejected),
            quality_distribution=quality_dist,
            enrichment_applied=["macro_context", "historical_analogues"],
            file_paths=export_paths,
        )

        metadata_path = REGISTRY_DIR / f"metadata_{version}.json"
        self._save_metadata(metadata, metadata_path)
        logger.info("Dataset build complete: %s (%d events)", dataset_id, len(valid))

        return metadata

    def _save_raw(
        self,
        events: List[HistoricalMarketImpact],
        path: Path,
    ) -> None:
        data = [e.to_dict() for e in events]
        path.write_text(json.dumps(data, indent=2, default=str))
        logger.info("Saved raw events to %s (%d records)", path, len(data))

    def _save_processed(
        self,
        valid: List[HistoricalMarketImpact],
        rejected: List[HistoricalMarketImpact],
        path: Path,
    ) -> None:
        data = {
            "valid": [e.to_dict() for e in valid],
            "rejected": [e.to_dict() for e in rejected],
            "stats": self.cleaner.get_quality_stats(),
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }
        path.write_text(json.dumps(data, indent=2, default=str))
        logger.info("Saved processed events to %s", path)

    def _save_metadata(
        self,
        metadata: HistoricalDatasetMetadata,
        path: Path,
    ) -> None:
        path.write_text(json.dumps(metadata.to_dict(), indent=2, default=str))
        # Also save a latest.json pointer
        latest_path = REGISTRY_DIR / "latest.json"
        latest_path.write_text(json.dumps(metadata.to_dict(), indent=2, default=str))
        logger.info("Saved metadata to %s", path)

    async def _export_dataset(
        self,
        events: List[HistoricalMarketImpact],
        version: str,
        formats: List[str],
    ) -> Dict[str, str]:
        paths: Dict[str, str] = {}

        for fmt in formats:
            try:
                if fmt == "json":
                    path = await self._export_json(events, version)
                elif fmt == "csv":
                    path = await self._export_csv(events, version)
                elif fmt == "parquet":
                    path = await self._export_parquet(events, version)
                else:
                    logger.warning("Unknown export format: %s", fmt)
                    continue
                paths[fmt] = str(path)
                logger.info("Exported %s: %s", fmt, path)
            except Exception as e:
                logger.error("Export failed for %s: %s", fmt, e)

        return paths

    async def _export_json(self, events: List[HistoricalMarketImpact], version: str) -> Path:
        path = EXPORTS_DIR / f"dataset_{version}.json"
        data = [e.to_dict() for e in events]
        path.write_text(json.dumps(data, indent=2, default=str))
        return path

    async def _export_csv(self, events: List[HistoricalMarketImpact], version: str) -> Path:
        path = EXPORTS_DIR / f"dataset_{version}.csv"
        fieldnames = [
            "event_id", "event_title", "event_type", "location", "event_date",
            "goldstein_scale", "num_mentions", "severity", "confidence",
            "data_quality", "overall_market_return_5d", "overall_market_return_30d",
        ]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for e in events:
                row = e.to_dict()
                writer.writerow(row)
        return path

    async def _export_parquet(self, events: List[HistoricalMarketImpact], version: str) -> Path:
        path = EXPORTS_DIR / f"dataset_{version}.parquet"
        try:
            import pandas as pd
            data = [e.to_dict() for e in events]
            df = pd.DataFrame(data)
            df.to_parquet(path, index=False)
        except ImportError:
            logger.warning("pandas not available; skipping parquet export")
            path = EXPORTS_DIR / f"dataset_{version}.json"
            data = [e.to_dict() for e in events]
            path.write_text(json.dumps(data, indent=2, default=str))
            path = path.with_suffix(".json")
        return path

    def _compute_market_volatility(self, events: List[HistoricalMarketImpact]) -> None:
        for event in events:
            if event.sectors_impacted:
                vol_changes = [s.volatility_impact for s in event.sectors_impacted if s.volatility_impact != 0]
                event.volatility_change_pct = (
                    sum(vol_changes) / len(vol_changes) if vol_changes else 0.0
                )

    async def _gather_with_limit(
        self,
        tasks: List[Any],
        concurrency: int = 3,
    ) -> List[Any]:
        sem = asyncio.Semaphore(concurrency)

        async def _run(task):
            async with sem:
                try:
                    return await task
                except Exception as e:
                    logger.warning("Task failed: %s", e)
                    return None

        return await asyncio.gather(*[_run(t) for t in tasks])

    async def close(self) -> None:
        await self.gdelt.close()
        await self.market.close()
