"""Pydantic v2 schema for the AutoForge Layer 0 Employer Profile.

The employer profile is the fixed, global source of truth for code standards, git rules,
security requirements, deployment windows, and approved technologies. Fields in locked
sections cannot be overridden by any project manifest.
"""

from __future__ import annotations

from datetime import date
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator
from typing import Literal


# ============================================================
# Sub-models
# ============================================================


class CodeStandards(BaseModel):
    """Code quality and style standards applied to every project.

    All fields in this section are locked and cannot be overridden at the project level.
    """

    python_style: Literal["pep8"] = "pep8"
    js_style: Literal["airbnb", "google", "standard"] = "airbnb"
    max_line_length: int = 100
    max_function_complexity: int = 10
    min_test_coverage: int = 80
    required_type_hints: bool = True
    required_docstrings: bool = True
    required_repo_files: list[str] = [
        "README.md",
        "CHANGELOG.md",
        ".env.example",
        "Dockerfile",
    ]
    forbidden_patterns: list[str] = []

    @field_validator("min_test_coverage")
    @classmethod
    def validate_coverage_range(cls, v: int) -> int:
        """Ensure test coverage threshold is between 0 and 100."""
        if not 0 <= v <= 100:
            raise ValueError("min_test_coverage must be between 0 and 100")
        return v


class GitRules(BaseModel):
    """Git workflow rules applied to every project.

    All fields in this section are locked and cannot be overridden at the project level.
    """

    branching_strategy: Literal["github_flow", "gitflow", "trunk"] = "github_flow"
    branch_prefixes: dict[str, str] = {
        "feature": "feature/",
        "fix": "fix/",
        "chore": "chore/",
        "hotfix": "hotfix/",
    }
    commit_format: Literal["conventional_commits", "internal"] = "conventional_commits"
    pr_min_reviewers: int = 1
    protected_branches: list[str] = ["main"]
    squash_merges: bool = True
    require_signed_commits: bool = False


class SecurityBaseline(BaseModel):
    """Security requirements that apply to every project without exception.

    This model is frozen — instances are immutable after creation. The three
    boolean guardrails (no_hardcoded_secrets, no_pii_in_logs, owasp_checks_required)
    are validated to always be True and cannot be set to False.
    """

    model_config = ConfigDict(frozen=True)

    no_hardcoded_secrets: bool = True
    secrets_manager: str = "pass"
    compliance_frameworks: list[str] = []
    no_pii_in_logs: bool = True
    owasp_checks_required: bool = True
    approved_auth_patterns: list[str] = []

    @model_validator(mode="after")
    def enforce_security_guardrails(self) -> "SecurityBaseline":
        """Ensure the three non-negotiable security booleans are always True."""
        if not self.no_hardcoded_secrets:
            raise ValueError(
                "no_hardcoded_secrets must always be True — this field cannot be disabled"
            )
        if not self.no_pii_in_logs:
            raise ValueError(
                "no_pii_in_logs must always be True — this field cannot be disabled"
            )
        if not self.owasp_checks_required:
            raise ValueError(
                "owasp_checks_required must always be True — this field cannot be disabled"
            )
        return self


class DeploymentRules(BaseModel):
    """Deployment policy rules applied to every project.

    All fields in this section are locked and cannot be overridden at the project level.
    """

    deployment_windows: list[str] = []
    environments: list[str] = ["dev", "staging", "prod"]
    requires_cab_approval: bool = False
    rollback_procedure_required: bool = True


class ObservabilityDefaults(BaseModel):
    """Default observability configuration.

    Fields in this section can be overridden at the project level via the project manifest.
    """

    logging_platform: str = "structlog"
    log_format: Literal["json", "plaintext"] = "json"
    metrics_platform: str = "prometheus"
    tracing_enabled: bool = True
    required_log_fields: list[str] = [
        "timestamp",
        "level",
        "service",
        "trace_id",
        "run_id",
    ]


class ApprovedTechnologies(BaseModel):
    """Approved and forbidden technology lists.

    Fields in this section can be overridden or extended at the project level.
    Forbidden technologies include brief reasons embedded in the string, e.g.
    ``"log4j:critical_cve"``.
    """

    languages: list[str] = []
    cloud_platforms: list[str] = []
    data_stores: list[str] = []
    ci_cd_tools: list[str] = []
    forbidden_technologies: list[str] = []


class EmployerIdentity(BaseModel):
    """Identifying information for the employer/organization."""

    employer_name: str
    department: str
    standards_version: str
    standards_owner_email: EmailStr
    last_updated: date


# ============================================================
# Root model
# ============================================================


class EmployerProfile(BaseModel):
    """Layer 0 — Employer Profile.

    The global, fixed source of truth for AutoForge. Applied to every project without
    exception. Locked fields cannot be overridden by any project manifest.

    ``locked_fields`` is a class variable listing the top-level field names whose
    values must not be overridden by project manifests.
    """

    schema_version: str = "1.0"
    locked_fields: ClassVar[list[str]] = [
        "code_standards",
        "git_rules",
        "security_baseline",
        "deployment_rules",
    ]

    identity: EmployerIdentity
    code_standards: CodeStandards = CodeStandards()
    git_rules: GitRules = GitRules()
    security_baseline: SecurityBaseline = SecurityBaseline()
    deployment_rules: DeploymentRules = DeploymentRules()
    observability_defaults: ObservabilityDefaults = ObservabilityDefaults()
    approved_technologies: ApprovedTechnologies = ApprovedTechnologies()

    @model_validator(mode="after")
    def enforce_security_baseline(self) -> "EmployerProfile":
        """Re-validate security guardrails at the top level as a belt-and-suspenders check."""
        sb = self.security_baseline
        if not sb.no_hardcoded_secrets:
            raise ValueError(
                "EmployerProfile.security_baseline.no_hardcoded_secrets must always be True"
            )
        if not sb.no_pii_in_logs:
            raise ValueError(
                "EmployerProfile.security_baseline.no_pii_in_logs must always be True"
            )
        if not sb.owasp_checks_required:
            raise ValueError(
                "EmployerProfile.security_baseline.owasp_checks_required must always be True"
            )
        return self
