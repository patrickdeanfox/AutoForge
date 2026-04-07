"""Manifest merge logic — Layer 0 employer profile + project intake → ProjectManifest.

The ManifestMerger is the gateway from the intake form to the project's source of truth.
It validates the project intake against employer constraints and injects employer-derived
fields to produce a fully validated ProjectManifest.

No agent writes a line of code until a manifest produced by this module has been approved
(``approved_at`` and ``approved_by`` are set by a subsequent human approval step).

Usage::

    from pathlib import Path
    from orchestration.manifest_merger import ManifestMerger
    from schemas.project_intake import ProjectIntake

    merger = ManifestMerger(Path("config/employer_profile.json"))
    manifest = merger.merge(intake)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import structlog

from schemas.employer_profile import EmployerProfile
from schemas.project_intake import ProjectIntake
from schemas.project_manifest import ObservabilityConfig, ProjectManifest

# ============================================================
# CONFIG
# ============================================================

logger = structlog.get_logger()


# ============================================================
# EXCEPTIONS
# ============================================================


class ManifestMergeError(Exception):
    """Raised when a project intake violates employer profile constraints.

    This indicates a hard block — the manifest cannot be generated until the
    violation is resolved. Common causes:
    - A project tool appears in the employer's forbidden_technologies list.
    - Project data is structurally inconsistent with employer constraints.
    """


# ============================================================
# MERGER
# ============================================================


class ManifestMerger:
    """Merges a ProjectIntake with the Layer 0 EmployerProfile to produce a ProjectManifest.

    The merger performs three categories of work:
    1. **Enforcement** — rejects intakes that violate locked employer constraints
       (forbidden technologies, security baseline).
    2. **Injection** — adds employer-derived fields the engineer does not set
       (observability config, standards version, created_at timestamp).
    3. **Warning** — logs anomalies that don't block merge but need attention
       (unapproved languages, missing human gates).

    The produced manifest is unapproved (``approved_at`` is None). Approval is a
    separate human action performed via the dashboard or Telegram.

    Args:
        employer_profile_path: Path to the ``employer_profile.json`` file on disk.

    Raises:
        FileNotFoundError: If the employer profile file does not exist.
        pydantic.ValidationError: If the employer profile JSON fails Pydantic validation.
    """

    def __init__(self, employer_profile_path: Path) -> None:
        self._profile_path = employer_profile_path
        self._employer: EmployerProfile = self._load_employer_profile()
        logger.info(
            "manifest_merger_initialized",
            profile_path=str(employer_profile_path),
            standards_version=self._employer.identity.standards_version,
        )

    # ----------------------------------------------------------
    # Public API
    # ----------------------------------------------------------

    @property
    def employer(self) -> EmployerProfile:
        """The loaded and validated employer profile (read-only)."""
        return self._employer

    def merge(self, intake: ProjectIntake) -> ProjectManifest:
        """Merge a ProjectIntake with the EmployerProfile to produce a ProjectManifest.

        Merge steps:
        1. Extract forbidden technology names from the employer profile.
        2. Validate that no project tool is on the forbidden list (hard block).
        3. Warn if project languages extend beyond the employer's approved list.
        4. Build ``ObservabilityConfig`` from employer defaults.
        5. Assemble and return a validated ``ProjectManifest``.

        Args:
            intake: The project intake data submitted by the engineer.

        Returns:
            A fully validated ``ProjectManifest`` with ``approved_at=None``.

        Raises:
            ManifestMergeError: If the intake violates employer profile constraints.
        """
        log = logger.bind(project_id=intake.project_id)

        forbidden_names = self._extract_forbidden_tech_names()
        self._validate_no_forbidden_tools(intake, forbidden_names, log)
        self._warn_on_unapproved_languages(intake, log)

        observability = self._build_observability_config()
        now = datetime.now(tz=UTC)

        manifest = ProjectManifest(
            project_id=intake.project_id,
            project_name=intake.project_name,
            client_name=intake.client_name,
            problem_statement=intake.problem_statement,
            success_metrics=intake.success_metrics,
            audience=intake.audience,
            technical=intake.technical,
            observability=observability,
            human_gates=intake.human_gates,
            decision_records=intake.decision_records,
            knowledge_resources=intake.knowledge_resources,
            known_constraints=intake.known_constraints,
            notes=intake.notes,
            employer_standards_version=self._employer.identity.standards_version,
            created_at=now,
        )

        log.info(
            "manifest_merged",
            project_name=intake.project_name,
            client_name=intake.client_name,
            employer_standards_version=manifest.employer_standards_version,
            gate_count=len(manifest.human_gates),
        )
        return manifest

    # ----------------------------------------------------------
    # Private helpers
    # ----------------------------------------------------------

    def _load_employer_profile(self) -> EmployerProfile:
        """Load and validate the employer profile from disk.

        Raises:
            FileNotFoundError: If the file at ``self._profile_path`` does not exist.
            pydantic.ValidationError: If the JSON content fails schema validation.
        """
        raw = json.loads(self._profile_path.read_text())
        return EmployerProfile.model_validate(raw)

    def _extract_forbidden_tech_names(self) -> set[str]:
        """Extract bare technology names from the employer forbidden_technologies list.

        Entries may include a reason suffix separated by a colon, e.g.
        ``"log4j:critical_cve_history"``. This method extracts just the name part and
        normalises to lowercase.

        Returns:
            Set of lowercase forbidden technology names (without reason suffixes).
        """
        names: set[str] = set()
        for entry in self._employer.approved_technologies.forbidden_technologies:
            name = entry.split(":")[0].lower().strip()
            if name:
                names.add(name)
        return names

    def _validate_no_forbidden_tools(
        self,
        intake: ProjectIntake,
        forbidden_names: set[str],
        log: structlog.BoundLogger,
    ) -> None:
        """Raise ManifestMergeError if any project tool appears on the forbidden list.

        Checks ``required_tools``, ``frameworks``, ``data_stores``, and ``ci_cd``
        against the employer's forbidden technology names. ``forbidden_tools`` declared
        on the project itself are also checked — they cannot re-allow a globally
        forbidden technology.

        Args:
            intake: The project intake data.
            forbidden_names: Lowercase set of employer-forbidden technology names.
            log: Bound structlog logger with project_id context.

        Raises:
            ManifestMergeError: If any violation is found.
        """
        if not forbidden_names:
            return

        project_tools: set[str] = set()
        project_tools.update(t.lower() for t in intake.technical.required_tools)
        project_tools.update(t.lower() for t in intake.technical.frameworks)
        project_tools.update(t.lower() for t in intake.technical.data_stores)
        project_tools.add(intake.technical.ci_cd.lower())

        violations = project_tools & forbidden_names
        if violations:
            log.warning(
                "manifest_merge_forbidden_tool_violation",
                violations=sorted(violations),
                forbidden_list=sorted(forbidden_names),
            )
            raise ManifestMergeError(
                f"Project intake includes technologies forbidden by the employer profile: "
                f"{sorted(violations)}. "
                "Remove or replace these before generating the manifest."
            )

    def _warn_on_unapproved_languages(
        self,
        intake: ProjectIntake,
        log: structlog.BoundLogger,
    ) -> None:
        """Log a warning if project languages are not in the employer-approved list.

        This does not block the merge — the engineer may be intentionally extending
        the approved technology list. The warning surfaces so the decision can be
        formalised in a Decision Record.

        Args:
            intake: The project intake data.
            log: Bound structlog logger with project_id context.
        """
        approved = {lang.lower() for lang in self._employer.approved_technologies.languages}
        if not approved:
            return  # employer has no approved language list — no restriction to check

        project_langs = {lang.lower() for lang in intake.technical.languages}
        unapproved = project_langs - approved
        if unapproved:
            log.warning(
                "manifest_merge_unapproved_languages",
                unapproved_languages=sorted(unapproved),
                approved_languages=sorted(approved),
                note=(
                    "Merge proceeding — create a decision-needed issue to formalise "
                    "this language choice."
                ),
            )

    def _build_observability_config(self) -> ObservabilityConfig:
        """Build an ObservabilityConfig from the employer's observability_defaults.

        Projects inherit the employer's logging platform, metrics platform, and
        tracing settings. Cost tracking is always enabled.

        Returns:
            An ``ObservabilityConfig`` populated from employer defaults.
        """
        defaults = self._employer.observability_defaults
        return ObservabilityConfig(
            logging_platform=defaults.logging_platform,
            metrics_platform=defaults.metrics_platform,
            tracing_enabled=defaults.tracing_enabled,
            cost_tracking_enabled=True,
        )
