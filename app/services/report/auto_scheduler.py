"""20-minute auto-scheduler for autonomous intelligence report generation."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.logging_config import get_logger
from app.config import settings

logger = get_logger(__name__)

BRIEF_INTERVAL_SECONDS = 1200  # 20 minutes
BRIEF_HISTORY_FILE = Path("data/reports/brief_history.json")


class ReportScheduler:
    """Autonomous report generation scheduler - runs every 20 minutes."""

    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._brief_history: List[Dict[str, Any]] = []
        self._builder: Any = None
        BRIEF_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._load_history()

    def _load_history(self) -> None:
        if BRIEF_HISTORY_FILE.exists():
            try:
                self._brief_history = json.loads(BRIEF_HISTORY_FILE.read_text())
                logger.info("Loaded %d briefs from history", len(self._brief_history))
            except Exception as e:
                logger.warning("Failed to load brief history: %s", e)
                self._brief_history = []

    def _save_history(self) -> None:
        try:
            keep = self._brief_history[-100:]
            BRIEF_HISTORY_FILE.write_text(json.dumps(keep, indent=2, default=str))
        except Exception as e:
            logger.warning("Failed to save brief history: %s", e)

    async def start(self) -> None:
        if self._running:
            logger.warning("Report scheduler already running")
            return
        self._running = True
        logger.info("Starting report scheduler (interval=%ds)", BRIEF_INTERVAL_SECONDS)
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Report scheduler started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._save_history()
        logger.info("Report scheduler stopped")

    async def _run_loop(self) -> None:
        while self._running:
            try:
                await self._generate_brief()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Brief generation failed: %s", e)
            await asyncio.sleep(BRIEF_INTERVAL_SECONDS)

    async def _generate_brief(self) -> None:
        logger.info("=== Auto brief generation cycle ===")
        start = datetime.now(timezone.utc)
        from app.services.report.intelligence_brief import IntelligenceBriefBuilder

        if self._builder is None:
            self._builder = IntelligenceBriefBuilder()
        try:
            brief = await self._builder.build()
        except Exception as e:
            logger.error("Intelligence brief build failed: %s", e)
            return

        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        entry = {
            "report_id": brief.get("report_id", ""),
            "generated_at": brief.get("generated_at", datetime.now(timezone.utc).isoformat()),
            "event_count": brief.get("event_count", 0),
            "sector_count": len(brief.get("sectors", [])),
            "analogy_count": len(brief.get("analogies", [])),
            "severity_estimate": brief.get("severity_estimate", 0),
            "overall_confidence": brief.get("overall_confidence", 0),
            "pdf_path": brief.get("pdf_path", ""),
            "json_path": brief.get("json_path", ""),
            "elapsed_seconds": round(elapsed, 1),
            "execution_time_ms": brief.get("execution_time_ms", 0),
        }
        self._brief_history.append(entry)
        self._save_history()
        self._cleanup_old_briefs()
        logger.info(
            "Auto brief complete: %s | %d events %d sectors | pdf=%s | %.0fms",
            entry["report_id"], entry["event_count"], entry["sector_count"],
            entry["pdf_path"], entry["elapsed_seconds"] * 1000,
        )

    def _cleanup_old_briefs(self, keep_hours: int = 72) -> None:
        cutoff = datetime.now(timezone.utc).timestamp() - keep_hours * 3600
        for d in [Path("data/reports/pdf"), Path("data/reports/json")]:
            for p in d.glob("*"):
                if p.is_file() and p.stat().st_mtime < cutoff:
                    try:
                        p.unlink()
                    except OSError:
                        pass
        self._brief_history = self._brief_history[-200:]

    async def get_status(self) -> Dict[str, Any]:
        running = self._running
        last = self._brief_history[-1] if self._brief_history else None
        return {
            "running": running,
            "interval_seconds": BRIEF_INTERVAL_SECONDS,
            "total_briefs_generated": len(self._brief_history),
            "last_brief": last,
            "recent_briefs": self._brief_history[-10:],
        }

    async def trigger_now(self) -> Dict[str, Any]:
        logger.info("Manual trigger: generating brief now")
        await self._generate_brief()
        return {"status": "completed", "brief": self._brief_history[-1] if self._brief_history else None}


report_scheduler = ReportScheduler()
