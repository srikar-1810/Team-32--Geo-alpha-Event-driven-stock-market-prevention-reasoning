from __future__ import annotations

from celery.schedules import crontab

from app.workers.celery_app import celery_app

celery_app.conf.beat_schedule = {
    "ingest-gdelt-events-hourly": {
        "task": "app.workers.tasks.ingestion.ingest_gdelt_events",
        "schedule": crontab(minute=0),
        "args": ("conflict OR election OR crisis OR sanctions OR protest",),
    },
    "ingest-reddit-sentiment-every-15min": {
        "task": "app.workers.tasks.ingestion.ingest_reddit_sentiment",
        "schedule": crontab(minute="*/15"),
        "args": ("wallstreetbets,stocks,investing,geopolitics,worldnews,economics",),
    },
    "ingest-market-data-daily": {
        "task": "app.workers.tasks.ingestion.ingest_market_data",
        "schedule": crontab(hour=22, minute=0),
        "args": ("SPY,QQQ,IWM,EEM,XLF,XLE,XLK,XLV,XLI,XLB,XLU,XLY,XLP",),
    },
    "run-morning-briefing": {
        "task": "app.workers.tasks.analysis.run_full_analysis",
        "schedule": crontab(hour=8, minute=30),
        "args": ("morning market briefing", ["SPY", "QQQ", "IWM"]),
    },
}
