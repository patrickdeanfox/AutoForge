"""
Celery task definitions.
Phase 0 skeleton — tasks will be added as each phase is built.
"""

from orchestration.scheduler import app


@app.task(name="orchestration.tasks.health_check")
def health_check() -> dict:
    """Periodic health check task — verifies workers are alive."""
    return {"status": "ok"}
