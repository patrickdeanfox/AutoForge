"""
Celery application and beat schedule.
Phase 0 skeleton — beat schedule entries will be added as each phase is built.
"""

import os

from celery import Celery

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

app = Celery(
    "autoforge",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["orchestration.tasks"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={},
)
