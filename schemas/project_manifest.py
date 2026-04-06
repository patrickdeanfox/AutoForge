"""Pydantic v2 schema for the AutoForge Layer 2 Project Manifest.

The project manifest is the per-project source of truth. It merges Layer 0 employer
standards with project-specific context and is human-approved before any execution begins.
No agent writes a line of code for a project until its manifest has an approved_at timestamp
and an approved_by value.
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


# ============================================================
# Enums
# ============================================================


class DeliveryType(str, Enum):
    """The primary artifact type this project delivers."""

    api = "api"
    script = "script"
    pipeline = "pipeline"
    dashboard = "dashboard"
    agent = "agent"
    library = "library"
    cli = "cli"
    other = "other"


class TechnicalLevel(str, Enum):
    """The technical sophistication of the primary audience."""

    non_technical = "non_technical"
    semi_technical = "semi_technical"
    technical = "technical"
    expert = "expert"


class InteractionMode(str, Enum):
    """How end-users or callers interact with the delivered artifact."""

    cli = "cli"
    api = "api"
    dashboard = "dashboard"
    scheduled = "scheduled"
    telegram = "telegram"


# ============================================================
# Sub-models
# ============================================================


class AudienceDefinition(BaseModel):
    """Describes who will use the project and how."""

    primary_users: list[str]
    technical_level: TechnicalLevel
    interaction_modes: list[InteractionMode]


class TechnicalConfig(BaseModel):
    """Technology choices for the project.

    ``required_tools`` and ``languages`` must always be populated. ``forbidden_tools``
    is checked against every dependency before installation.
    """

    delivery_type: DeliveryType
    required_tools: list[str]
    forbidden_tools: list[str] = []
    languages: list[str]
    frameworks: list[str]
    data_stores: list[str]
    ci_cd: str


class ObservabilityConfig(BaseModel):
    """Observability configuration for a specific project.

    Overrides or extends the employer-level observability defaults defined in
    ``EmployerProfile.observability_defaults``.
    """

    logging_platform: str
    metrics_platform: str
    tracing_enabled: bool
    error_tracking: str | None = None
    cost_tracking_enabled: bool = True


class HumanGate(BaseModel):
    """A checkpoint in the agent workflow that requires human approval before proceeding.

    Human gates are used to enforce review at critical decision points such as
    deploying to staging, merging a breaking change, or releasing to production.
    """

    gate_id: str
    description: str
    trigger: str
    telegram_command: str | None = None
    required: bool = True


# ============================================================
# Root model
# ============================================================

_PROJECT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")


class ProjectManifest(BaseModel):
    """Layer 2 — Project Manifest.

    The single source of truth for a customer project. Agents must read this before
    writing a single line of code. The manifest is considered active only when both
    ``approved_at`` and ``approved_by`` are set.
    """

    schema_version: str = "1.0"
    manifest_version: int = 1
    project_id: str
    project_name: str
    client_name: str
    problem_statement: str
    success_metrics: list[str]
    audience: AudienceDefinition
    technical: TechnicalConfig
    observability: ObservabilityConfig
    human_gates: list[HumanGate]
    decision_records: list[str] = Field(
        default_factory=list,
        description="List of Decision Record IDs (DR-NNN) referenced by this project.",
    )
    knowledge_resources: list[str] = Field(
        default_factory=list,
        description="List of KnowledgeResource UUIDs referenced by this project.",
    )
    employer_standards_version: str
    created_at: datetime
    approved_at: datetime | None = None
    approved_by: str | None = None
    known_constraints: list[str] = []
    notes: str = ""

    @field_validator("project_id")
    @classmethod
    def validate_project_id_slug(cls, v: str) -> str:
        """Enforce lowercase alphanumeric + hyphen slug format for project_id.

        Valid examples: ``my-project``, ``acme-onboarding-v2``
        Invalid examples: ``MyProject``, ``-bad-start``, ``bad-end-``
        """
        if len(v) < 2:
            raise ValueError("project_id must be at least 2 characters long")
        if not _PROJECT_ID_RE.match(v):
            raise ValueError(
                "project_id must be lowercase alphanumeric characters and hyphens only, "
                "must start and end with an alphanumeric character. "
                f"Got: {v!r}"
            )
        return v

    @model_validator(mode="after")
    def require_both_approval_fields_together(self) -> "ProjectManifest":
        """Ensure approved_at and approved_by are always set or unset together."""
        has_at = self.approved_at is not None
        has_by = self.approved_by is not None
        if has_at != has_by:
            raise ValueError(
                "approved_at and approved_by must both be set or both be None — "
                "partial approval state is not valid"
            )
        return self
