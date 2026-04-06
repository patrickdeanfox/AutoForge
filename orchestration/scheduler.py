"""
Celery application and task definitions.
Phase 0 skeleton — tasks will be added as each phase is built.
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
    beat_schedule={
        # Phase 0: morning summary at 7am daily
        "morning-summary": {
            "task": "orchestration.tasks.send_morning_summary",
            "schedule": 25200.0,  # 7am UTC — adjust for your timezone
        },
    },
)
