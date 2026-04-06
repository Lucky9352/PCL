"""Celery application for IndiaGround background tasks."""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core import get_settings

settings = get_settings()

celery_app = Celery(
    "indiaground",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.scrape_task",
        "app.tasks.analyze_task",
        "app.tasks.cleanup_task",
    ],
)

celery_app.conf.update(
    timezone="Asia/Kolkata",
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Auto-discover tasks in app.tasks package
celery_app.autodiscover_tasks(["app.tasks"])

# Periodic beat schedule
celery_app.conf.beat_schedule = {
    "scrape-inshorts-periodic": {
        "task": "app.tasks.scrape_task.scrape_inshorts",
        "schedule": crontab(minute=f"*/{settings.SCRAPE_INTERVAL_MINUTES}"),
    },
    "cleanup-archive-old-articles": {
        "task": "app.tasks.cleanup_task.archive_old_articles",
        "schedule": crontab(hour=2, minute=0),  # 2 AM daily
    },
}
