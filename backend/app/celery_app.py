"""
Celery application configuration.
File: backend/app/celery_app.py

Initializes Celery with Redis broker for async task processing.
"""

from celery import Celery
from backend.app.core.config import settings

# Create Celery application
celery_app = Celery(
    "audit_agent",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,  # Results expire after 1 hour
    task_track_started=True,  # Track task start time
    task_time_limit=600,  # 10 minutes max per task
    task_soft_time_limit=540,  # Soft limit at 9 minutes
)


# Configure task autodiscovery
celery_app.autodiscover_tasks(['backend.app'], force=True)
