from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from app.logging_config import get_logger
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(bind=True, max_retries=2, soft_time_limit=600)
def run_full_analysis(self, query: str, tickers: List[str] = None) -> Dict[str, Any]:
    logger.info("Starting full analysis: query='%s'", query)
    try:
        import asyncio
        from app.services.agent.orchestrator import AgentOrchestrator

        async def _run():
            orchestrator = AgentOrchestrator()
            result = await orchestrator.run_full_analysis(
                query=query,
                tickers=tickers or [],
                generate_report=True,
            )
            return result

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_run())
        result["timestamp"] = datetime.now(timezone.utc).isoformat()
        logger.info("Full analysis completed: %s", result.get("orchestration_id"))
        return result

    except Exception as e:
        logger.error("Full analysis failed: %s", e)
        self.retry(exc=e, countdown=120)


@celery_app.task(bind=True, max_retries=2, soft_time_limit=300)
def run_sentiment_analysis(self, query: str, source: str = "reddit") -> Dict[str, Any]:
    logger.info("Starting sentiment analysis: query='%s'", query)
    try:
        import asyncio
        from app.services.agent.sentiment_agent import SentimentAnalystAgent

        async def _run():
            agent = SentimentAnalystAgent()
            result = await agent.run({"query": query, "limit": 200})
            return result

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_run())
        result["timestamp"] = datetime.now(timezone.utc).isoformat()
        return result

    except Exception as e:
        logger.error("Sentiment analysis failed: %s", e)
        self.retry(exc=e, countdown=60)


@celery_app.task(bind=True, max_retries=2, soft_time_limit=120)
def generate_report(self, title: str, sections: Dict[str, str], format: str = "markdown") -> Dict[str, Any]:
    logger.info("Starting report generation: title='%s'", title)
    try:
        import asyncio
        from app.services.report.generator import ReportGenerator

        async def _generate():
            generator = ReportGenerator()
            report = await generator.generate(
                title=title,
                sections=sections,
                format=format,
            )
            return {
                "status": "success",
                "report_id": report.id,
                "title": report.title,
                "format": report.format,
                "file_path": report.file_path,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_generate())

    except Exception as e:
        logger.error("Report generation failed: %s", e)
        self.retry(exc=e, countdown=30)
