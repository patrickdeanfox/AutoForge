"""Tests for BaseAgent abstract class and ResearchAgent skeleton.

Covers:
- BaseAgent cannot be instantiated directly (abstract method enforcement)
- Concrete subclass instantiates successfully with valid manifest + employer profile
- run_id format: starts with "run-", is unique per instance
- manifest is loaded as a ProjectManifest instance
- employer is loaded as an EmployerProfile instance
- step_context emits step_start and step_complete log events on clean exit
- step_context emits step_failed and re-raises on exception
- step_context duration_ms is a non-negative integer on both success and failure
- tokens_used on StepContext is mutable (agent can increment it)
- ResearchAgent instantiates with seed_urls
- ResearchAgent.run() returns a dict with "status" and "urls_processed" keys
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from agents.base.base_agent import BaseAgent
from agents.research.research_agent import ResearchAgent
from schemas.employer_profile import EmployerProfile
from schemas.project_manifest import ProjectManifest

# ============================================================
# JSON fixtures
# ============================================================

_EMPLOYER_PROFILE_JSON: dict[str, Any] = {
    "schema_version": "1.0",
    "identity": {
        "employer_name": "Test Corp",
        "department": "Engineering",
        "standards_version": "1.0",
        "standards_owner_email": "eng@testcorp.com",
        "last_updated": "2026-01-01",
    },
    "code_standards": {
        "python_style": "pep8",
        "js_style": "airbnb",
        "max_line_length": 100,
        "max_function_complexity": 10,
        "min_test_coverage": 80,
        "required_type_hints": True,
        "required_docstrings": True,
        "required_repo_files": ["README.md"],
        "forbidden_patterns": [],
    },
    "git_rules": {
        "branching_strategy": "github_flow",
        "branch_prefixes": {"feature": "feature/", "fix": "fix/"},
        "commit_format": "conventional_commits",
        "pr_min_reviewers": 1,
        "protected_branches": ["main"],
        "squash_merges": True,
        "require_signed_commits": False,
    },
    "security_baseline": {
        "no_hardcoded_secrets": True,
        "secrets_manager": "pass",
        "compliance_frameworks": [],
        "no_pii_in_logs": True,
        "owasp_checks_required": True,
        "approved_auth_patterns": [],
    },
    "deployment_rules": {
        "deployment_windows": [],
        "environments": ["dev", "staging", "prod"],
        "requires_cab_approval": False,
        "rollback_procedure_required": True,
    },
    "observability_defaults": {
        "logging_platform": "structlog",
        "log_format": "json",
        "metrics_platform": "prometheus",
        "tracing_enabled": True,
        "required_log_fields": ["timestamp", "level", "service", "trace_id", "run_id"],
    },
    "approved_technologies": {
        "languages": ["python"],
        "cloud_platforms": [],
        "data_stores": [],
        "ci_cd_tools": [],
        "forbidden_technologies": [],
    },
}

_PROJECT_MANIFEST_JSON: dict[str, Any] = {
    "schema_version": "1.0",
    "manifest_version": 1,
    "project_id": "test-project",
    "project_name": "Test Project",
    "client_name": "Test Client",
    "problem_statement": "Build a test harness.",
    "success_metrics": ["All tests pass"],
    "audience": {
        "primary_users": ["engineers"],
        "technical_level": "technical",
        "interaction_modes": ["api"],
    },
    "technical": {
        "delivery_type": "api",
        "required_tools": ["pytest"],
        "forbidden_tools": [],
        "languages": ["python"],
        "frameworks": ["fastapi"],
        "data_stores": ["postgresql"],
        "ci_cd": "github_actions",
    },
    "observability": {
        "logging_platform": "structlog",
        "metrics_platform": "prometheus",
        "tracing_enabled": True,
        "cost_tracking_enabled": True,
    },
    "human_gates": [
        {
            "gate_id": "gate-001",
            "description": "Approve deployment to staging",
            "trigger": "pr_merged",
            "required": True,
        }
    ],
    "employer_standards_version": "1.0",
    "created_at": "2026-01-01T00:00:00",
    "approved_at": "2026-01-02T00:00:00",
    "approved_by": "engineer@testcorp.com",
    "known_constraints": [],
    "notes": "",
}


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture()
def employer_profile_path(tmp_path: Path) -> Path:
    """Write employer profile JSON to a temp file and return its path."""
    p = tmp_path / "employer_profile.json"
    p.write_text(json.dumps(_EMPLOYER_PROFILE_JSON), encoding="utf-8")
    return p


@pytest.fixture()
def manifest_path(tmp_path: Path) -> Path:
    """Write project manifest JSON to a temp file and return its path."""
    p = tmp_path / "project_manifest.json"
    p.write_text(json.dumps(_PROJECT_MANIFEST_JSON), encoding="utf-8")
    return p


# ============================================================
# Minimal concrete subclass for testing BaseAgent
# ============================================================


class _ConcreteAgent(BaseAgent):
    """Minimal concrete BaseAgent subclass used only in tests."""

    service_name = "test-agent"

    async def run(self) -> dict[str, Any]:
        """Return a trivial result dict."""
        return {"status": "ok"}


# ============================================================
# BaseAgent — instantiation tests
# ============================================================


def test_base_agent_cannot_be_instantiated_directly(
    manifest_path: Path,
    employer_profile_path: Path,
) -> None:
    """BaseAgent is abstract and must not be instantiatable on its own."""
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        BaseAgent(  # type: ignore[abstract]
            project_id="test-project",
            issue_id="GH-1",
            manifest_path=manifest_path,
            employer_profile_path=employer_profile_path,
        )


def test_concrete_agent_instantiates_successfully(
    manifest_path: Path,
    employer_profile_path: Path,
) -> None:
    """A concrete BaseAgent subclass with a valid manifest and profile instantiates cleanly."""
    agent = _ConcreteAgent(
        project_id="test-project",
        issue_id="GH-1",
        manifest_path=manifest_path,
        employer_profile_path=employer_profile_path,
    )
    assert agent is not None


# ============================================================
# BaseAgent — run_id tests
# ============================================================


def test_run_id_starts_with_run_prefix(
    manifest_path: Path,
    employer_profile_path: Path,
) -> None:
    """run_id must start with the 'run-' prefix."""
    agent = _ConcreteAgent(
        project_id="test-project",
        issue_id="GH-1",
        manifest_path=manifest_path,
        employer_profile_path=employer_profile_path,
    )
    assert agent.run_id.startswith("run-")


def test_run_id_is_unique_per_instance(
    manifest_path: Path,
    employer_profile_path: Path,
) -> None:
    """Each agent instance must receive a distinct run_id."""
    agent_a = _ConcreteAgent(
        project_id="test-project",
        issue_id="GH-1",
        manifest_path=manifest_path,
        employer_profile_path=employer_profile_path,
    )
    agent_b = _ConcreteAgent(
        project_id="test-project",
        issue_id="GH-1",
        manifest_path=manifest_path,
        employer_profile_path=employer_profile_path,
    )
    assert agent_a.run_id != agent_b.run_id


# ============================================================
# BaseAgent — schema loading tests
# ============================================================


def test_manifest_is_project_manifest_instance(
    manifest_path: Path,
    employer_profile_path: Path,
) -> None:
    """agent.manifest must be a validated ProjectManifest instance."""
    agent = _ConcreteAgent(
        project_id="test-project",
        issue_id="GH-1",
        manifest_path=manifest_path,
        employer_profile_path=employer_profile_path,
    )
    assert isinstance(agent.manifest, ProjectManifest)


def test_employer_is_employer_profile_instance(
    manifest_path: Path,
    employer_profile_path: Path,
) -> None:
    """agent.employer must be a validated EmployerProfile instance."""
    agent = _ConcreteAgent(
        project_id="test-project",
        issue_id="GH-1",
        manifest_path=manifest_path,
        employer_profile_path=employer_profile_path,
    )
    assert isinstance(agent.employer, EmployerProfile)


# ============================================================
# step_context — success path
# ============================================================


@pytest.mark.asyncio
async def test_step_context_emits_step_start_and_step_complete(
    manifest_path: Path,
    employer_profile_path: Path,
) -> None:
    """step_context must emit step_start on entry and step_complete on clean exit."""
    agent = _ConcreteAgent(
        project_id="test-project",
        issue_id="GH-1",
        manifest_path=manifest_path,
        employer_profile_path=employer_profile_path,
    )

    # structlog uses the first positional arg as the event string.
    # Capture all positional event names emitted via logger.info().
    info_events: list[str] = []

    def _capture_info(*args: Any, **kwargs: Any) -> None:
        if args:
            info_events.append(str(args[0]))

    agent.logger = MagicMock()
    agent.logger.info = MagicMock(side_effect=_capture_info)
    agent.logger.error = MagicMock()

    async with agent.step_context("test_step"):
        pass

    assert "step_start" in info_events
    assert "step_complete" in info_events
    assert "step_failed" not in info_events


@pytest.mark.asyncio
async def test_step_context_duration_ms_is_non_negative_on_success(
    manifest_path: Path,
    employer_profile_path: Path,
) -> None:
    """step_complete must carry a non-negative integer duration_ms."""
    agent = _ConcreteAgent(
        project_id="test-project",
        issue_id="GH-1",
        manifest_path=manifest_path,
        employer_profile_path=employer_profile_path,
    )

    captured_complete: dict[str, Any] = {}

    def _capture_info(*args: Any, **kwargs: Any) -> None:
        # structlog event is the first positional arg
        if args and args[0] == "step_complete":
            captured_complete.update(kwargs)

    agent.logger = MagicMock()
    agent.logger.info = MagicMock(side_effect=_capture_info)
    agent.logger.error = MagicMock()

    async with agent.step_context("measure_step"):
        pass

    assert "duration_ms" in captured_complete
    assert isinstance(captured_complete["duration_ms"], int)
    assert captured_complete["duration_ms"] >= 0


@pytest.mark.asyncio
async def test_step_context_tokens_used_is_mutable(
    manifest_path: Path,
    employer_profile_path: Path,
) -> None:
    """The agent must be able to increment ctx.tokens_used inside step_context."""
    agent = _ConcreteAgent(
        project_id="test-project",
        issue_id="GH-1",
        manifest_path=manifest_path,
        employer_profile_path=employer_profile_path,
    )

    captured_tokens: list[int] = []

    def _capture_info(*args: Any, **kwargs: Any) -> None:
        if args and args[0] == "step_complete":
            captured_tokens.append(kwargs.get("tokens_used", -1))

    agent.logger = MagicMock()
    agent.logger.info = MagicMock(side_effect=_capture_info)
    agent.logger.error = MagicMock()

    async with agent.step_context("llm_step") as ctx:
        ctx.tokens_used += 750

    assert captured_tokens == [750]


# ============================================================
# step_context — failure path
# ============================================================


@pytest.mark.asyncio
async def test_step_context_emits_step_failed_and_reraises_on_exception(
    manifest_path: Path,
    employer_profile_path: Path,
) -> None:
    """step_context must emit step_failed and re-raise the original exception."""
    agent = _ConcreteAgent(
        project_id="test-project",
        issue_id="GH-1",
        manifest_path=manifest_path,
        employer_profile_path=employer_profile_path,
    )

    captured_error: dict[str, Any] = {}

    def _capture_error(*args: Any, **kwargs: Any) -> None:
        # structlog event is the first positional arg
        if args:
            captured_error["event"] = str(args[0])
        captured_error.update(kwargs)

    agent.logger = MagicMock()
    agent.logger.info = MagicMock()
    agent.logger.error = MagicMock(side_effect=_capture_error)

    with pytest.raises(ValueError, match="boom"):
        async with agent.step_context("failing_step"):
            raise ValueError("boom")

    assert captured_error.get("event") == "step_failed"
    assert captured_error.get("outcome") == "failure"


@pytest.mark.asyncio
async def test_step_context_duration_ms_is_non_negative_on_failure(
    manifest_path: Path,
    employer_profile_path: Path,
) -> None:
    """step_failed must carry a non-negative integer duration_ms."""
    agent = _ConcreteAgent(
        project_id="test-project",
        issue_id="GH-1",
        manifest_path=manifest_path,
        employer_profile_path=employer_profile_path,
    )

    captured_error: dict[str, Any] = {}

    def _capture_error(*args: Any, **kwargs: Any) -> None:
        captured_error.update(kwargs)

    agent.logger = MagicMock()
    agent.logger.info = MagicMock()
    agent.logger.error = MagicMock(side_effect=_capture_error)

    with pytest.raises(RuntimeError):
        async with agent.step_context("failing_step"):
            raise RuntimeError("unexpected")

    assert isinstance(captured_error.get("duration_ms"), int)
    assert captured_error["duration_ms"] >= 0


# ============================================================
# ResearchAgent — instantiation
# ============================================================


def test_research_agent_instantiates_with_seed_urls(
    manifest_path: Path,
    employer_profile_path: Path,
) -> None:
    """ResearchAgent must instantiate cleanly with a list of seed URLs."""
    with patch("anthropic.Anthropic"):
        agent = ResearchAgent(
            project_id="test-project",
            issue_id="GH-2",
            manifest_path=manifest_path,
            employer_profile_path=employer_profile_path,
            seed_urls=["https://example.com/api", "https://example.com/docs"],
        )
    assert agent._seed_urls == ["https://example.com/api", "https://example.com/docs"]
    assert agent.service_name == "research-agent"


# ============================================================
# ResearchAgent — run()
# ============================================================


@pytest.mark.asyncio
async def test_research_agent_run_returns_expected_keys(
    manifest_path: Path,
    employer_profile_path: Path,
) -> None:
    """ResearchAgent.run() must return a dict with 'status' and 'urls_processed' keys."""
    with patch("anthropic.Anthropic"):
        agent = ResearchAgent(
            project_id="test-project",
            issue_id="GH-2",
            manifest_path=manifest_path,
            employer_profile_path=employer_profile_path,
            seed_urls=["https://example.com/api", "https://example.com/schema"],
        )

    result = await agent.run()

    assert "status" in result
    assert "urls_processed" in result
    assert result["status"] == "complete"
    assert result["urls_processed"] == 2


@pytest.mark.asyncio
async def test_research_agent_run_with_empty_seed_urls(
    manifest_path: Path,
    employer_profile_path: Path,
) -> None:
    """ResearchAgent.run() with no seed URLs should return urls_processed=0."""
    with patch("anthropic.Anthropic"):
        agent = ResearchAgent(
            project_id="test-project",
            issue_id="GH-2",
            manifest_path=manifest_path,
            employer_profile_path=employer_profile_path,
            seed_urls=[],
        )

    result = await agent.run()

    assert result["status"] == "complete"
    assert result["urls_processed"] == 0
    assert result["findings"] == []
