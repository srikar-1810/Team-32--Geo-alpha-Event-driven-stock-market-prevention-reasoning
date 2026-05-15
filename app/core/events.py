from __future__ import annotations

from fastapi import FastAPI

from app.config import settings
from app.db.session import engine
from app.logging_config import get_logger
from app.services.ingestion.manager import ingestion_manager
from app.services.ingestion.storage import geopol_storage
from app.utils.singleton import redis_client

logger = get_logger(__name__)


async def on_startup_handler(app: FastAPI) -> None:
    logger.info("Initializing services...")

    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection verified.")
    except Exception as e:
        logger.warning("Database not available: %s", e)

    try:
        await redis_client.ping()
        logger.info("Redis connection verified.")
    except Exception as e:
        logger.warning("Redis not available: %s", e)

    if settings.SENTRY_DSN:
        _init_sentry(app)

    try:
        # Register storage callbacks
        ingestion_manager.register_storage_callback("geopol", geopol_storage.save_events)
        
        await ingestion_manager.start()
        logger.info("Ingestion manager started with %d tasks.", ingestion_manager.scheduler.task_count)
    except Exception as e:
        logger.warning("Ingestion manager failed to start: %s. Data ingestion will be unavailable.", e)

    try:
        from app.services.report.auto_scheduler import report_scheduler
        await report_scheduler.start()
        logger.info("Autonomous report scheduler started (interval=%ds).", settings.REPORT_AUTO_GENERATE_INTERVAL)
    except Exception as e:
        logger.warning("Report scheduler failed to start: %s", e)


async def on_shutdown_handler(app: FastAPI) -> None:
    logger.info("Shutting down services...")

    try:
        from app.services.report.auto_scheduler import report_scheduler
        await report_scheduler.stop()
        logger.info("Report scheduler stopped.")
    except Exception as e:
        logger.warning("Report scheduler shutdown error: %s", e)

    try:
        await ingestion_manager.stop()
        logger.info("Ingestion manager stopped.")
    except Exception as e:
        logger.warning("Ingestion manager shutdown error: %s", e)

    await engine.dispose()
    logger.info("Database connections closed.")

    await redis_client.close()
    logger.info("Redis connection closed.")


def _init_sentry(app: FastAPI) -> None:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.APP_ENV.value,
            traces_sample_rate=0.1 if settings.is_development else 0.5,
        )
        app.add_middleware(SentryAsgiMiddleware)
        logger.info("Sentry initialized.")
    except ImportError:
        logger.warning("sentry-sdk not installed; skipping Sentry init.")
