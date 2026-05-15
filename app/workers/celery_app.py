from __future__ import annotations

from celery import Celery

from app.config import settings

celery_app = Celery(
    "geomarketgpt",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.tasks.ingestion",
        "app.workers.tasks.analysis",
        "app.workers.tasks.reports",
    ],
)

celery_app.conf.update(
    task_track_started=settings.CELERY_TASK_TRACK_STARTED,
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    result_serializer=settings.CELERY_RESULT_SERIALIZER,
    accept_content=settings.CELERY_ACCEPT_CONTENT,
    result_expires=3600 * 48,
    worker_max_tasks_per_child=200,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)
