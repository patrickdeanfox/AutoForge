"""GitHub webhook router — receives and dispatches GitHub event payloads.

AutoForge registers a webhook on every project repo pointing to this endpoint.
Events are validated via HMAC-SHA256 signature (``X-Hub-Signature-256`` header)
then dispatched to the appropriate Celery task for async processing.

Supported events:
- ``pull_request`` — opened, ready_for_review, closed, synchronize
- ``issues``       — labeled (triggers execution pipeline on ``approved`` label)
- Custom           — ``issue_approved``, ``pr_ready_for_qa``, ``drift_scan_requested``
                     sent by GitHub Actions workflows via direct POST
"""

from __future__ import annotations

import os

import structlog
from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel

from orchestration.github_manager import GitHubManager

logger = structlog.get_logger()

router = APIRouter(prefix="/api/github", tags=["github"])

# ============================================================
# CONFIG
# ============================================================

WEBHOOK_SECRET: str = os.environ.get("GITHUB_WEBHOOK_SECRET", "")


# ============================================================
# REQUEST MODELS — custom events from GitHub Actions workflows
# ============================================================


class IssueApprovedEvent(BaseModel):
    """Payload sent by ``agent_trigger.yml`` when an issue gains the approved label."""

    event: str
    project_id: str
    issue_number: int
    issue_title: str
    issue_url: str


class PrReadyForQAEvent(BaseModel):
    """Payload sent by ``qa_trigger.yml`` when a PR becomes ready for review."""

    event: str
    project_id: str
    pr_number: int
    pr_title: str
    pr_url: str
    head_sha: str


class DriftScanRequestedEvent(BaseModel):
    """Payload sent by ``drift_monitor.yml`` to request a knowledge re-crawl."""

    event: str
    project_id: str
    triggered_by: str


# ============================================================
# ENDPOINTS
# ============================================================


@router.post(
    "/webhook",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Receive GitHub webhook or AutoForge Actions event",
)
async def receive_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    x_autoforge_source: str | None = Header(default=None),
) -> dict[str, str]:
    """Handle inbound events from GitHub or GitHub Actions.

    GitHub native webhooks include ``X-Hub-Signature-256`` for HMAC validation.
    Events sent by AutoForge GitHub Actions workflows use ``X-AutoForge-Source``
    and carry a typed JSON body.

    All processing is asynchronous — this endpoint returns 202 immediately and
    dispatches work to Celery. This keeps the GitHub webhook delivery window
    well within GitHub's 10-second timeout.
    """
    raw_body = await request.body()

    # Validate HMAC signature for native GitHub webhook deliveries
    if x_hub_signature_256 is not None:
        _verify_signature(raw_body, x_hub_signature_256)

    payload = await request.json()
    event_type = _infer_event_type(payload, x_autoforge_source)

    log = logger.bind(event_type=event_type, source=x_autoforge_source or "github")
    log.info("webhook_received", step="receive_webhook", lifecycle="step_start")

    handler = _EVENT_HANDLERS.get(event_type, _handle_unknown)
    result = handler(payload)

    log.info(
        "webhook_dispatched",
        step="receive_webhook",
        lifecycle="step_complete",
        outcome=result,
    )
    return {"status": "accepted", "event": event_type}


# ============================================================
# EVENT HANDLERS
# ============================================================


def _handle_issue_approved(payload: dict) -> str:
    """Dispatch execution pipeline trigger for an approved issue."""
    project_id = payload.get("project_id") or _extract_repo_slug(payload)
    issue_number = payload.get("issue_number") or payload.get("issue", {}).get("number")
    logger.info(
        "issue_approved_received",
        project_id=project_id,
        issue_number=issue_number,
    )
    # TODO Phase 3: dispatch orchestration.tasks.trigger_execution_pipeline.delay(...)
    return "issue_approved"


def _handle_pr_ready_for_qa(payload: dict) -> str:
    """Dispatch QA pipeline trigger for a PR that is ready for review."""
    project_id = payload.get("project_id") or _extract_repo_slug(payload)
    pr_number = payload.get("pr_number") or payload.get("pull_request", {}).get("number")
    logger.info(
        "pr_ready_for_qa_received",
        project_id=project_id,
        pr_number=pr_number,
    )
    # TODO Phase 4: dispatch orchestration.tasks.trigger_qa_pipeline.delay(...)
    return "pr_ready_for_qa"


def _handle_drift_scan(payload: dict) -> str:
    """Dispatch knowledge drift scan for a project."""
    project_id = payload.get("project_id") or _extract_repo_slug(payload)
    triggered_by = payload.get("triggered_by", "unknown")
    logger.info(
        "drift_scan_requested",
        project_id=project_id,
        triggered_by=triggered_by,
    )
    # TODO Phase 1: dispatch orchestration.tasks.trigger_drift_scan.delay(...)
    return "drift_scan_requested"


def _handle_pr_closed(payload: dict) -> str:
    """Log PR closure — used for audit trail and cost tracking."""
    repo = _extract_repo_slug(payload)
    pr_number = payload.get("pull_request", {}).get("number")
    merged = payload.get("pull_request", {}).get("merged", False)
    logger.info(
        "pr_closed",
        project_id=repo,
        pr_number=pr_number,
        merged=merged,
    )
    return "pr_closed"


def _handle_unknown(payload: dict) -> str:
    """Log and ignore unrecognised event types."""
    logger.info("unknown_event_received", payload_keys=list(payload.keys()))
    return "ignored"


# Map event type strings → handler functions
_EVENT_HANDLERS = {
    "issue_approved": _handle_issue_approved,
    "issues.labeled.approved": _handle_issue_approved,
    "pr_ready_for_qa": _handle_pr_ready_for_qa,
    "pull_request.ready_for_review": _handle_pr_ready_for_qa,
    "drift_scan_requested": _handle_drift_scan,
    "pull_request.closed": _handle_pr_closed,
}


# ============================================================
# HELPERS
# ============================================================


def _verify_signature(raw_body: bytes, signature_header: str) -> None:
    """Raise 401 if the HMAC-SHA256 signature does not match.

    Skips validation if GITHUB_WEBHOOK_SECRET is not configured (dev only).
    """
    if not WEBHOOK_SECRET:
        logger.warning("webhook_signature_check_skipped", reason="GITHUB_WEBHOOK_SECRET not set")
        return

    if not GitHubManager.verify_webhook_signature(raw_body, signature_header, WEBHOOK_SECRET):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )


def _infer_event_type(payload: dict, source: str | None) -> str:
    """Derive a canonical event type string from the payload.

    For direct AutoForge Actions posts the ``event`` field is explicit.
    For native GitHub webhooks we compose ``{github_event}.{action}`` or
    ``{github_event}.{action}.{label}`` for finer granularity.
    """
    # Custom event posted by GitHub Actions workflow
    explicit_event = payload.get("event")
    if explicit_event:
        return str(explicit_event)

    # Native GitHub webhook — compose from action + label context
    action = payload.get("action", "")

    if "pull_request" in payload:
        if action == "ready_for_review":
            return "pull_request.ready_for_review"
        if action == "closed":
            return "pull_request.closed"
        return f"pull_request.{action}"

    if "issue" in payload:
        if action == "labeled":
            label_name = payload.get("label", {}).get("name", "")
            if label_name == "approved":
                return "issues.labeled.approved"
            return f"issues.labeled.{label_name}"
        return f"issues.{action}"

    return "unknown"


def _extract_repo_slug(payload: dict) -> str:
    """Extract the repo name (project slug) from a native GitHub webhook payload."""
    return payload.get("repository", {}).get("name", "unknown")
