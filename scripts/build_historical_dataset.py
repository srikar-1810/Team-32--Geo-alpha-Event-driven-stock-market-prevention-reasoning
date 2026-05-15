#!/usr/bin/env python3
"""Build a complete historical geopolitical market dataset from scratch."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


async def build_dataset(
    days: int = 365,
    max_events: int = 500,
    version: str = "",
    export_formats: Optional[List[str]] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Run the full dataset build pipeline."""
    try:
        from app.services.historical.orchestrator import HistoricalOrchestrator
    except ImportError as e:
        print(f"Error: cannot import HistoricalOrchestrator: {e}", file=sys.stderr)
        print("Make sure you're running from the project root and app is installed.", file=sys.stderr)
        sys.exit(1)

    end = date.today()
    start = end - timedelta(days=days)
    formats = export_formats or ["json"]

    print(f"Building historical dataset: {start} to {end} ({days} days)")
    print(f"Max events: {max_events}")
    print(f"Export formats: {', '.join(formats)}")
    print()

    orchestrator = HistoricalOrchestrator()

    start_time = datetime.now(timezone.utc)
    try:
        metadata = await orchestrator.run_full_build(
            days=days,
            max_events=max_events,
            export_formats=formats,
        )
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()

        print(f"Dataset build complete!")
        print(f"  Dataset ID: {metadata.dataset_id}")
        print(f"  Version: {metadata.version}")
        print(f"  Events collected: {metadata.total_collected}")
        print(f"  Events validated: {metadata.total_validated}")
        print(f"  Events rejected:  {metadata.total_rejected}")
        print(f"  Sectors covered:  {len(metadata.sectors_covered)}")
        print(f"  Elapsed: {elapsed:.1f}s")
        print(f"  Files:")
        for fmt, path in metadata.file_paths.items():
            print(f"    {fmt}: {path}")

        quality = metadata.quality_distribution
        if quality:
            print(f"  Quality distribution:")
            for q, count in sorted(quality.items()):
                print(f"    {q}: {count}")

        return metadata.to_dict()

    except Exception as e:
        print(f"Error during build: {e}", file=sys.stderr)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    finally:
        await orchestrator.close()


async def list_datasets() -> None:
    """List all built datasets from the registry."""
    registry_dir = Path("data/historical/registry")
    if not registry_dir.exists():
        print("No datasets found (data/historical/registry does not exist).")
        return

    metadata_files = sorted(registry_dir.glob("metadata_*.json"))
    if not metadata_files:
        print("No dataset metadata found.")
        return

    latest_path = registry_dir / "latest.json"
    latest = None
    if latest_path.exists():
        try:
            latest = json.loads(latest_path.read_text())
            latest = latest.get("version")
        except Exception:
            pass

    print(f"Found {len(metadata_files)} dataset(s):")
    print()
    for mf in metadata_files:
        try:
            meta = json.loads(mf.read_text())
            version = meta.get("version", "?")
            marker = " <-- latest" if version == latest else ""
            print(f"  {version}{marker}")
            print(f"    Events: {meta.get('event_count', '?')}")
            print(f"    Range: {meta.get('date_range_start', '?')} to {meta.get('date_range_end', '?')}")
            print(f"    Created: {meta.get('created_at', '?')}")
            print(f"    Sectors: {len(meta.get('sectors_covered', []))}")
            print()
        except Exception as e:
            print(f"  {mf.name}: error reading ({e})")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a complete historical geopolitical market dataset",
    )
    parser.add_argument(
        "--days", type=int, default=365,
        help="Number of days back to collect (default: 365)",
    )
    parser.add_argument(
        "--max-events", type=int, default=500,
        help="Maximum events to include (default: 500)",
    )
    parser.add_argument(
        "--version", type=str, default="",
        help="Custom version string (default: auto-generated)",
    )
    parser.add_argument(
        "--formats", type=str, nargs="+", default=["json"],
        help="Export formats: json csv parquet (default: json)",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List existing datasets and exit",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Verbose error output",
    )

    args = parser.parse_args()

    if args.list:
        asyncio.run(list_datasets())
        return

    asyncio.run(build_dataset(
        days=args.days,
        max_events=args.max_events,
        version=args.version,
        export_formats=args.formats,
        verbose=args.verbose,
    ))


if __name__ == "__main__":
    main()
