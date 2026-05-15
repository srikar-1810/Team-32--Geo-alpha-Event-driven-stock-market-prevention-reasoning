"""Celery tasks for autonomous intelligence brief generation."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.logging_config import get_logger
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(bind=True, max_retries=2, soft_time_limit=600)
def generate_auto_brief(self) -> Dict[str, Any]:
    """Generate an autonomous intelligence brief."""
    logger.info("Starting auto brief generation task")
    try:
        from app.services.report.intelligence_brief import IntelligenceBriefBuilder

        async def _build():
            builder = IntelligenceBriefBuilder()
            result = await builder.build()
            return result

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_build())
        logger.info("Auto brief complete: %s", result.get("report_id", ""))
        return {
            "status": "success",
            "report_id": result.get("report_id"),
            "event_count": result.get("event_count"),
            "pdf_path": result.get("pdf_path"),
            "json_path": result.get("json_path"),
            "elapsed_ms": result.get("execution_time_ms"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error("Auto brief generation failed: %s", e)
        self.retry(exc=e, countdown=120)


@celery_app.task(bind=True, max_retries=1, soft_time_limit=120)
def list_recent_briefs(self) -> List[Dict[str, Any]]:
    """List recent briefs from the scheduler history."""
    try:
        from app.services.report.auto_scheduler import report_scheduler
        status = report_scheduler.get_status()
        if asyncio.iscoroutine(status):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(status).get("recent_briefs", [])
        return status.get("recent_briefs", [])
    except Exception as e:
        logger.error("Failed to list briefs: %s", e)
        return []
