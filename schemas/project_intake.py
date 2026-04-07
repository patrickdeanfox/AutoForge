"""Pydantic v2 schema for the AutoForge Layer 1/2 project intake form.

ProjectIntake represents the data submitted by the engineer via the project intake
wizard. It contains all project-specific fields that the engineer fills in.

The ManifestMerger (``orchestration/manifest_merger.py``) merges this with the
Layer 0 EmployerProfile to produce a fully validated ProjectManifest.

Fields NOT present here — injected by the merger at merge time:
- ``employer_standards_version`` — pulled from EmployerProfile.identity
- ``observability`` — built from EmployerProfile.observability_defaults
- ``created_at`` — set to UTC now
- ``approved_at`` / ``approved_by`` — set when the engineer approves the manifest
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

from schemas.project_manifest import AudienceDefinition, HumanGate, TechnicalConfig

# ============================================================
# CONFIG
# ============================================================

_PROJECT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")

# Default human gates injected when the engineer does not specify custom ones.
# Every project must have at minimum a manifest approval gate and a PR merge gate.
_DEFAULT_HUMAN_GATES: list[HumanGate] = [
    HumanGate(
        gate_id="gate-manifest-approval",
        description=(
            "Engineer reviews and approves the project manifest before execution begins."
        ),
        trigger="before_execution_start",
        telegram_command="/approve manifest",
        required=True,
    ),
    HumanGate(
        gate_id="gate-pr-merge",
        description="Engineer reviews and merges the agent-created pull request.",
        trigger="before_pr_merge",
        telegram_command="/queue",
        required=True,
    ),
]


# ============================================================
# SCHEMA
# ============================================================


class ProjectIntake(BaseModel):
    """Layer 1/2 project intake form data submitted by the engineer.

    This is the input to ``ManifestMerger.merge()``. All employer-derived fields
    (observability, employer_standards_version, timestamps) are absent here — they
    are injected by the merger based on the active EmployerProfile.

    Args:
        project_id: Lowercase alphanumeric slug, hyphens allowed, min 2 chars.
        project_name: Human-readable project name.
        client_name: The customer or client this project is for.
        problem_statement: What business problem this project solves.
        success_metrics: Measurable outcomes that define project success. At least one required.
        audience: Who will use the delivered artifact and how.
        technical: Technology choices for this project.
        human_gates: Checkpoints requiring human approval. Defaults to manifest + PR gates.
        decision_records: DR IDs referenced by this project (e.g. ["DR-001", "DR-002"]).
        knowledge_resources: KnowledgeResource UUIDs referenced by this project.
        known_constraints: Known limitations, quirks, or hard requirements.
        notes: Free-form notes for the engineer or planning agent.
    """

    project_id: str
    project_name: str
    client_name: str
    problem_statement: str
    success_metrics: list[str] = Field(..., min_length=1)
    audience: AudienceDefinition
    technical: TechnicalConfig
    human_gates: list[HumanGate] = Field(
        default_factory=lambda: list(_DEFAULT_HUMAN_GATES)
    )
    decision_records: list[str] = Field(default_factory=list)
    knowledge_resources: list[str] = Field(default_factory=list)
    known_constraints: list[str] = Field(default_factory=list)
    notes: str = ""

    @field_validator("project_id")
    @classmethod
    def validate_project_id_slug(cls, v: str) -> str:
        """Enforce lowercase alphanumeric + hyphen slug format for project_id."""
        if len(v) < 2:
            raise ValueError("project_id must be at least 2 characters long")
        if not _PROJECT_ID_RE.match(v):
            raise ValueError(
                "project_id must be lowercase alphanumeric characters and hyphens only, "
                "must start and end with an alphanumeric character. "
                f"Got: {v!r}"
            )
        return v

    @field_validator("success_metrics")
    @classmethod
    def validate_success_metrics_not_empty(cls, v: list[str]) -> list[str]:
        """Ensure no success metric is an empty or whitespace-only string."""
        for i, metric in enumerate(v):
            if not metric.strip():
                raise ValueError(f"success_metrics[{i}] must not be an empty string")
        return v
