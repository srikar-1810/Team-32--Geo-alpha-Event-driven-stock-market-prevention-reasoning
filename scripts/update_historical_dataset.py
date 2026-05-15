#!/usr/bin/env python3
"""Incrementally update the historical geopolitical market dataset."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


async def update_dataset(
    days: int = 7,
    max_events: int = 100,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Run an incremental dataset update for the last N days."""
    try:
        from app.services.historical.orchestrator import HistoricalOrchestrator
    except ImportError as e:
        print(f"Error: cannot import HistoricalOrchestrator: {e}", file=sys.stderr)
        print("Make sure you're running from the project root and app is installed.", file=sys.stderr)
        sys.exit(1)

    print(f"Running incremental update (last {days} days, max {max_events} events)")
    print()

    orchestrator = HistoricalOrchestrator()

    start_time = datetime.now(timezone.utc)
    try:
        metadata = await orchestrator.run_incremental_update(
            days=days,
            max_events=max_events,
        )
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()

        if metadata is None:
            print("Dataset is already up to date. No new events to collect.")
            latest_path = Path("data/historical/registry/latest.json")
            if latest_path.exists():
                meta = json.loads(latest_path.read_text())
                print(f"Latest dataset: {meta.get('version', '?')} "
                      f"({meta.get('event_count', '?')} events, "
                      f"updated {meta.get('created_at', '?')})")
            return {}

        print(f"Incremental update complete!")
        print(f"  Dataset ID: {metadata.dataset_id}")
        print(f"  Version: {metadata.version}")
        print(f"  New events collected: {metadata.total_collected}")
        print(f"  New events validated: {metadata.total_validated}")
        print(f"  New events rejected:  {metadata.total_rejected}")
        print(f"  Elapsed: {elapsed:.1f}s")
        print(f"  Files:")
        for fmt, path in metadata.file_paths.items():
            print(f"    {fmt}: {path}")

        return metadata.to_dict()

    except Exception as e:
        print(f"Error during incremental update: {e}", file=sys.stderr)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    finally:
        await orchestrator.close()


async def show_stats() -> Dict[str, Any]:
    """Display statistics about the latest dataset."""
    try:
        from app.services.historical.orchestrator import HistoricalOrchestrator
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    orchestrator = HistoricalOrchestrator()
    try:
        stats = await orchestrator.get_stats()
        status = stats.get("status", "unknown")

        if status == "no_dataset":
            print("No dataset has been built yet. Run build_historical_dataset.py first.")
            return {}

        print("Current Dataset Status:")
        print(f"  Version: {stats.get('version', '?')}")
        print(f"  Events: {stats.get('event_count', '?')}")
        dr = stats.get("date_range", {})
        print(f"  Date range: {dr.get('start', '?')} to {dr.get('end', '?')}")
        print(f"  Sectors covered: {len(stats.get('sectors_covered', []))}")
        print(f"  Created: {stats.get('created_at', '?')}")

        quality = stats.get("quality_distribution", {})
        if quality:
            print("  Quality distribution:")
            for q, count in sorted(quality.items()):
                print(f"    {q}: {count}")

        files = stats.get("files", {})
        if files:
            print("  Files:")
            for fmt, path in files.items():
                print(f"    {fmt}: {path}")

        return stats

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return {}
    finally:
        await orchestrator.close()


async def run_scheduled_updates(
    interval_hours: int = 24,
    days_per_update: int = 7,
    max_events: int = 100,
    iterations: int = 0,
    verbose: bool = False,
) -> None:
    """Run incremental updates on a schedule."""
    print(f"Scheduled updates every {interval_hours}h, {days_per_update} day window")
    if iterations > 0:
        print(f"Running {iterations} iteration(s)")
    else:
        print("Running indefinitely (Ctrl+C to stop)")
    print()

    count = 0
    while iterations == 0 or count < iterations:
        count += 1
        print(f"[{datetime.now(timezone.utc).isoformat()}] Update #{count}")
        await update_dataset(
            days=days_per_update,
            max_events=max_events,
            verbose=verbose,
        )
        print()

        if iterations != 0 and count >= iterations:
            break

        print(f"Sleeping for {interval_hours}h...")
        await asyncio.sleep(interval_hours * 3600)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Incrementally update the historical geopolitical market dataset",
    )
    parser.add_argument(
        "--days", type=int, default=7,
        help="Days back to collect (default: 7)",
    )
    parser.add_argument(
        "--max-events", type=int, default=100,
        help="Maximum events per update (default: 100)",
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Show dataset statistics and exit",
    )
    parser.add_argument(
        "--schedule", type=float, default=0,
        help="Run on a schedule: interval in hours (default: 0 = one-off)",
    )
    parser.add_argument(
        "--iterations", type=int, default=0,
        help="Number of scheduled iterations (0 = indefinite, default: 0)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Verbose error output",
    )

    args = parser.parse_args()

    if args.stats:
        asyncio.run(show_stats())
        return

    if args.schedule > 0:
        asyncio.run(run_scheduled_updates(
            interval_hours=args.schedule,
            days_per_update=args.days,
            max_events=args.max_events,
            iterations=args.iterations,
            verbose=args.verbose,
        ))
    else:
        asyncio.run(update_dataset(
            days=args.days,
            max_events=args.max_events,
            verbose=args.verbose,
        ))


if __name__ == "__main__":
    main()
