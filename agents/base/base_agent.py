"""AutoForge BaseAgent abstract class.

All AutoForge agents inherit from BaseAgent. It handles:
- Loading the employer profile (Layer 0) and project manifest (Layer 2) via Pydantic
- Structured JSON logging via structlog with all required observability fields
- A ``step_context()`` async context manager that emits step_start / step_complete /
  step_failed events with accurate duration_ms measurements
- Mutable token cost tracking per step via StepContext.tokens_used
- Unique run ID generation (``run-{uuid4}``) per agent instantiation
"""

from __future__ import annotations

import contextlib
import json
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar
from uuid import uuid4

import structlog

from schemas.employer_profile import EmployerProfile
from schemas.project_manifest import ProjectManifest

# ============================================================
# StepContext dataclass
# ============================================================


@dataclass
class StepContext:
    """Mutable context yielded by BaseAgent.step_context().

    The agent can increment ``tokens_used`` during a step to track LLM spend.
    ``start_time`` is a monotonic timestamp (seconds) captured at step entry.
    """

    step_name: str
    start_time: float
    tokens_used: int = field(default=0)
    metadata: dict[str, Any] = field(default_factory=dict)


# ============================================================
# BaseAgent
# ============================================================


class BaseAgent(ABC):
    """Abstract base class for all AutoForge agents.

    Subclasses must:
    - Override ``service_name`` as a class variable (e.g. ``"research-agent"``)
    - Implement the ``async def run(self) -> dict[str, Any]`` method

    Args:
        project_id: The project slug this agent is working on (e.g. ``"acme-onboarding"``).
        issue_id: The GitHub Issue identifier (e.g. ``"GH-42"``).
        manifest_path: Path to the project's ``project_manifest.json``.
        employer_profile_path: Path to ``config/employer_profile.json``.
    """

    service_name: ClassVar[str] = "base-agent"

    def __init__(
        self,
        project_id: str,
        issue_id: str,
        manifest_path: Path,
        employer_profile_path: Path,
    ) -> None:
        """Initialise the agent, loading Layer 0 and Layer 2 documents.

        Generates a unique ``run_id`` and binds a structlog logger with all required
        observability fields attached as context.

        Raises:
            FileNotFoundError: If either JSON file does not exist.
            pydantic.ValidationError: If either JSON file fails schema validation.
        """
        self.project_id = project_id
        self.issue_id = issue_id
        self.run_id = f"run-{uuid4()}"

        # Load Layer 0 — Employer Profile
        self.employer: EmployerProfile = EmployerProfile.model_validate(
            json.loads(employer_profile_path.read_text(encoding="utf-8"))
        )

        # Load Layer 2 — Project Manifest
        self.manifest: ProjectManifest = ProjectManifest.model_validate(
            json.loads(manifest_path.read_text(encoding="utf-8"))
        )

        # Bind structured logger with all required observability fields
        self.logger: structlog.stdlib.BoundLogger = structlog.get_logger(
            self.service_name
        ).bind(
            service=self.service_name,
            agent_id=self.run_id,
            project_id=self.project_id,
            issue_id=self.issue_id,
            run_id=self.run_id,
            trace_id="",  # Stubbed — OpenTelemetry wired in Phase 2
        )

    # ============================================================
    # Abstract interface
    # ============================================================

    @abstractmethod
    async def run(self) -> dict[str, Any]:
        """Execute the agent's primary task. Returns a result dict."""

    # ============================================================
    # Step context manager
    # ============================================================

    @contextlib.asynccontextmanager
    async def step_context(
        self,
        step_name: str,
        metadata: dict[str, Any] | None = None,
    ) -> AsyncIterator[StepContext]:
        """Async context manager that wraps a named agent step with observability events.

        Emits a ``step_start`` log on entry, ``step_complete`` on clean exit, and
        ``step_failed`` on exception. Duration (in milliseconds) and ``tokens_used``
        are recorded on exit events.

        Args:
            step_name: A short identifier for the step (e.g. ``"crawl_url"``).
            metadata: Optional arbitrary key/value context logged with the start event.

        Yields:
            StepContext: Mutable context object. The agent can increment
                ``ctx.tokens_used`` during the step to record LLM spend.

        Raises:
            Exception: Any exception raised inside the block is re-raised after the
                ``step_failed`` event is emitted.

        Example::

            async with self.step_context("write_implementation") as ctx:
                result = await self._call_llm(prompt)
                ctx.tokens_used += result.usage.total_tokens
        """
        ctx = StepContext(
            step_name=step_name,
            start_time=time.monotonic(),
            metadata=metadata or {},
        )

        # structlog uses the first positional argument as the "event" field in the
        # rendered JSON. Do not also pass event= as a keyword — it would conflict.
        self.logger.info(
            "step_start",
            step=step_name,
            duration_ms=0,
            tokens_used=0,
            outcome="success",
            metadata=ctx.metadata,
        )

        try:
            yield ctx
        except Exception:
            duration_ms = int((time.monotonic() - ctx.start_time) * 1000)
            self.logger.error(
                "step_failed",
                step=step_name,
                duration_ms=duration_ms,
                tokens_used=ctx.tokens_used,
                outcome="failure",
                metadata=ctx.metadata,
            )
            raise
        else:
            duration_ms = int((time.monotonic() - ctx.start_time) * 1000)
            self.logger.info(
                "step_complete",
                step=step_name,
                duration_ms=duration_ms,
                tokens_used=ctx.tokens_used,
                outcome="success",
                metadata=ctx.metadata,
            )
