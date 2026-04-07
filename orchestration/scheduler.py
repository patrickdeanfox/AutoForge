"""Celery application and beat schedule for AutoForge.

Infrastructure:
- Broker and result backend: Redis (URL from REDIS_URL env var).
- Beat schedule: tasks that run on a cron schedule.

Phase 0 beat schedule:
- ``morning-summary``: daily at 13:00 UTC (7:00 AM CDT / 8:00 AM CST).
  Stub in Phase 0; populated with real pipeline data in Phase 5.

Beat schedule entries are added here as each phase is built. Do not add a
schedule entry until the underlying task is implemented and tested.
"""

from __future__ import annotations

import os

from celery import Celery
from celery.schedules import crontab

# ============================================================
# CONFIG
# ============================================================

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Morning summary schedule — 13:00 UTC = 7:00 AM CDT (UTC-6).
# During CST (UTC-5) this fires at 8:00 AM. Adjust when DST handling matters.
_MORNING_SUMMARY_HOUR_UTC = 13
_MORNING_SUMMARY_MINUTE_UTC = 0

# ============================================================
# CELERY APP
# ============================================================

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
        "morning-summary": {
            "task": "orchestration.tasks.morning_summary",
            "schedule": crontab(
                hour=_MORNING_SUMMARY_HOUR_UTC,
                minute=_MORNING_SUMMARY_MINUTE_UTC,
            ),
            # Allow up to 1 hour for a missed beat to still run.
            # After 1 hour, skip the missed run rather than pile up.
            "options": {"expires": 3600},
        },
    },
)
