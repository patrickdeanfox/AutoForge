"""Tests for the manifest merge logic (orchestration/manifest_merger.py).

Covers:
- Happy path: valid intake produces a valid manifest
- Employer-derived field injection (observability, standards version, created_at)
- Forbidden technology enforcement (hard block)
- Unapproved language warning (soft warn — does not block merge)
- Approval state (merged manifest is always unapproved)
- ManifestMerger with missing employer profile file
- ProjectIntake validation (slug format, empty metrics)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from orchestration.manifest_merger import ManifestMergeError, ManifestMerger
from schemas.project_intake import ProjectIntake
from schemas.project_manifest import (
    AudienceDefinition,
    DeliveryType,
    HumanGate,
    InteractionMode,
    TechnicalConfig,
    TechnicalLevel,
)


# ============================================================
# Fixtures
# ============================================================


def _employer_profile_dict(
    standards_version: str = "1.0",
    forbidden_technologies: list[str] | None = None,
    approved_languages: list[str] | None = None,
    logging_platform: str = "structlog",
    metrics_platform: str = "prometheus",
    tracing_enabled: bool = True,
) -> dict:
    """Build a minimal valid employer profile dict for testing."""
    return {
        "schema_version": "1.0",
        "identity": {
            "employer_name": "Acme Corp",
            "department": "Engineering",
            "standards_version": standards_version,
            "standards_owner_email": "eng@acme.com",
            "last_updated": "2026-01-01",
        },
        "approved_technologies": {
            "languages": approved_languages if approved_languages is not None else ["python"],
            "forbidden_technologies": (
                forbidden_technologies if forbidden_technologies is not None else []
            ),
        },
        "observability_defaults": {
            "logging_platform": logging_platform,
            "metrics_platform": metrics_platform,
            "tracing_enabled": tracing_enabled,
        },
    }


@pytest.fixture()
def employer_profile_file(tmp_path: Path) -> Path:
    """Write a minimal valid employer profile JSON to a temp file."""
    profile_path = tmp_path / "employer_profile.json"
    profile_path.write_text(json.dumps(_employer_profile_dict()))
    return profile_path


@pytest.fixture()
def merger(employer_profile_file: Path) -> ManifestMerger:
    """Return a ManifestMerger pointed at the temp employer profile."""
    return ManifestMerger(employer_profile_file)


def _valid_intake(**kwargs: object) -> ProjectIntake:
    """Build a minimal valid ProjectIntake for testing."""
    base: dict[str, object] = {
        "project_id": "acme-onboarding",
        "project_name": "Acme Onboarding Pipeline",
        "client_name": "Acme Corp",
        "problem_statement": "Automate customer onboarding.",
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
        "human_gates": [
            HumanGate(
                gate_id="gate-manifest-approval",
                description="Approve manifest.",
                trigger="before_execution_start",
            )
        ],
    }
    base.update(kwargs)
    return ProjectIntake(**base)  # type: ignore[arg-type]


# ============================================================
# ManifestMerger — initialisation
# ============================================================


class TestManifestMergerInit:
    """ManifestMerger loads and validates the employer profile on construction."""

    def test_loads_employer_profile_successfully(self, employer_profile_file: Path) -> None:
        m = ManifestMerger(employer_profile_file)
        assert m.employer.identity.employer_name == "Acme Corp"

    def test_raises_file_not_found_for_missing_profile(self, tmp_path: Path) -> None:
        missing = tmp_path / "does_not_exist.json"
        with pytest.raises(FileNotFoundError):
            ManifestMerger(missing)

    def test_raises_validation_error_for_invalid_profile_json(
        self, tmp_path: Path
    ) -> None:
        bad_profile = tmp_path / "bad.json"
        bad_profile.write_text(json.dumps({"schema_version": "1.0"}))
        with pytest.raises(Exception):  # pydantic ValidationError
            ManifestMerger(bad_profile)


# ============================================================
# ManifestMerger — happy path merge
# ============================================================


class TestManifestMergerHappyPath:
    """Valid intake produces a complete, correctly populated manifest."""

    def test_merge_returns_project_manifest(self, merger: ManifestMerger) -> None:
        from schemas.project_manifest import ProjectManifest

        intake = _valid_intake()
        manifest = merger.merge(intake)
        assert isinstance(manifest, ProjectManifest)

    def test_project_fields_are_carried_through(self, merger: ManifestMerger) -> None:
        intake = _valid_intake()
        manifest = merger.merge(intake)
        assert manifest.project_id == "acme-onboarding"
        assert manifest.project_name == "Acme Onboarding Pipeline"
        assert manifest.client_name == "Acme Corp"
        assert manifest.problem_statement == "Automate customer onboarding."
        assert manifest.success_metrics == ["Time-to-first-login < 2 days"]

    def test_technical_config_is_carried_through(self, merger: ManifestMerger) -> None:
        intake = _valid_intake()
        manifest = merger.merge(intake)
        assert manifest.technical.delivery_type == DeliveryType.api
        assert "fastapi" in manifest.technical.required_tools

    def test_human_gates_are_carried_through(self, merger: ManifestMerger) -> None:
        intake = _valid_intake()
        manifest = merger.merge(intake)
        assert len(manifest.human_gates) == 1
        assert manifest.human_gates[0].gate_id == "gate-manifest-approval"

    def test_known_constraints_and_notes_carried_through(
        self, merger: ManifestMerger
    ) -> None:
        intake = _valid_intake(known_constraints=["no PII in logs"], notes="Phase 0 test")
        manifest = merger.merge(intake)
        assert manifest.known_constraints == ["no PII in logs"]
        assert manifest.notes == "Phase 0 test"


# ============================================================
# ManifestMerger — employer-derived field injection
# ============================================================


class TestManifestMergerInjectedFields:
    """Employer-derived fields are correctly injected into the merged manifest."""

    def test_employer_standards_version_is_injected(
        self, tmp_path: Path
    ) -> None:
        profile_path = tmp_path / "profile.json"
        profile_path.write_text(
            json.dumps(_employer_profile_dict(standards_version="2.5"))
        )
        m = ManifestMerger(profile_path)
        manifest = m.merge(_valid_intake())
        assert manifest.employer_standards_version == "2.5"

    def test_observability_logging_platform_from_employer(
        self, tmp_path: Path
    ) -> None:
        profile_path = tmp_path / "profile.json"
        profile_path.write_text(
            json.dumps(_employer_profile_dict(logging_platform="datadog"))
        )
        m = ManifestMerger(profile_path)
        manifest = m.merge(_valid_intake())
        assert manifest.observability.logging_platform == "datadog"

    def test_observability_metrics_platform_from_employer(
        self, tmp_path: Path
    ) -> None:
        profile_path = tmp_path / "profile.json"
        profile_path.write_text(
            json.dumps(_employer_profile_dict(metrics_platform="cloudwatch"))
        )
        m = ManifestMerger(profile_path)
        manifest = m.merge(_valid_intake())
        assert manifest.observability.metrics_platform == "cloudwatch"

    def test_observability_tracing_enabled_from_employer(
        self, tmp_path: Path
    ) -> None:
        profile_path = tmp_path / "profile.json"
        profile_path.write_text(
            json.dumps(_employer_profile_dict(tracing_enabled=False))
        )
        m = ManifestMerger(profile_path)
        manifest = m.merge(_valid_intake())
        assert manifest.observability.tracing_enabled is False

    def test_cost_tracking_is_always_enabled(self, merger: ManifestMerger) -> None:
        manifest = merger.merge(_valid_intake())
        assert manifest.observability.cost_tracking_enabled is True

    def test_created_at_is_set_to_utc_now(self, merger: ManifestMerger) -> None:
        before = datetime.now(tz=UTC)
        manifest = merger.merge(_valid_intake())
        after = datetime.now(tz=UTC)
        assert before <= manifest.created_at <= after

    def test_approved_at_is_none_after_merge(self, merger: ManifestMerger) -> None:
        manifest = merger.merge(_valid_intake())
        assert manifest.approved_at is None

    def test_approved_by_is_none_after_merge(self, merger: ManifestMerger) -> None:
        manifest = merger.merge(_valid_intake())
        assert manifest.approved_by is None


# ============================================================
# ManifestMerger — forbidden technology enforcement
# ============================================================


class TestManifestMergerForbiddenTechnologies:
    """Project tools that appear on the employer forbidden list block the merge."""

    def _merger_with_forbidden(
        self, tmp_path: Path, forbidden: list[str]
    ) -> ManifestMerger:
        profile_path = tmp_path / "profile.json"
        profile_path.write_text(
            json.dumps(_employer_profile_dict(forbidden_technologies=forbidden))
        )
        return ManifestMerger(profile_path)

    def test_forbidden_required_tool_raises_merge_error(
        self, tmp_path: Path
    ) -> None:
        m = self._merger_with_forbidden(tmp_path, ["flask:prefer_fastapi"])
        intake = _valid_intake(
            technical=TechnicalConfig(
                delivery_type=DeliveryType.api,
                required_tools=["flask"],
                languages=["python"],
                frameworks=[],
                data_stores=["postgresql"],
                ci_cd="github-actions",
            )
        )
        with pytest.raises(ManifestMergeError, match="flask"):
            m.merge(intake)

    def test_forbidden_framework_raises_merge_error(self, tmp_path: Path) -> None:
        m = self._merger_with_forbidden(tmp_path, ["log4j:critical_cve_history"])
        intake = _valid_intake(
            technical=TechnicalConfig(
                delivery_type=DeliveryType.api,
                required_tools=["fastapi"],
                languages=["python"],
                frameworks=["log4j"],
                data_stores=["postgresql"],
                ci_cd="github-actions",
            )
        )
        with pytest.raises(ManifestMergeError, match="log4j"):
            m.merge(intake)

    def test_forbidden_data_store_raises_merge_error(self, tmp_path: Path) -> None:
        m = self._merger_with_forbidden(tmp_path, ["sqlite:not_approved_for_prod"])
        intake = _valid_intake(
            technical=TechnicalConfig(
                delivery_type=DeliveryType.api,
                required_tools=["fastapi"],
                languages=["python"],
                frameworks=[],
                data_stores=["sqlite"],
                ci_cd="github-actions",
            )
        )
        with pytest.raises(ManifestMergeError, match="sqlite"):
            m.merge(intake)

    def test_forbidden_ci_cd_raises_merge_error(self, tmp_path: Path) -> None:
        m = self._merger_with_forbidden(tmp_path, ["jenkins:legacy_tooling"])
        intake = _valid_intake(
            technical=TechnicalConfig(
                delivery_type=DeliveryType.api,
                required_tools=["fastapi"],
                languages=["python"],
                frameworks=[],
                data_stores=["postgresql"],
                ci_cd="jenkins",
            )
        )
        with pytest.raises(ManifestMergeError, match="jenkins"):
            m.merge(intake)

    def test_reason_suffix_after_colon_is_stripped(self, tmp_path: Path) -> None:
        """'flask:reason' in forbidden list still matches 'flask' in project tools."""
        m = self._merger_with_forbidden(
            tmp_path, ["flask:prefer_fastapi_for_new_projects"]
        )
        intake = _valid_intake(
            technical=TechnicalConfig(
                delivery_type=DeliveryType.api,
                required_tools=["flask"],
                languages=["python"],
                frameworks=[],
                data_stores=["postgresql"],
                ci_cd="github-actions",
            )
        )
        with pytest.raises(ManifestMergeError):
            m.merge(intake)

    def test_no_forbidden_technologies_allows_any_tool(
        self, merger: ManifestMerger
    ) -> None:
        """Empty forbidden list means no restriction — merge proceeds."""
        intake = _valid_intake()
        manifest = merger.merge(intake)
        assert manifest is not None

    def test_match_is_case_insensitive(self, tmp_path: Path) -> None:
        """'Flask' in project tools must match 'flask' in forbidden list."""
        m = self._merger_with_forbidden(tmp_path, ["flask:reason"])
        intake = _valid_intake(
            technical=TechnicalConfig(
                delivery_type=DeliveryType.api,
                required_tools=["Flask"],  # capitalised
                languages=["python"],
                frameworks=[],
                data_stores=["postgresql"],
                ci_cd="github-actions",
            )
        )
        with pytest.raises(ManifestMergeError):
            m.merge(intake)


# ============================================================
# ManifestMerger — unapproved language warning
# ============================================================


class TestManifestMergerUnapprovedLanguages:
    """Unapproved languages produce a warning but do not block the merge."""

    def test_unapproved_language_does_not_raise(self, tmp_path: Path) -> None:
        profile_path = tmp_path / "profile.json"
        profile_path.write_text(
            json.dumps(_employer_profile_dict(approved_languages=["python"]))
        )
        m = ManifestMerger(profile_path)
        intake = _valid_intake(
            technical=TechnicalConfig(
                delivery_type=DeliveryType.api,
                required_tools=["fastapi"],
                languages=["python", "rust"],  # rust not approved
                frameworks=[],
                data_stores=["postgresql"],
                ci_cd="github-actions",
            )
        )
        manifest = m.merge(intake)
        assert "rust" in manifest.technical.languages

    def test_unapproved_language_emits_warning_log(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # structlog writes to stdout by default in dev mode — capture via capsys.
        profile_path = tmp_path / "profile.json"
        profile_path.write_text(
            json.dumps(_employer_profile_dict(approved_languages=["python"]))
        )
        m = ManifestMerger(profile_path)
        intake = _valid_intake(
            technical=TechnicalConfig(
                delivery_type=DeliveryType.api,
                required_tools=["fastapi"],
                languages=["python", "go"],
                frameworks=[],
                data_stores=["postgresql"],
                ci_cd="github-actions",
            )
        )
        m.merge(intake)
        captured = capsys.readouterr()
        combined = (captured.out + captured.err).lower()
        assert "unapproved" in combined or "warning" in combined

    def test_empty_approved_languages_skips_check(
        self, tmp_path: Path
    ) -> None:
        """If the employer has no approved language list, the check is skipped."""
        profile_path = tmp_path / "profile.json"
        profile_path.write_text(
            json.dumps(_employer_profile_dict(approved_languages=[]))
        )
        m = ManifestMerger(profile_path)
        intake = _valid_intake(
            technical=TechnicalConfig(
                delivery_type=DeliveryType.api,
                required_tools=["fastapi"],
                languages=["cobol"],  # unconventional but no list to check against
                frameworks=[],
                data_stores=["postgresql"],
                ci_cd="github-actions",
            )
        )
        manifest = m.merge(intake)
        assert "cobol" in manifest.technical.languages


# ============================================================
# ProjectIntake — schema validation
# ============================================================


class TestProjectIntakeValidation:
    """ProjectIntake enforces slug format and success_metrics non-emptiness."""

    def test_valid_intake_creates_successfully(self) -> None:
        intake = _valid_intake()
        assert intake.project_id == "acme-onboarding"

    def test_invalid_project_id_uppercase_raises(self) -> None:
        with pytest.raises(ValidationError):
            _valid_intake(project_id="AcmeOnboarding")

    def test_invalid_project_id_leading_hyphen_raises(self) -> None:
        with pytest.raises(ValidationError):
            _valid_intake(project_id="-bad-start")

    def test_invalid_project_id_single_char_raises(self) -> None:
        with pytest.raises(ValidationError):
            _valid_intake(project_id="a")

    def test_empty_success_metrics_list_raises(self) -> None:
        with pytest.raises(ValidationError):
            _valid_intake(success_metrics=[])

    def test_whitespace_only_success_metric_raises(self) -> None:
        with pytest.raises(ValidationError):
            _valid_intake(success_metrics=["   "])

    def test_default_human_gates_are_injected(self) -> None:
        """When human_gates is omitted, two default gates are added."""
        intake = ProjectIntake(
            project_id="acme-onboarding",
            project_name="Acme",
            client_name="Acme Corp",
            problem_statement="Automate onboarding.",
            success_metrics=["KPI met"],
            audience=AudienceDefinition(
                primary_users=["team"],
                technical_level=TechnicalLevel.technical,
                interaction_modes=[InteractionMode.api],
            ),
            technical=TechnicalConfig(
                delivery_type=DeliveryType.api,
                required_tools=["fastapi"],
                languages=["python"],
                frameworks=[],
                data_stores=["postgresql"],
                ci_cd="github-actions",
            ),
        )
        gate_ids = {g.gate_id for g in intake.human_gates}
        assert "gate-manifest-approval" in gate_ids
        assert "gate-pr-merge" in gate_ids

    def test_decision_records_defaults_to_empty_list(self) -> None:
        intake = _valid_intake()
        assert intake.decision_records == []

    def test_knowledge_resources_defaults_to_empty_list(self) -> None:
        intake = _valid_intake()
        assert intake.knowledge_resources == []
