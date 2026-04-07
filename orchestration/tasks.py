"""Celery task definitions for AutoForge.

Phase 0 tasks:
- ``health_check`` — verifies workers are alive (always on)
- ``morning_summary`` — daily 7am CT digest (Phase 0 stub; populated with real
  pipeline data in Phase 5 once the observability layer is built)

Tasks are imported by the Celery application in ``orchestration/scheduler.py``
via the ``include`` directive.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog

from orchestration.scheduler import app

logger = structlog.get_logger()


# ============================================================
# HEALTH CHECK
# ============================================================


@app.task(name="orchestration.tasks.health_check")
def health_check() -> dict[str, str]:
    """Periodic health check task — verifies workers are alive."""
    return {"status": "ok"}


# ============================================================
# MORNING SUMMARY
# ============================================================


@app.task(name="orchestration.tasks.morning_summary", bind=True)
def morning_summary(self: object) -> dict[str, object]:
    """Daily morning summary — runs at 7:00 AM CT via Celery Beat.

    Phase 0 stub: logs a structured placeholder summary and returns it.
    The summary dict shape is the contract that Phase 5 will populate with
    real data from the observability layer (PR queue, cost, stuck agents, etc.).

    In Phase 5 this task will also push the summary to Telegram via the bot.

    Returns:
        Dict with keys:
        - ``run_at``: ISO 8601 UTC timestamp of when this run executed.
        - ``phase``: Current AutoForge build phase (0 during initial development).
        - ``pr_queue``: List of PRs awaiting review (empty in Phase 0).
        - ``needs_human``: List of needs-human issues (empty in Phase 0).
        - ``stuck_agents``: List of stuck agent run IDs (empty in Phase 0).
        - ``last_24h_runs``: Count of agent runs in the past 24 hours.
        - ``last_24h_cost_usd``: Estimated token cost in USD for the past 24 hours.
        - ``message``: Human-readable status note.
    """
    run_at = datetime.now(tz=UTC).isoformat()

    summary: dict[str, object] = {
        "run_at": run_at,
        "phase": 0,
        "pr_queue": [],
        "needs_human": [],
        "stuck_agents": [],
        "last_24h_runs": 0,
        "last_24h_cost_usd": 0.0,
        "message": "Pipeline not yet built — Phase 0 stub. Real data arrives in Phase 5.",
    }

    logger.info(
        "morning_summary_generated",
        run_at=run_at,
        phase=0,
        pr_queue_count=0,
        needs_human_count=0,
        stuck_agents_count=0,
        last_24h_runs=0,
        last_24h_cost_usd=0.0,
    )

    return summary
