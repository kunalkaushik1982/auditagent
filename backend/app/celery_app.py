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


# Optional: Configure task routes (for multiple queues)
# Commented out to use default "celery" queue for now
# celery_app.conf.task_routes = {
#     "backend.app.tasks.process_audit_task": {"queue": "audits"},
#     "backend.app.tasks_mock.process_audit_task_mock": {"queue": "audits"},
# }

# Import tasks to register them with Celery (avoid circular import)
try:
    from backend.app.tasks_mock import process_audit_task_mock  # noqa: F401
    from backend.app.tasks import process_audit_task  # noqa: F401
except ImportError as e:
    print(f"Warning: Could not import tasks: {e}")
