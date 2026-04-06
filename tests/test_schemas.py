"""Tests for the AutoForge Pydantic v2 schema layer.

Covers:
- EmployerProfile security baseline enforcement
- DecisionRecord status/field co-validation and ID format
- KnowledgeResource locator requirement
- ProjectManifest project_id slug validation and approval co-validation
"""

from __future__ import annotations

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from schemas.decision_record import (
    DecisionCategory,
    DecisionOption,
    DecisionRecord,
    DecisionRecordStatus,
)
from schemas.employer_profile import (
    EmployerIdentity,
    EmployerProfile,
    SecurityBaseline,
)
from schemas.knowledge_resource import KnowledgeResource, ResourceType
from schemas.project_manifest import (
    AudienceDefinition,
    DeliveryType,
    HumanGate,
    InteractionMode,
    ObservabilityConfig,
    ProjectManifest,
    TechnicalConfig,
    TechnicalLevel,
)


# ============================================================
# Helpers — minimal valid fixtures
# ============================================================


def _valid_identity() -> EmployerIdentity:
    return EmployerIdentity(
        employer_name="Acme Corp",
        department="Engineering",
        standards_version="1.0",
        standards_owner_email="eng@acme.com",
        last_updated=date.today(),
    )


def _valid_employer_profile() -> EmployerProfile:
    return EmployerProfile(identity=_valid_identity())


def _valid_decision_record(
    status: DecisionRecordStatus = DecisionRecordStatus.unexplored,
    **kwargs: object,
) -> DecisionRecord:
    base = {
        "id": "DR-001",
        "title": "Choose database",
        "status": status,
        "category": DecisionCategory.data,
        "context": "We need a relational store.",
        "options": [DecisionOption(name="PostgreSQL", pros=["mature"], cons=["ops overhead"])],
        "project_id": "test-project",
    }
    base.update(kwargs)
    return DecisionRecord(**base)  # type: ignore[arg-type]


def _valid_knowledge_resource(**kwargs: object) -> KnowledgeResource:
    base: dict[str, object] = {
        "project_id": "test-project",
        "resource_type": ResourceType.api_docs,
        "title": "Payments API",
        "description": "REST docs for the payments service",
        "source_url": "https://docs.example.com/payments",
    }
    base.update(kwargs)
    return KnowledgeResource(**base)  # type: ignore[arg-type]


def _valid_manifest(**kwargs: object) -> ProjectManifest:
    base: dict[str, object] = {
        "project_id": "acme-onboarding",
        "project_name": "Acme Onboarding Pipeline",
        "client_name": "Acme Corp",
        "problem_statement": "Automate the customer onboarding flow.",
        "success_metrics": ["Time-to-first-login < 2 days"],
        "audience": AudienceDefinition(
            primary_users=["onboarding team"],
            technical_level=TechnicalLevel.technical,
            interaction_modes=[InteractionMode.api],
        ),
        "technical": TechnicalConfig(
            delivery_type=DeliveryType.api,
            required_tools=["fastapi", "celery"],
            languages=["python"],
            frameworks=["fastapi"],
            data_stores=["postgresql"],
            ci_cd="github-actions",
        ),
        "observability": ObservabilityConfig(
            logging_platform="structlog",
            metrics_platform="prometheus",
            tracing_enabled=True,
        ),
        "human_gates": [
            HumanGate(
                gate_id="gate-staging",
                description="Approve staging deploy",
                trigger="before_staging_deploy",
            )
        ],
        "employer_standards_version": "1.0",
        "created_at": datetime(2025, 1, 1, 9, 0, 0),
    }
    base.update(kwargs)
    return ProjectManifest(**base)  # type: ignore[arg-type]


# ============================================================
# EmployerProfile — security baseline enforcement
# ============================================================


class TestEmployerProfileSecurityBaseline:
    """EmployerProfile must reject any attempt to disable security guardrails."""

    def test_valid_profile_creates_successfully(self) -> None:
        profile = _valid_employer_profile()
        assert profile.schema_version == "1.0"
        assert profile.security_baseline.no_hardcoded_secrets is True

    def test_rejects_no_hardcoded_secrets_false(self) -> None:
        """Setting no_hardcoded_secrets=False must raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SecurityBaseline(no_hardcoded_secrets=False)
        errors = exc_info.value.errors()
        assert any("no_hardcoded_secrets" in str(e) for e in errors)

    def test_rejects_no_pii_in_logs_false(self) -> None:
        """Setting no_pii_in_logs=False must raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SecurityBaseline(no_pii_in_logs=False)
        errors = exc_info.value.errors()
        assert any("no_pii_in_logs" in str(e) for e in errors)

    def test_rejects_owasp_checks_required_false(self) -> None:
        """Setting owasp_checks_required=False must raise ValidationError on SecurityBaseline."""
        with pytest.raises(ValidationError) as exc_info:
            SecurityBaseline(owasp_checks_required=False)
        errors = exc_info.value.errors()
        assert any("owasp_checks_required" in str(e) for e in errors)

    def test_locked_fields_class_var_lists_code_standards(self) -> None:
        """locked_fields must enumerate the sections that projects cannot override."""
        assert "code_standards" in EmployerProfile.locked_fields
        assert "security_baseline" in EmployerProfile.locked_fields

    def test_security_baseline_is_immutable(self) -> None:
        """SecurityBaseline is frozen — attempting mutation raises an error."""
        profile = _valid_employer_profile()
        with pytest.raises(Exception):
            profile.security_baseline.no_hardcoded_secrets = False  # type: ignore[misc]


# ============================================================
# DecisionRecord — status/field co-validation and ID format
# ============================================================


class TestDecisionRecordValidation:
    """DecisionRecord enforces ID format and locked-status field requirements."""

    def test_valid_unexplored_record(self) -> None:
        dr = _valid_decision_record()
        assert dr.id == "DR-001"
        assert dr.status == DecisionRecordStatus.unexplored

    def test_valid_locked_record_with_decision_and_rationale(self) -> None:
        dr = _valid_decision_record(
            status=DecisionRecordStatus.locked,
            decision="Use PostgreSQL",
            rationale="Strong community, proven at scale, aligns with employer tech stack.",
        )
        assert dr.decision == "Use PostgreSQL"

    def test_locked_status_requires_decision(self) -> None:
        """A locked DR without a decision value must raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            _valid_decision_record(
                status=DecisionRecordStatus.locked,
                rationale="Some rationale",
                # decision omitted
            )
        errors = exc_info.value.errors()
        assert any("decision" in str(e) for e in errors)

    def test_locked_status_requires_rationale(self) -> None:
        """A locked DR without a rationale value must raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            _valid_decision_record(
                status=DecisionRecordStatus.locked,
                decision="Use PostgreSQL",
                # rationale omitted
            )
        errors = exc_info.value.errors()
        assert any("rationale" in str(e) for e in errors)

    def test_id_format_dr_001_is_valid(self) -> None:
        dr = _valid_decision_record(id="DR-001")
        assert dr.id == "DR-001"

    def test_id_format_dr_999_is_valid(self) -> None:
        dr = _valid_decision_record(id="DR-999")
        assert dr.id == "DR-999"

    def test_id_format_dr_1_is_invalid(self) -> None:
        """DR-1 is invalid — must be exactly three digits."""
        with pytest.raises(ValidationError) as exc_info:
            _valid_decision_record(id="DR-1")
        assert "DR-NNN" in str(exc_info.value) or "DR-1" in str(exc_info.value)

    def test_id_format_abc_is_invalid(self) -> None:
        """Arbitrary strings without the DR- prefix are invalid."""
        with pytest.raises(ValidationError):
            _valid_decision_record(id="abc")

    def test_id_format_dr_00a_is_invalid(self) -> None:
        """Non-digit characters in the number segment are invalid."""
        with pytest.raises(ValidationError):
            _valid_decision_record(id="DR-00A")

    def test_under_discussion_does_not_require_decision(self) -> None:
        """under_discussion status must not require decision or rationale."""
        dr = _valid_decision_record(status=DecisionRecordStatus.under_discussion)
        assert dr.decision is None
        assert dr.rationale is None


# ============================================================
# KnowledgeResource — locator requirement
# ============================================================


class TestKnowledgeResourceValidation:
    """KnowledgeResource requires at least one of source_url or file_path."""

    def test_valid_with_source_url(self) -> None:
        resource = _valid_knowledge_resource()
        assert resource.source_url is not None

    def test_valid_with_file_path_only(self) -> None:
        resource = _valid_knowledge_resource(source_url=None, file_path="knowledge/spec.yaml")
        assert resource.file_path == "knowledge/spec.yaml"

    def test_valid_with_both_source_url_and_file_path(self) -> None:
        resource = _valid_knowledge_resource(file_path="knowledge/spec.yaml")
        assert resource.source_url is not None
        assert resource.file_path is not None

    def test_invalid_with_neither_source_url_nor_file_path(self) -> None:
        """Omitting both source_url and file_path must raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            _valid_knowledge_resource(source_url=None, file_path=None)
        errors = exc_info.value.errors()
        assert any("source_url" in str(e) or "file_path" in str(e) for e in errors)

    def test_id_defaults_to_uuid4_string(self) -> None:
        resource = _valid_knowledge_resource()
        import uuid
        uuid.UUID(resource.id)  # raises if not valid UUID

    def test_default_status_is_pending_crawl(self) -> None:
        from schemas.knowledge_resource import ResourceStatus
        resource = _valid_knowledge_resource()
        assert resource.status == ResourceStatus.pending_crawl


# ============================================================
# ProjectManifest — slug validation and approval co-validation
# ============================================================


class TestProjectManifestValidation:
    """ProjectManifest enforces project_id slug format and approval field co-presence."""

    def test_valid_manifest_creates_successfully(self) -> None:
        manifest = _valid_manifest()
        assert manifest.project_id == "acme-onboarding"
        assert manifest.approved_at is None
        assert manifest.approved_by is None

    def test_valid_project_id_two_chars(self) -> None:
        manifest = _valid_manifest(project_id="ab")
        assert manifest.project_id == "ab"

    def test_valid_project_id_with_numbers(self) -> None:
        manifest = _valid_manifest(project_id="acme-v2")
        assert manifest.project_id == "acme-v2"

    def test_invalid_project_id_uppercase(self) -> None:
        """Uppercase characters are not allowed in project_id."""
        with pytest.raises(ValidationError):
            _valid_manifest(project_id="AcmeProject")

    def test_invalid_project_id_leading_hyphen(self) -> None:
        """project_id cannot start with a hyphen."""
        with pytest.raises(ValidationError):
            _valid_manifest(project_id="-bad-start")

    def test_invalid_project_id_trailing_hyphen(self) -> None:
        """project_id cannot end with a hyphen."""
        with pytest.raises(ValidationError):
            _valid_manifest(project_id="bad-end-")

    def test_invalid_project_id_underscore(self) -> None:
        """Underscores are not allowed — only hyphens."""
        with pytest.raises(ValidationError):
            _valid_manifest(project_id="bad_underscore")

    def test_invalid_project_id_single_char(self) -> None:
        """project_id must be at least 2 characters."""
        with pytest.raises(ValidationError):
            _valid_manifest(project_id="a")

    def test_approved_at_and_approved_by_can_both_be_set(self) -> None:
        """Both approval fields set together is valid."""
        manifest = _valid_manifest(
            approved_at=datetime(2025, 2, 1, 10, 0, 0),
            approved_by="engineer@acme.com",
        )
        assert manifest.approved_at is not None
        assert manifest.approved_by == "engineer@acme.com"

    def test_approved_at_without_approved_by_is_invalid(self) -> None:
        """approved_at set without approved_by must raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            _valid_manifest(
                approved_at=datetime(2025, 2, 1, 10, 0, 0),
                approved_by=None,
            )
        errors = exc_info.value.errors()
        assert any("approved" in str(e) for e in errors)

    def test_approved_by_without_approved_at_is_invalid(self) -> None:
        """approved_by set without approved_at must raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            _valid_manifest(
                approved_at=None,
                approved_by="engineer@acme.com",
            )
        errors = exc_info.value.errors()
        assert any("approved" in str(e) for e in errors)

    def test_decision_records_defaults_to_empty_list(self) -> None:
        manifest = _valid_manifest()
        assert manifest.decision_records == []

    def test_manifest_version_defaults_to_1(self) -> None:
        manifest = _valid_manifest()
        assert manifest.manifest_version == 1
