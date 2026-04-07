"""Tests for agents.research.conflict_detector.

Covers all three check families (insecure transport, forbidden technology,
forbidden pattern), error-result skipping, UUID validity, UTC timestamps,
multi-conflict scenarios, and empty input handling.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from agents.research.conflict_detector import (
    ConflictDetector,
    ConflictSeverity,
)
from schemas.employer_profile import (
    ApprovedTechnologies,
    CodeStandards,
    EmployerIdentity,
    EmployerProfile,
)

# ============================================================
# TEST FIXTURES AND HELPERS
# ============================================================

_UUID4_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


@dataclass
class FakeCrawlResult:
    """Minimal crawl result stand-in that satisfies CrawlResultLike."""

    url: str
    is_swagger: bool = False
    summary: str | None = None
    error: str | None = None


def _make_profile(
    forbidden_technologies: list[str] | None = None,
    forbidden_patterns: list[str] | None = None,
) -> EmployerProfile:
    """Build a minimal EmployerProfile for testing."""
    return EmployerProfile(
        identity=EmployerIdentity(
            employer_name="Test Corp",
            department="Engineering",
            standards_version="1.0",
            standards_owner_email="eng@test.example.com",
            last_updated="2025-01-01",
        ),
        approved_technologies=ApprovedTechnologies(
            forbidden_technologies=forbidden_technologies or [],
        ),
        code_standards=CodeStandards(
            forbidden_patterns=forbidden_patterns or [],
        ),
    )


# ============================================================
# TESTS — insecure transport
# ============================================================


def test_no_conflicts_for_https_url_with_clean_summary() -> None:
    """HTTPS URL with no HTTP links in summary and no forbidden tech → empty list."""
    profile = _make_profile()
    detector = ConflictDetector(profile)
    result = FakeCrawlResult(url="https://api.example.com/docs", summary="All clean here.")
    conflicts = detector.detect([result])
    assert conflicts == []


def test_insecure_transport_http_url_raises_medium_conflict() -> None:
    """A crawled URL starting with http:// produces a MEDIUM insecure_transport conflict."""
    profile = _make_profile()
    detector = ConflictDetector(profile)
    result = FakeCrawlResult(url="http://api.example.com/docs", summary="No issues in text.")
    conflicts = detector.detect([result])

    assert len(conflicts) == 1
    c = conflicts[0]
    assert c.severity == ConflictSeverity.MEDIUM
    assert c.conflict_type == "insecure_transport"
    assert "http://api.example.com/docs" in c.description
    assert c.source_url == "http://api.example.com/docs"


def test_http_link_in_summary_raises_low_conflict() -> None:
    """An HTTPS crawl URL whose summary contains an http:// link → LOW conflict."""
    profile = _make_profile()
    detector = ConflictDetector(profile)
    result = FakeCrawlResult(
        url="https://api.example.com/docs",
        summary="See also http://old.example.com/legacy for reference.",
    )
    conflicts = detector.detect([result])

    assert len(conflicts) == 1
    c = conflicts[0]
    assert c.severity == ConflictSeverity.LOW
    assert c.conflict_type == "insecure_transport"
    assert "http://old.example.com/legacy" in c.description


def test_http_link_in_summary_deduplicates_same_url() -> None:
    """The same http:// link appearing twice in a summary produces only one LOW conflict."""
    profile = _make_profile()
    detector = ConflictDetector(profile)
    result = FakeCrawlResult(
        url="https://api.example.com/docs",
        summary="http://old.example.com http://old.example.com again here",
    )
    conflicts = detector.detect([result])

    insecure = [c for c in conflicts if c.conflict_type == "insecure_transport"]
    assert len(insecure) == 1


# ============================================================
# TESTS — forbidden technology
# ============================================================


def test_forbidden_technology_in_summary_raises_high_conflict() -> None:
    """A summary mentioning a forbidden tech name → HIGH forbidden_technology conflict."""
    profile = _make_profile(forbidden_technologies=["flask:lightweight_but_not_approved"])
    detector = ConflictDetector(profile)
    result = FakeCrawlResult(
        url="https://api.example.com",
        summary="This service is built with flask and sqlalchemy.",
    )
    conflicts = detector.detect([result])

    tech_conflicts = [c for c in conflicts if c.conflict_type == "forbidden_technology"]
    assert len(tech_conflicts) == 1
    c = tech_conflicts[0]
    assert c.severity == ConflictSeverity.HIGH
    assert "flask" in c.description.lower()


def test_forbidden_technology_matching_is_case_insensitive() -> None:
    """'Flask' in summary matches 'flask' in the forbidden list (case-insensitive)."""
    profile = _make_profile(forbidden_technologies=["flask:not_approved"])
    detector = ConflictDetector(profile)
    result = FakeCrawlResult(
        url="https://api.example.com",
        summary="Built with Flask framework.",
    )
    conflicts = detector.detect([result])

    tech_conflicts = [c for c in conflicts if c.conflict_type == "forbidden_technology"]
    assert len(tech_conflicts) == 1


def test_forbidden_technology_reason_suffix_stripped() -> None:
    """'flask:critical_reason' in forbidden list still matches 'flask' in summary."""
    profile = _make_profile(forbidden_technologies=["flask:critical_reason"])
    detector = ConflictDetector(profile)
    result = FakeCrawlResult(
        url="https://api.example.com",
        summary="The API uses flask for routing.",
    )
    conflicts = detector.detect([result])

    tech_conflicts = [c for c in conflicts if c.conflict_type == "forbidden_technology"]
    assert len(tech_conflicts) == 1


def test_forbidden_technology_word_boundary_no_false_positive() -> None:
    """'flask' in forbidden list should NOT match 'flaskful' (word-boundary check)."""
    profile = _make_profile(forbidden_technologies=["flask:not_approved"])
    detector = ConflictDetector(profile)
    result = FakeCrawlResult(
        url="https://api.example.com",
        summary="The system uses flaskful patterns throughout.",
    )
    conflicts = detector.detect([result])

    tech_conflicts = [c for c in conflicts if c.conflict_type == "forbidden_technology"]
    assert len(tech_conflicts) == 0


# ============================================================
# TESTS — forbidden patterns
# ============================================================


def test_forbidden_pattern_in_summary_raises_low_conflict() -> None:
    """Summary containing a forbidden pattern string → LOW forbidden_pattern conflict."""
    profile = _make_profile(forbidden_patterns=["bare except clauses"])
    detector = ConflictDetector(profile)
    result = FakeCrawlResult(
        url="https://api.example.com",
        summary="The code uses bare except clauses extensively.",
    )
    conflicts = detector.detect([result])

    pattern_conflicts = [c for c in conflicts if c.conflict_type == "forbidden_pattern"]
    assert len(pattern_conflicts) == 1
    c = pattern_conflicts[0]
    assert c.severity == ConflictSeverity.LOW
    assert "bare except clauses" in c.description


# ============================================================
# TESTS — error skipping
# ============================================================


def test_detect_skips_crawl_results_with_errors() -> None:
    """CrawlResults with a non-None error field are skipped without raising."""
    profile = _make_profile(forbidden_technologies=["flask:bad"])
    detector = ConflictDetector(profile)
    result = FakeCrawlResult(
        url="http://broken.example.com",
        summary="flask is used here",
        error="ConnectionTimeout",
    )
    conflicts = detector.detect([result])
    assert conflicts == []


# ============================================================
# TESTS — ConflictRecord field validation
# ============================================================


def test_conflict_record_has_uuid_id() -> None:
    """Every ConflictRecord.conflict_id must be a valid UUID4 string."""
    profile = _make_profile()
    detector = ConflictDetector(profile)
    result = FakeCrawlResult(url="http://api.example.com", summary="")
    conflicts = detector.detect([result])

    assert len(conflicts) >= 1
    for c in conflicts:
        assert _UUID4_RE.match(c.conflict_id), (
            f"conflict_id '{c.conflict_id}' is not a valid UUID4"
        )


def test_conflict_record_detected_at_is_utc() -> None:
    """ConflictRecord.detected_at must be timezone-aware and in UTC."""
    profile = _make_profile()
    detector = ConflictDetector(profile)
    result = FakeCrawlResult(url="http://api.example.com", summary="")
    conflicts = detector.detect([result])

    assert len(conflicts) >= 1
    for c in conflicts:
        assert c.detected_at.tzinfo is not None, "detected_at must be timezone-aware"
        # UTC offset must be zero.
        assert c.detected_at.utcoffset().total_seconds() == 0, (  # type: ignore[union-attr]
            "detected_at must be UTC"
        )


# ============================================================
# TESTS — multi-conflict and empty input
# ============================================================


def test_multiple_conflicts_from_single_url() -> None:
    """A single URL with both an HTTP scheme and a forbidden tech → 2+ conflicts."""
    profile = _make_profile(forbidden_technologies=["flask:not_approved"])
    detector = ConflictDetector(profile)
    result = FakeCrawlResult(
        url="http://api.example.com",
        summary="Built entirely with flask.",
    )
    conflicts = detector.detect([result])

    types = {c.conflict_type for c in conflicts}
    assert "insecure_transport" in types
    assert "forbidden_technology" in types
    assert len(conflicts) >= 2


def test_empty_crawl_results_returns_empty_list() -> None:
    """detect([]) with no results returns an empty list without error."""
    profile = _make_profile()
    detector = ConflictDetector(profile)
    assert detector.detect([]) == []
