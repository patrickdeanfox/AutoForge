"""Unit tests for api.routers.github — webhook endpoint and event dispatch.

Uses FastAPI's TestClient so no live server is needed.
All HMAC validation is exercised with real signatures.
"""

from __future__ import annotations

import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from api.main import app

# ============================================================
# FIXTURES
# ============================================================


@pytest.fixture()
def client() -> TestClient:
    """Return a TestClient for the FastAPI app."""
    return TestClient(app, raise_server_exceptions=True)


def _sign(payload: bytes, secret: str) -> str:
    """Build a valid X-Hub-Signature-256 header value."""
    digest = hmac.new(
        key=secret.encode(),
        msg=payload,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return f"sha256={digest}"


# ============================================================
# WEBHOOK ENDPOINT — BASIC
# ============================================================


class TestReceiveWebhook:
    """Tests for POST /api/github/webhook."""

    def test_health_check_returns_ok(self, client: TestClient) -> None:
        """Health endpoint is reachable (sanity check that app starts)."""
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_accepts_custom_issue_approved_event(self, client: TestClient) -> None:
        """Custom issue_approved event from GitHub Actions is accepted with 202."""
        payload = {
            "event": "issue_approved",
            "project_id": "my-project",
            "issue_number": 42,
            "issue_title": "feat: add retry logic",
            "issue_url": "https://github.com/org/my-project/issues/42",
        }
        resp = client.post(
            "/api/github/webhook",
            json=payload,
            headers={"X-AutoForge-Source": "github-actions"},
        )
        assert resp.status_code == 202
        assert resp.json()["event"] == "issue_approved"

    def test_accepts_pr_ready_for_qa_event(self, client: TestClient) -> None:
        """pr_ready_for_qa event is dispatched and returns 202."""
        payload = {
            "event": "pr_ready_for_qa",
            "project_id": "my-project",
            "pr_number": 7,
            "pr_title": "feat: done",
            "pr_url": "https://github.com/org/my-project/pull/7",
            "head_sha": "abc123",
        }
        resp = client.post(
            "/api/github/webhook",
            json=payload,
            headers={"X-AutoForge-Source": "github-actions"},
        )
        assert resp.status_code == 202
        assert resp.json()["event"] == "pr_ready_for_qa"

    def test_accepts_drift_scan_event(self, client: TestClient) -> None:
        """drift_scan_requested event is accepted with 202."""
        payload = {
            "event": "drift_scan_requested",
            "project_id": "my-project",
            "triggered_by": "schedule",
        }
        resp = client.post(
            "/api/github/webhook",
            json=payload,
            headers={"X-AutoForge-Source": "github-actions"},
        )
        assert resp.status_code == 202
        assert resp.json()["event"] == "drift_scan_requested"

    def test_accepts_unknown_event_without_error(self, client: TestClient) -> None:
        """Unrecognised event type is logged and returns 202 (not 4xx)."""
        payload = {"some_new_field": "value", "action": "unknown_future_action"}
        resp = client.post(
            "/api/github/webhook",
            json=payload,
        )
        assert resp.status_code == 202


# ============================================================
# NATIVE GITHUB WEBHOOK — SIGNATURE VALIDATION
# ============================================================


class TestWebhookSignatureValidation:
    """Tests for X-Hub-Signature-256 header validation."""

    def test_valid_signature_is_accepted(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A valid X-Hub-Signature-256 header passes signature check."""
        import api.routers.github as github_module

        monkeypatch.setattr(github_module, "WEBHOOK_SECRET", "correct-secret")

        payload = json.dumps({"action": "opened", "pull_request": {"number": 1}}).encode()
        sig = _sign(payload, "correct-secret")

        resp = client.post(
            "/api/github/webhook",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": sig,
            },
        )
        assert resp.status_code == 202

    def test_invalid_signature_returns_401(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A tampered payload with a mismatched signature returns 401."""
        import api.routers.github as github_module

        monkeypatch.setattr(github_module, "WEBHOOK_SECRET", "correct-secret")

        payload = json.dumps({"action": "opened"}).encode()
        sig = _sign(payload, "wrong-secret")

        resp = client.post(
            "/api/github/webhook",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": sig,
            },
        )
        assert resp.status_code == 401

    def test_no_secret_configured_skips_validation(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When WEBHOOK_SECRET is empty, any signature is accepted (dev mode)."""
        import api.routers.github as github_module

        monkeypatch.setattr(github_module, "WEBHOOK_SECRET", "")

        payload = json.dumps({"action": "opened", "pull_request": {"number": 1}}).encode()

        resp = client.post(
            "/api/github/webhook",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": "sha256=not-a-valid-sig",
            },
        )
        assert resp.status_code == 202


# ============================================================
# NATIVE GITHUB PR EVENT DISPATCH
# ============================================================


class TestNativeGithubEvents:
    """Tests for native GitHub webhook payload dispatch."""

    def test_pr_ready_for_review_action(self, client: TestClient) -> None:
        """Native pull_request.ready_for_review event dispatches correctly."""
        payload = {
            "action": "ready_for_review",
            "pull_request": {"number": 5, "title": "done"},
            "repository": {"name": "my-project"},
        }
        resp = client.post("/api/github/webhook", json=payload)
        assert resp.status_code == 202
        assert resp.json()["event"] == "pull_request.ready_for_review"

    def test_pr_closed_action(self, client: TestClient) -> None:
        """Native pull_request.closed event dispatches to pr_closed handler."""
        payload = {
            "action": "closed",
            "pull_request": {"number": 3, "merged": True},
            "repository": {"name": "my-project"},
        }
        resp = client.post("/api/github/webhook", json=payload)
        assert resp.status_code == 202
        assert resp.json()["event"] == "pull_request.closed"

    def test_issue_labeled_approved(self, client: TestClient) -> None:
        """issues.labeled with label=approved dispatches to issue_approved handler."""
        payload = {
            "action": "labeled",
            "label": {"name": "approved"},
            "issue": {"number": 42, "title": "feat: thing"},
            "repository": {"name": "my-project"},
        }
        resp = client.post("/api/github/webhook", json=payload)
        assert resp.status_code == 202
        assert resp.json()["event"] == "issues.labeled.approved"

    def test_issue_labeled_other(self, client: TestClient) -> None:
        """issues.labeled with non-approved label returns 202 but non-dispatch event."""
        payload = {
            "action": "labeled",
            "label": {"name": "feature"},
            "issue": {"number": 10},
            "repository": {"name": "my-project"},
        }
        resp = client.post("/api/github/webhook", json=payload)
        assert resp.status_code == 202
