"""Integration-style tests for the knowledge resource API router.

Uses FastAPI's synchronous TestClient with a tmp_path-backed KNOWLEDGE_DIR
so no real filesystem paths are polluted. Every test is fully isolated.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers import knowledge as knowledge_router
from schemas.knowledge_resource import ResourceStatus

# NOTE: KNOWLEDGE_DIR is set per-test via monkeypatch. The router reads it
# at request time via _knowledge_dir(), not at import time, so overriding
# the env var in each test fixture is sufficient for full isolation.

# ============================================================
# APP FIXTURE
# ============================================================


@pytest.fixture()
def app() -> FastAPI:
    """Minimal FastAPI app with only the knowledge router mounted."""
    _app = FastAPI()
    _app.include_router(knowledge_router.router)
    return _app


@pytest.fixture()
def knowledge_dir(tmp_path: Path) -> Path:
    """Return a temporary knowledge base directory."""
    d = tmp_path / "knowledge"
    d.mkdir()
    return d


@pytest.fixture()
def client(app: FastAPI, knowledge_dir: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """TestClient with KNOWLEDGE_DIR pointed at a temp directory."""
    monkeypatch.setenv("KNOWLEDGE_DIR", str(knowledge_dir))
    return TestClient(app)


# ============================================================
# HELPERS
# ============================================================

_VALID_PAYLOAD = {
    "resource_type": "api_docs",
    "title": "Stripe API Docs",
    "description": "Official Stripe REST API documentation.",
    "source_url": "https://stripe.com/docs/api",
}

_PROJECT_ID = "test-project"
_BASE_URL = f"/api/projects/{_PROJECT_ID}/knowledge"


def _create_resource(client: TestClient, payload: dict | None = None) -> dict:
    """Helper — POST a resource and return the parsed response body."""
    body = payload or _VALID_PAYLOAD
    resp = client.post(_BASE_URL, json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ============================================================
# TESTS — POST /knowledge
# ============================================================


def test_create_knowledge_resource_returns_201(client: TestClient) -> None:
    """POST with valid payload returns HTTP 201."""
    resp = client.post(_BASE_URL, json=_VALID_PAYLOAD)
    assert resp.status_code == 201


def test_create_sets_project_id_from_url(client: TestClient) -> None:
    """The created resource has project_id taken from the URL path, not the body."""
    data = _create_resource(client)
    assert data["project_id"] == _PROJECT_ID


def test_create_sets_created_at_to_now(client: TestClient) -> None:
    """created_at is populated server-side as a recent UTC timestamp."""
    before = datetime.now(UTC)
    data = _create_resource(client)
    after = datetime.now(UTC)

    # Parse the returned timestamp — it may or may not have a timezone suffix.
    created_at_str = data["created_at"]
    # Pydantic serialises as ISO 8601; handle both tz-aware and naive representations.
    try:
        created_at = datetime.fromisoformat(created_at_str)
    except ValueError:
        pytest.fail(f"created_at is not a valid ISO datetime: {created_at_str!r}")

    # Make timezone-aware if naive (treat as UTC).
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)

    assert before <= created_at <= after


def test_create_sets_status_to_pending_crawl(client: TestClient) -> None:
    """Newly created resources always start with status 'pending_crawl'."""
    data = _create_resource(client)
    assert data["status"] == ResourceStatus.pending_crawl.value


# ============================================================
# TESTS — GET /knowledge (list)
# ============================================================


def test_list_returns_all_resources_for_project(client: TestClient) -> None:
    """GET returns all resources created for a project."""
    _create_resource(client)
    _create_resource(
        client,
        {
            **_VALID_PAYLOAD,
            "title": "Second Resource",
            "source_url": "https://stripe.com/docs/api2",
        },
    )
    resp = client.get(_BASE_URL)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2


def test_list_returns_empty_for_unknown_project(client: TestClient) -> None:
    """GET on a project with no resources returns an empty list (not 404)."""
    resp = client.get("/api/projects/nonexistent-project/knowledge")
    assert resp.status_code == 200
    assert resp.json() == []


# ============================================================
# TESTS — GET /knowledge/{id}
# ============================================================


def test_get_resource_by_id_returns_200(client: TestClient) -> None:
    """GET /{id} returns the correct resource with HTTP 200."""
    created = _create_resource(client)
    resource_id = created["id"]

    resp = client.get(f"{_BASE_URL}/{resource_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == resource_id
    assert data["title"] == _VALID_PAYLOAD["title"]


def test_get_unknown_resource_returns_404(client: TestClient) -> None:
    """GET /{id} for a non-existent resource returns HTTP 404."""
    resp = client.get(f"{_BASE_URL}/00000000-0000-4000-8000-000000000000")
    assert resp.status_code == 404


# ============================================================
# TESTS — PATCH /knowledge/{id}/status
# ============================================================


def test_update_status_changes_status(client: TestClient) -> None:
    """PATCH /{id}/status updates the persisted status and returns the resource."""
    created = _create_resource(client)
    resource_id = created["id"]

    resp = client.patch(
        f"{_BASE_URL}/{resource_id}/status",
        json={"status": "crawled"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "crawled"

    # Verify persistence — re-fetch the resource.
    refetched = client.get(f"{_BASE_URL}/{resource_id}")
    assert refetched.json()["status"] == "crawled"


def test_update_status_with_invalid_value_returns_422(client: TestClient) -> None:
    """PATCH with an invalid status value returns HTTP 422 (Pydantic validation)."""
    created = _create_resource(client)
    resource_id = created["id"]

    resp = client.patch(
        f"{_BASE_URL}/{resource_id}/status",
        json={"status": "definitely_not_a_real_status"},
    )
    assert resp.status_code == 422


# ============================================================
# TESTS — DELETE /knowledge/{id}
# ============================================================


def test_delete_resource_returns_204(client: TestClient) -> None:
    """DELETE /{id} returns HTTP 204 and the resource no longer exists."""
    created = _create_resource(client)
    resource_id = created["id"]

    resp = client.delete(f"{_BASE_URL}/{resource_id}")
    assert resp.status_code == 204

    # Confirm it's gone.
    resp = client.get(f"{_BASE_URL}/{resource_id}")
    assert resp.status_code == 404


def test_delete_unknown_resource_returns_404(client: TestClient) -> None:
    """DELETE on a non-existent resource returns HTTP 404."""
    resp = client.delete(f"{_BASE_URL}/00000000-0000-4000-8000-000000000099")
    assert resp.status_code == 404
