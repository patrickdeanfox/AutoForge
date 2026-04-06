"""Pydantic v2 schema for AutoForge Decision Records.

Decision Records track every significant technology choice across the lifecycle
Unexplored -> Under Discussion -> Locked. Once locked, a Decision Record is an
immutable constraint for the project it belongs to.
"""

from __future__ import annotations

import re
from datetime import date
from enum import Enum

from pydantic import BaseModel, field_validator, model_validator


# ============================================================
# Enums
# ============================================================


class DecisionRecordStatus(str, Enum):
    """Lifecycle status of a Decision Record."""

    unexplored = "unexplored"
    under_discussion = "under_discussion"
    locked = "locked"


class DecisionCategory(str, Enum):
    """Broad category the decision falls into."""

    infrastructure = "infrastructure"
    library = "library"
    architecture = "architecture"
    integration = "integration"
    data = "data"


# ============================================================
# Sub-models
# ============================================================


class DecisionOption(BaseModel):
    """A single candidate option in a Decision Record."""

    name: str
    pros: list[str]
    cons: list[str]
    estimated_cost: str | None = None


# ============================================================
# Root model
# ============================================================


class DecisionRecord(BaseModel):
    """A structured record of a technology or architecture decision.

    IDs follow the format ``DR-NNN`` (e.g. ``DR-001``).  When ``status`` is
    ``locked``, both ``decision`` and ``rationale`` must be populated.
    """

    id: str
    title: str
    status: DecisionRecordStatus
    category: DecisionCategory
    context: str
    options: list[DecisionOption]
    decision: str | None = None
    rationale: str | None = None
    locked_by: str | None = None
    locked_date: date | None = None
    revisit_trigger: str | None = None
    created_date: date = date.today()
    project_id: str

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        """Ensure the Decision Record ID follows the DR-NNN format."""
        if not re.match(r"^DR-\d{3}$", v):
            raise ValueError(
                f"Decision Record id must match pattern DR-NNN (e.g. DR-001), got: {v!r}"
            )
        return v

    @model_validator(mode="after")
    def require_decision_and_rationale_when_locked(self) -> "DecisionRecord":
        """Enforce that decision and rationale are present when status is locked."""
        if self.status == DecisionRecordStatus.locked:
            if not self.decision:
                raise ValueError(
                    "decision must be set when status is 'locked'"
                )
            if not self.rationale:
                raise ValueError(
                    "rationale must be set when status is 'locked'"
                )
        return self
