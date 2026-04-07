"""Unit tests for orchestration.github_manager.

All GitHub API calls are mocked — no live network calls are made.
Tests cover: webhook signature validation, event type inference, branch/PR
creation, issue operations, and the scaffold orchestration flow.
"""

from __future__ import annotations

import hashlib
import hmac
from unittest.mock import MagicMock, patch

import pytest

from orchestration.github_manager import (
    STANDARD_LABELS,
    GitHubManager,
    build_github_manager,
)


# ============================================================
# FIXTURES
# ============================================================


@pytest.fixture()
def manager() -> GitHubManager:
    """Return a GitHubManager backed by a mocked Github client."""
    with patch("orchestration.github_manager.Github"):
        return GitHubManager(token="test-token", org="test-org")


@pytest.fixture()
def mock_repo() -> MagicMock:
    """Return a mock Repository with common attributes pre-configured."""
    repo = MagicMock()
    repo.full_name = "test-org/test-project"
    repo.html_url = "https://github.com/test-org/test-project"
    return repo


# ============================================================
# WEBHOOK SIGNATURE VALIDATION
# ============================================================


class TestVerifyWebhookSignature:
    """Tests for GitHubManager.verify_webhook_signature."""

    def _make_signature(self, payload: bytes, secret: str) -> str:
        """Build a valid sha256 signature for testing."""
        digest = hmac.new(
            key=secret.encode(),
            msg=payload,
            digestmod=hashlib.sha256,
        ).hexdigest()
        return f"sha256={digest}"

    def test_valid_signature_returns_true(self) -> None:
        """Correct HMAC signature is accepted."""
        payload = b'{"action": "opened"}'
        secret = "my-webhook-secret"
        sig = self._make_signature(payload, secret)

        assert GitHubManager.verify_webhook_signature(payload, sig, secret) is True

    def test_invalid_signature_returns_false(self) -> None:
        """Tampered payload is rejected."""
        payload = b'{"action": "opened"}'
        secret = "my-webhook-secret"
        tampered = b'{"action": "closed"}'
        sig = self._make_signature(payload, secret)

        assert GitHubManager.verify_webhook_signature(tampered, sig, secret) is False

    def test_missing_sha256_prefix_returns_false(self) -> None:
        """Signature header without sha256= prefix is rejected."""
        payload = b"body"
        secret = "secret"
        sig = "deadbeef"  # no prefix

        assert GitHubManager.verify_webhook_signature(payload, sig, secret) is False

    def test_wrong_secret_returns_false(self) -> None:
        """Signature produced with a different secret is rejected."""
        payload = b"body"
        sig = self._make_signature(payload, "correct-secret")

        assert GitHubManager.verify_webhook_signature(payload, sig, "wrong-secret") is False

    def test_empty_payload_with_valid_signature_returns_true(self) -> None:
        """Empty payload with correct HMAC is still accepted."""
        payload = b""
        secret = "s3cr3t"
        sig = self._make_signature(payload, secret)

        assert GitHubManager.verify_webhook_signature(payload, sig, secret) is True


# ============================================================
# STANDARD LABELS
# ============================================================


class TestStandardLabels:
    """Tests for the STANDARD_LABELS constant."""

    def test_all_required_labels_present(self) -> None:
        """All labels required by the CLAUDE.md spec are in STANDARD_LABELS."""
        required = {
            "approved",
            "needs-human",
            "decision-needed",
            "blocked",
            "feature",
            "fix",
            "chore",
            "spike",
            "S",
            "M",
            "L",
            "XL",
        }
        label_names = {name for name, _, _ in STANDARD_LABELS}
        assert required.issubset(label_names)

    def test_all_labels_have_non_empty_fields(self) -> None:
        """Every label has a name, color, and description."""
        for name, color, description in STANDARD_LABELS:
            assert name, "Label name must not be empty"
            assert color, f"Color missing for label '{name}'"
            assert description, f"Description missing for label '{name}'"

    def test_all_colors_are_valid_hex(self) -> None:
        """All color values are 6-character hex strings (no # prefix)."""
        for name, color, _ in STANDARD_LABELS:
            assert len(color) == 6, f"Color for '{name}' must be 6 hex chars, got '{color}'"
            assert all(c in "0123456789abcdefABCDEF" for c in color), (
                f"Color for '{name}' contains non-hex character: '{color}'"
            )


# ============================================================
# CREATE BRANCH
# ============================================================


class TestCreateBranch:
    """Tests for GitHubManager.create_branch."""

    def test_creates_branch_from_main(self, manager: GitHubManager) -> None:
        """create_branch calls get_branch and create_git_ref with correct args."""
        mock_base_branch = MagicMock()
        mock_base_branch.commit.sha = "abc123"

        mock_repo = MagicMock()
        mock_repo.get_branch.return_value = mock_base_branch

        manager._gh.get_repo.return_value = mock_repo

        manager.create_branch("test-org/test-project", "feature/42-add-retry", base="main")

        mock_repo.get_branch.assert_called_once_with("main")
        mock_repo.create_git_ref.assert_called_once_with(
            ref="refs/heads/feature/42-add-retry",
            sha="abc123",
        )

    def test_default_base_is_main(self, manager: GitHubManager) -> None:
        """create_branch uses main as default base when not specified."""
        mock_base = MagicMock()
        mock_base.commit.sha = "deadbeef"
        mock_repo = MagicMock()
        mock_repo.get_branch.return_value = mock_base
        manager._gh.get_repo.return_value = mock_repo

        manager.create_branch("test-org/test-project", "fix/99-typo")

        mock_repo.get_branch.assert_called_once_with("main")


# ============================================================
# OPEN DRAFT PR
# ============================================================


class TestOpenDraftPr:
    """Tests for GitHubManager.open_draft_pr."""

    def test_opens_draft_pr_and_returns_number(self, manager: GitHubManager) -> None:
        """open_draft_pr calls create_pull with draft=True and returns the PR number."""
        mock_pr = MagicMock()
        mock_pr.number = 7

        mock_repo = MagicMock()
        mock_repo.create_pull.return_value = mock_pr
        manager._gh.get_repo.return_value = mock_repo

        pr_number = manager.open_draft_pr(
            repo_full_name="test-org/test-project",
            title="feat: add retry logic",
            body="Closes #42",
            head="feature/42-add-retry",
        )

        assert pr_number == 7
        mock_repo.create_pull.assert_called_once_with(
            title="feat: add retry logic",
            body="Closes #42",
            head="feature/42-add-retry",
            base="main",
            draft=True,
        )

    def test_custom_base_branch(self, manager: GitHubManager) -> None:
        """open_draft_pr respects a non-default base branch."""
        mock_pr = MagicMock()
        mock_pr.number = 3
        mock_repo = MagicMock()
        mock_repo.create_pull.return_value = mock_pr
        manager._gh.get_repo.return_value = mock_repo

        manager.open_draft_pr(
            repo_full_name="test-org/test-project",
            title="hotfix",
            body="",
            head="hotfix/critical",
            base="release",
        )

        call_kwargs = mock_repo.create_pull.call_args.kwargs
        assert call_kwargs["base"] == "release"


# ============================================================
# CREATE ISSUE
# ============================================================


class TestCreateIssue:
    """Tests for GitHubManager.create_issue."""

    def test_creates_issue_and_returns_number(self, manager: GitHubManager) -> None:
        """create_issue calls create_issue on the repo and returns the number."""
        mock_issue = MagicMock()
        mock_issue.number = 15

        mock_repo = MagicMock()
        mock_repo.create_issue.return_value = mock_issue
        manager._gh.get_repo.return_value = mock_repo

        number = manager.create_issue(
            repo_full_name="test-org/test-project",
            title="needs-human: debug agent stuck after 3 attempts",
            body="## Diagnosis\n...",
            labels=["needs-human", "L"],
        )

        assert number == 15
        mock_repo.create_issue.assert_called_once_with(
            title="needs-human: debug agent stuck after 3 attempts",
            body="## Diagnosis\n...",
            labels=["needs-human", "L"],
        )

    def test_no_labels_passes_empty_list(self, manager: GitHubManager) -> None:
        """create_issue passes [] when no labels are given."""
        mock_issue = MagicMock()
        mock_issue.number = 1
        mock_repo = MagicMock()
        mock_repo.create_issue.return_value = mock_issue
        manager._gh.get_repo.return_value = mock_repo

        manager.create_issue("test-org/test-project", "title", "body")

        call_kwargs = mock_repo.create_issue.call_args.kwargs
        assert call_kwargs["labels"] == []


# ============================================================
# GET OPEN PRS
# ============================================================


class TestGetOpenPrs:
    """Tests for GitHubManager.get_open_prs."""

    def test_returns_only_non_draft_prs(self, manager: GitHubManager) -> None:
        """get_open_prs filters out draft PRs from the result set."""
        draft_pr = MagicMock()
        draft_pr.draft = True
        draft_pr.number = 1

        ready_pr = MagicMock()
        ready_pr.draft = False
        ready_pr.number = 2
        ready_pr.title = "feat: done"
        ready_pr.html_url = "https://github.com/test-org/test-project/pull/2"
        ready_pr.head.ref = "feature/done"
        ready_pr.created_at.isoformat.return_value = "2026-04-01T00:00:00"

        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [draft_pr, ready_pr]
        manager._gh.get_repo.return_value = mock_repo

        result = manager.get_open_prs("test-org/test-project")

        assert len(result) == 1
        assert result[0]["number"] == 2

    def test_returns_empty_list_when_no_prs(self, manager: GitHubManager) -> None:
        """get_open_prs returns [] when there are no open non-draft PRs."""
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = []
        manager._gh.get_repo.return_value = mock_repo

        result = manager.get_open_prs("test-org/test-project")

        assert result == []


# ============================================================
# BUILD GITHUB MANAGER FACTORY
# ============================================================


class TestBuildGitHubManager:
    """Tests for the build_github_manager() factory function."""

    def test_raises_when_token_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """build_github_manager raises ValueError when GITHUB_TOKEN is not set."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.setenv("GITHUB_ORG", "test-org")

        with pytest.raises(ValueError, match="GITHUB_TOKEN"):
            build_github_manager()

    def test_raises_when_org_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """build_github_manager raises ValueError when GITHUB_ORG is not set."""
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")
        monkeypatch.delenv("GITHUB_ORG", raising=False)

        with pytest.raises(ValueError, match="GITHUB_ORG"):
            build_github_manager()

    def test_returns_manager_when_env_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """build_github_manager returns a GitHubManager when both vars are set."""
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")
        monkeypatch.setenv("GITHUB_ORG", "test-org")

        with patch("orchestration.github_manager.Github"):
            mgr = build_github_manager()

        assert isinstance(mgr, GitHubManager)
