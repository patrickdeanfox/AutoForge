"""Conflict Detector for the AutoForge Research Agent.

After the crawl engine fetches and summarises external URLs, this module
compares each result against the Layer 0 EmployerProfile and emits
ConflictRecord objects for any violations found.

Three check families are implemented:
- Insecure transport   — HTTP URLs in the crawled URL or in the page summary
- Forbidden technology — tools listed in employer.approved_technologies.forbidden_technologies
- Forbidden pattern    — text patterns listed in employer.code_standards.forbidden_patterns

A ``typing.Protocol`` is used for crawl-result inputs so this module stays
decoupled from the crawl engine being built in parallel.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import uuid4

import structlog
from pydantic import BaseModel, Field

from schemas.employer_profile import EmployerProfile

# ============================================================
# CONFIG
# ============================================================

# Regex to locate bare http:// links inside body text.
_HTTP_LINK_RE = re.compile(r"http://[^\s\"'<>]+", re.IGNORECASE)

# Word-boundary wrapper — matches whole words only.
_WORD_BOUNDARY_RE_TEMPLATE = r"(?<![a-zA-Z0-9_])({term})(?![a-zA-Z0-9_])"

logger = structlog.get_logger(__name__)


# ============================================================
# PROTOCOL — accepted crawl result shape
# ============================================================


class CrawlResultLike(Protocol):
    """Structural interface for objects produced by the crawl engine.

    Any object that exposes these four attributes is accepted by
    ConflictDetector.detect — no explicit inheritance required.
    """

    url: str
    is_swagger: bool
    summary: str | None
    error: str | None


# ============================================================
# ENUMS AND MODELS
# ============================================================


class ConflictSeverity(StrEnum):
    """Severity levels for detected conflicts, ordered from lowest to highest."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ConflictRecord(BaseModel):
    """A single conflict detected between a crawl result and the EmployerProfile.

    Each record captures what was found, where it was found, which employer
    rule was violated, and a severity rating to guide triage priority.
    """

    conflict_id: str = Field(default_factory=lambda: str(uuid4()))
    severity: ConflictSeverity
    conflict_type: str
    description: str
    source_url: str | None = None
    employer_rule: str
    detected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ============================================================
# DETECTOR
# ============================================================


class ConflictDetector:
    """Checks crawl results against a Layer 0 EmployerProfile and returns conflicts.

    Instantiate once per research session with the loaded EmployerProfile, then
    call ``detect()`` with the list of crawl results after each crawl batch.

    Args:
        employer_profile: The parsed Layer 0 EmployerProfile for the current employer.
    """

    def __init__(self, employer_profile: EmployerProfile) -> None:
        """Store the employer profile and pre-compile forbidden-tech patterns."""
        self._profile = employer_profile
        # Pre-extract tech names (strip ":reason" suffixes) for efficient reuse.
        self._forbidden_tech_names: list[str] = [
            entry.split(":")[0].strip()
            for entry in employer_profile.approved_technologies.forbidden_technologies
            if entry.strip()
        ]

    def detect(self, crawl_results: list[CrawlResultLike]) -> list[ConflictRecord]:
        """Run all conflict checks against a batch of crawl results.

        Results that contain a non-None ``error`` field are skipped entirely —
        a failed crawl cannot reliably be checked for content violations.

        Args:
            crawl_results: Crawl result objects conforming to CrawlResultLike.

        Returns:
            A flat list of ConflictRecord objects, one per violation found.
            Returns an empty list when no conflicts are detected.
        """
        conflicts: list[ConflictRecord] = []

        for result in crawl_results:
            if result.error is not None:
                logger.debug(
                    "conflict_detector_skip_errored_result",
                    url=result.url,
                    error=result.error,
                )
                continue

            summary = result.summary or ""

            conflicts.extend(self._check_insecure_transport(result.url, summary))
            conflicts.extend(self._check_forbidden_technologies(result.url, summary))
            conflicts.extend(self._check_forbidden_patterns(result.url, summary))

        logger.info(
            "conflict_detection_complete",
            results_checked=sum(1 for r in crawl_results if r.error is None),
            conflicts_found=len(conflicts),
        )
        return conflicts

    # ----------------------------------------------------------
    # Private check methods
    # ----------------------------------------------------------

    def _check_insecure_transport(
        self, url: str, summary: str
    ) -> list[ConflictRecord]:
        """Detect insecure HTTP transport in the crawled URL and in page content.

        - If the crawled URL itself uses http:// → MEDIUM conflict.
        - For each unique http:// link found inside the page summary → LOW conflict.

        Args:
            url: The URL that was crawled.
            summary: Summarised text content of the crawled resource.

        Returns:
            A list of ConflictRecord objects (may be empty).
        """
        found: list[ConflictRecord] = []

        if url.lower().startswith("http://"):
            found.append(
                ConflictRecord(
                    severity=ConflictSeverity.MEDIUM,
                    conflict_type="insecure_transport",
                    description=(
                        f"Crawled URL uses insecure HTTP transport: {url}"
                    ),
                    source_url=url,
                    employer_rule=(
                        "security_baseline.owasp_checks_required — "
                        "all API endpoints must use HTTPS"
                    ),
                )
            )

        seen_http_links: set[str] = set()
        for match in _HTTP_LINK_RE.finditer(summary):
            http_link = match.group(0)
            if http_link not in seen_http_links:
                seen_http_links.add(http_link)
                found.append(
                    ConflictRecord(
                        severity=ConflictSeverity.LOW,
                        conflict_type="insecure_transport",
                        description=(
                            f"Page summary contains insecure HTTP link: {http_link}"
                        ),
                        source_url=url,
                        employer_rule=(
                            "security_baseline.owasp_checks_required — "
                            "referenced URLs should use HTTPS"
                        ),
                    )
                )

        return found

    def _check_forbidden_technologies(
        self, url: str, summary: str
    ) -> list[ConflictRecord]:
        """Detect mentions of forbidden technologies in the crawled page summary.

        Performs a case-insensitive whole-word search for each technology name
        extracted from employer.approved_technologies.forbidden_technologies.
        The ":reason" suffix present in many entries is stripped before matching.

        Args:
            url: The URL that was crawled.
            summary: Summarised text content of the crawled resource.

        Returns:
            A list of ConflictRecord objects (may be empty).
        """
        found: list[ConflictRecord] = []

        for tech_name in self._forbidden_tech_names:
            if not tech_name:
                continue
            pattern = re.compile(
                _WORD_BOUNDARY_RE_TEMPLATE.format(term=re.escape(tech_name)),
                re.IGNORECASE,
            )
            if pattern.search(summary):
                found.append(
                    ConflictRecord(
                        severity=ConflictSeverity.HIGH,
                        conflict_type="forbidden_technology",
                        description=(
                            f"Page summary references forbidden technology "
                            f"'{tech_name}': {url}"
                        ),
                        source_url=url,
                        employer_rule=(
                            f"approved_technologies.forbidden_technologies "
                            f"— '{tech_name}' is explicitly forbidden"
                        ),
                    )
                )

        return found

    def _check_forbidden_patterns(
        self, url: str, summary: str
    ) -> list[ConflictRecord]:
        """Detect code or text patterns flagged in employer.code_standards.forbidden_patterns.

        Each pattern entry is lowercased and checked as a plain substring against the
        lowercased summary. This is intentionally broad — more precise regex matching
        can be added when pattern entries grow more specific.

        Args:
            url: The URL that was crawled.
            summary: Summarised text content of the crawled resource.

        Returns:
            A list of ConflictRecord objects (may be empty).
        """
        found: list[ConflictRecord] = []
        summary_lower = summary.lower()

        for pattern in self._profile.code_standards.forbidden_patterns:
            if not pattern:
                continue
            if pattern.lower() in summary_lower:
                found.append(
                    ConflictRecord(
                        severity=ConflictSeverity.LOW,
                        conflict_type="forbidden_pattern",
                        description=(
                            f"Page summary contains forbidden pattern "
                            f"'{pattern}': {url}"
                        ),
                        source_url=url,
                        employer_rule=(
                            f"code_standards.forbidden_patterns — "
                            f"'{pattern}' is a forbidden pattern"
                        ),
                    )
                )

        return found
