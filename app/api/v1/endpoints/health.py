from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app import __version__
from app.config import settings
from app.utils.singleton import redis_client

router = APIRouter()


@router.get("")
async def health_check():
    db_status = "unknown"
    redis_status = "unknown"

    try:
        from sqlalchemy import text
        from app.db.session import engine
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"

    try:
        await redis_client.ping()
        redis_status = "healthy"
    except Exception:
        redis_status = "unhealthy"

    return {
        "name": settings.APP_NAME,
        "version": __version__,
        "environment": settings.APP_ENV.value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "ok" if db_status == "healthy" or redis_status == "healthy" else "degraded",
        "checks": {
            "database": db_status,
            "redis": redis_status,
        },
    }
