"""Celery configuration — broker, beat schedule, task settings."""

from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "storemd",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_time_limit=600,  # Hard timeout 10 min
    task_soft_time_limit=540,  # Soft timeout 9 min
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Beat schedule — cron-based scans
celery_app.conf.beat_schedule = {
    # Pro/Agency: daily at 3 AM UTC
    "daily-scan-pro": {
        "task": "tasks.scan_tasks.run_scheduled_scans",
        "schedule": crontab(hour=3, minute=0),
        "args": ("pro",),
    },
    # Starter: weekly Monday at 4 AM UTC
    "weekly-scan-starter": {
        "task": "tasks.scan_tasks.run_scheduled_scans",
        "schedule": crontab(hour=4, minute=0, day_of_week="monday"),
        "args": ("starter",),
    },
    # Agency: daily at 3 AM UTC (same schedule, different plan)
    "daily-scan-agency": {
        "task": "tasks.scan_tasks.run_scheduled_scans",
        "schedule": crontab(hour=3, minute=15),
        "args": ("agency",),
    },
    # Weekly digest: Sunday 09:00 UTC for Starter+ merchants.
    "weekly-reports": {
        "task": "tasks.report_tasks.send_weekly_reports",
        "schedule": crontab(hour=9, minute=0, day_of_week="sunday"),
    },
    # Cross-store intelligence: daily 5 AM UTC.
    "cross-store-analysis": {
        "task": "tasks.cross_store_tasks.run_cross_store_analysis",
        "schedule": crontab(hour=5, minute=0),
    },
}

celery_app.autodiscover_tasks(["tasks"])
