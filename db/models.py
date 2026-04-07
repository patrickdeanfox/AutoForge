"""SQLAlchemy ORM models for AutoForge.

Covers four core tables:
- projects        — customer project registry
- agent_runs      — every agent execution record
- cost_records    — Anthropic API spend per run
- human_gates     — pending engineer approvals
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Index, Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base

# ============================================================
# MODELS
# ============================================================


class Project(Base):
    """Customer project managed by AutoForge.

    Tracks project lifecycle from intake through completion, linking to
    the project manifest and GitHub repository.

    Valid status values: intake, knowledge_building, planning, execution,
    qa, complete, archived.
    """

    __tablename__ = "projects"

    id: Mapped[Any] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        nullable=False,
    )
    project_id: Mapped[str] = mapped_column(
        nullable=False,
        unique=True,
    )
    name: Mapped[str] = mapped_column(
        nullable=False,
    )
    client_name: Mapped[str] = mapped_column(
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        nullable=False,
        server_default="intake",
    )
    manifest_path: Mapped[str | None] = mapped_column(
        nullable=True,
    )
    github_repo: Mapped[str | None] = mapped_column(
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )

    def __init__(
        self,
        project_id: str,
        name: str,
        client_name: str,
        status: str = "intake",
        manifest_path: str | None = None,
        github_repo: str | None = None,
        approved_at: datetime | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialise a Project with Python-level defaults applied immediately."""
        super().__init__(**kwargs)
        self.project_id = project_id
        self.name = name
        self.client_name = client_name
        self.status = status
        self.manifest_path = manifest_path
        self.github_repo = github_repo
        self.approved_at = approved_at

    def __repr__(self) -> str:
        return (
            f"<Project id={self.id!r} project_id={self.project_id!r} "
            f"status={self.status!r}>"
        )


class AgentRun(Base):
    """Record of a single agent execution.

    Captures timing, token usage, outcome, and optional error details for
    every agent invocation in the system.

    Valid status values: running, success, failed, escalated, cancelled.
    """

    __tablename__ = "agent_runs"

    id: Mapped[Any] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        nullable=False,
    )
    run_id: Mapped[str] = mapped_column(
        nullable=False,
        unique=True,
    )
    project_id: Mapped[str] = mapped_column(
        nullable=False,
    )
    agent_name: Mapped[str] = mapped_column(
        nullable=False,
    )
    issue_id: Mapped[str | None] = mapped_column(
        nullable=True,
    )
    branch: Mapped[str | None] = mapped_column(
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        nullable=False,
        server_default="running",
    )
    started_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )
    duration_ms: Mapped[int | None] = mapped_column(
        nullable=True,
    )
    tokens_in: Mapped[int] = mapped_column(
        nullable=False,
        server_default="0",
    )
    tokens_out: Mapped[int] = mapped_column(
        nullable=False,
        server_default="0",
    )
    model: Mapped[str | None] = mapped_column(
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    run_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default="{}",
    )

    __table_args__ = (
        Index("idx_agent_runs_project_id", "project_id"),
        Index("idx_agent_runs_status", "status"),
    )

    def __init__(
        self,
        run_id: str,
        project_id: str,
        agent_name: str,
        status: str = "running",
        issue_id: str | None = None,
        branch: str | None = None,
        completed_at: datetime | None = None,
        duration_ms: int | None = None,
        tokens_in: int = 0,
        tokens_out: int = 0,
        model: str | None = None,
        error_message: str | None = None,
        run_metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialise an AgentRun with Python-level defaults applied immediately."""
        super().__init__(**kwargs)
        self.run_id = run_id
        self.project_id = project_id
        self.agent_name = agent_name
        self.status = status
        self.issue_id = issue_id
        self.branch = branch
        self.completed_at = completed_at
        self.duration_ms = duration_ms
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.model = model
        self.error_message = error_message
        self.run_metadata = run_metadata if run_metadata is not None else {}

    def __repr__(self) -> str:
        return (
            f"<AgentRun id={self.id!r} run_id={self.run_id!r} "
            f"agent_name={self.agent_name!r} status={self.status!r}>"
        )


class CostRecord(Base):
    """Anthropic API cost record for a single agent run.

    Stores token counts and calculated USD cost per model per run, used
    by the cost tracking dashboard and spend reporting.
    """

    __tablename__ = "cost_records"

    id: Mapped[Any] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        nullable=False,
    )
    run_id: Mapped[str] = mapped_column(
        nullable=False,
    )
    project_id: Mapped[str] = mapped_column(
        nullable=False,
    )
    model: Mapped[str] = mapped_column(
        nullable=False,
    )
    tokens_in: Mapped[int] = mapped_column(
        nullable=False,
    )
    tokens_out: Mapped[int] = mapped_column(
        nullable=False,
    )
    cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 6),
        nullable=False,
    )
    recorded_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (Index("idx_cost_records_project_id", "project_id"),)

    def __repr__(self) -> str:
        return (
            f"<CostRecord id={self.id!r} run_id={self.run_id!r} "
            f"model={self.model!r} cost_usd={self.cost_usd!r}>"
        )


class HumanGate(Base):
    """Pending engineer approval gate.

    Created whenever an agent requires human intervention — spec approvals,
    manifest locks, PR merges, decision-needed items, or stuck agents.

    Valid gate_type values: spec_approval, manifest_lock, pr_merge,
    decision_needed, needs_human.

    Valid status values: pending, approved, rejected, expired.
    """

    __tablename__ = "human_gates"

    id: Mapped[Any] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        nullable=False,
    )
    gate_id: Mapped[str] = mapped_column(
        nullable=False,
        unique=True,
    )
    project_id: Mapped[str] = mapped_column(
        nullable=False,
    )
    gate_type: Mapped[str] = mapped_column(
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        nullable=False,
        server_default="pending",
    )
    github_issue_url: Mapped[str | None] = mapped_column(
        nullable=True,
    )
    telegram_message_id: Mapped[str | None] = mapped_column(
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )
    resolved_by: Mapped[str | None] = mapped_column(
        nullable=True,
    )

    __table_args__ = (
        Index("idx_human_gates_project_id", "project_id"),
        Index("idx_human_gates_status", "status"),
    )

    def __init__(
        self,
        gate_id: str,
        project_id: str,
        gate_type: str,
        description: str,
        status: str = "pending",
        github_issue_url: str | None = None,
        telegram_message_id: str | None = None,
        resolved_at: datetime | None = None,
        resolved_by: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialise a HumanGate with Python-level defaults applied immediately."""
        super().__init__(**kwargs)
        self.gate_id = gate_id
        self.project_id = project_id
        self.gate_type = gate_type
        self.description = description
        self.status = status
        self.github_issue_url = github_issue_url
        self.telegram_message_id = telegram_message_id
        self.resolved_at = resolved_at
        self.resolved_by = resolved_by

    def __repr__(self) -> str:
        return (
            f"<HumanGate id={self.id!r} gate_id={self.gate_id!r} "
            f"gate_type={self.gate_type!r} status={self.status!r}>"
        )
