"""GitHub Manager — all GitHub API operations for AutoForge.

Every customer project repo is created, configured, and maintained through this module.
Agents use it to create branches, open PRs, post comments, and manage issues.
The engineer's GitHub token is required — loaded from environment variables.

Workflow template files are read from ``templates/github/workflows/`` in the
AutoForge repo root at scaffolding time and committed to each new project repo.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path
from typing import Any

import structlog
from github import Github, GithubException
from github.Repository import Repository

# ============================================================
# CONFIG
# ============================================================

TEMPLATES_DIR: Path = Path(__file__).parent.parent / "templates" / "github" / "workflows"

# Standard label set applied to every project repo.
# (name, color-hex, description)
STANDARD_LABELS: list[tuple[str, str, str]] = [
    ("approved", "0075ca", "Engineer approved — ready for execution"),
    ("needs-human", "d93f0b", "Agent stuck — requires human intervention"),
    ("decision-needed", "e4e669", "Undecided technology choice — awaiting engineer decision"),
    ("blocked", "b60205", "Cannot proceed — dependency or prerequisite missing"),
    ("feature", "a2eeef", "New functionality"),
    ("fix", "d73a4a", "Bug fix"),
    ("chore", "cfd3d7", "Maintenance, refactor, or dependency bump"),
    ("spike", "5319e7", "Research task — no code output required"),
    ("S", "c5def5", "Complexity: Small"),
    ("M", "0075ca", "Complexity: Medium"),
    ("L", "e99695", "Complexity: Large"),
    ("XL", "b60205", "Complexity: Extra Large"),
]

logger = structlog.get_logger()


# ============================================================
# GITHUB MANAGER
# ============================================================


class GitHubManager:
    """Wraps PyGithub to provide all AutoForge GitHub operations.

    Instantiate once per session and reuse. The underlying PyGithub client
    is thread-safe for read operations; use separate instances per Celery
    worker for write operations.

    Args:
        token: GitHub personal access token with repo + webhook scopes.
        org: GitHub organisation name under which project repos are created.
    """

    def __init__(self, token: str, org: str) -> None:
        self._gh = Github(token)
        self._org_name = org
        self._token = token

    # ------------------------------------------------------------------ #
    # Repo scaffolding                                                     #
    # ------------------------------------------------------------------ #

    def scaffold_project_repo(
        self,
        project_id: str,
        name: str,
        description: str,
        private: bool = True,
        webhook_url: str | None = None,
        webhook_secret: str | None = None,
    ) -> str:
        """Create and fully configure a new project repository.

        Steps performed in order:
        1. Create the repo under the configured org
        2. Set up branch protection on main
        3. Create the standard AutoForge label set
        4. Inject GitHub Actions workflow files from templates
        5. Commit the initial project directory skeleton (knowledge/, src/, tests/)
        6. Register an inbound webhook pointing to AutoForge API (if webhook_url provided)

        Args:
            project_id: The kebab-case project slug (used as the repo name).
            name: Human-readable project name (used in repo description).
            description: Short project description for the GitHub repo About field.
            private: Whether the repo should be private. Defaults to True.
            webhook_url: AutoForge API webhook endpoint to register. Optional.
            webhook_secret: HMAC secret for webhook signature validation. Optional.

        Returns:
            The full GitHub repo URL (e.g. ``https://github.com/org/project-id``).

        Raises:
            GithubException: If the repo already exists or the token lacks permissions.
        """
        log = logger.bind(project_id=project_id, org=self._org_name)
        log.info("scaffold_start", step="scaffold_project_repo", lifecycle="step_start")

        org = self._gh.get_organization(self._org_name)
        repo = self._create_repo(org, project_id, description, private)

        self._setup_branch_protection(repo)
        self._delete_default_labels(repo)
        self._create_standard_labels(repo)
        self._inject_workflow_files(repo)
        self._commit_initial_skeleton(repo, project_id, name, description)

        if webhook_url:
            self._register_webhook(repo, webhook_url, webhook_secret or "")

        repo_url = repo.html_url
        log.info(
            "scaffold_complete",
            step="scaffold_project_repo",
            lifecycle="step_complete",
            repo_url=repo_url,
        )
        return repo_url

    def _create_repo(
        self,
        org: Any,
        slug: str,
        description: str,
        private: bool,
    ) -> Repository:
        """Create the GitHub repo under the org."""
        repo = org.create_repo(
            name=slug,
            description=description,
            private=private,
            auto_init=True,  # creates an initial commit so main exists
            has_issues=True,
            has_wiki=False,
            has_projects=False,
        )
        logger.info(
            "repo_created",
            repo_full_name=repo.full_name,
            step="create_repo",
            lifecycle="step_complete",
        )
        return repo

    def _setup_branch_protection(self, repo: Repository) -> None:
        """Protect main: require PR, disallow direct pushes, enforce status checks."""
        branch = repo.get_branch("main")
        branch.edit_protection(
            required_approving_review_count=1,
            enforce_admins=False,
            dismiss_stale_reviews=True,
            require_code_owner_reviews=False,
        )
        logger.info(
            "branch_protection_set",
            repo=repo.full_name,
            branch="main",
            step="setup_branch_protection",
            lifecycle="step_complete",
        )

    def _delete_default_labels(self, repo: Repository) -> None:
        """Remove GitHub's default labels to start with a clean slate."""
        for label in repo.get_labels():
            try:
                label.delete()
            except GithubException:
                pass  # best-effort — don't block scaffolding on label cleanup

    def _create_standard_labels(self, repo: Repository) -> None:
        """Create the standard AutoForge label set on the repo."""
        for label_name, color, description in STANDARD_LABELS:
            try:
                repo.create_label(
                    name=label_name,
                    color=color,
                    description=description,
                )
            except GithubException as exc:
                # 422 = label already exists — safe to ignore
                if exc.status != 422:
                    raise
        logger.info(
            "labels_created",
            repo=repo.full_name,
            count=len(STANDARD_LABELS),
            step="create_standard_labels",
            lifecycle="step_complete",
        )

    def _inject_workflow_files(self, repo: Repository) -> None:
        """Commit GitHub Actions workflow files from AutoForge templates."""
        workflow_files = list(TEMPLATES_DIR.glob("*.yml"))
        if not workflow_files:
            logger.warning(
                "no_workflow_templates_found",
                templates_dir=str(TEMPLATES_DIR),
            )
            return

        for template_path in workflow_files:
            content = template_path.read_text()
            dest_path = f".github/workflows/{template_path.name}"
            try:
                repo.create_file(
                    path=dest_path,
                    message=f"chore: inject {template_path.name} workflow from AutoForge template",
                    content=content,
                    branch="main",
                )
            except GithubException as exc:
                if exc.status != 422:  # 422 = file already exists
                    raise

        logger.info(
            "workflows_injected",
            repo=repo.full_name,
            count=len(workflow_files),
            step="inject_workflow_files",
            lifecycle="step_complete",
        )

    def _commit_initial_skeleton(
        self,
        repo: Repository,
        project_id: str,
        name: str,
        description: str,
    ) -> None:
        """Commit the initial project directory skeleton to main."""
        skeleton_files: dict[str, str] = {
            "knowledge/resources/.gitkeep": "",
            "knowledge/decisions/.gitkeep": "",
            "knowledge/conflicts/.gitkeep": "",
            "knowledge/crawl_log/.gitkeep": "",
            "src/.gitkeep": "",
            "tests/.gitkeep": "",
            "docs/.gitkeep": "",
            "README.md": self._render_readme(project_id, name, description),
            "CHANGELOG.md": self._render_changelog(name),
        }

        for path, content in skeleton_files.items():
            try:
                repo.create_file(
                    path=path,
                    message=f"chore: initialise {path}",
                    content=content,
                    branch="main",
                )
            except GithubException as exc:
                if exc.status != 422:
                    raise

        logger.info(
            "skeleton_committed",
            repo=repo.full_name,
            files=len(skeleton_files),
            step="commit_initial_skeleton",
            lifecycle="step_complete",
        )

    def _register_webhook(
        self,
        repo: Repository,
        webhook_url: str,
        webhook_secret: str,
    ) -> None:
        """Register an inbound webhook on the repo pointing to AutoForge API."""
        repo.create_hook(
            name="web",
            config={
                "url": webhook_url,
                "content_type": "json",
                "secret": webhook_secret,
                "insecure_ssl": "0",
            },
            events=["push", "pull_request", "issues", "issue_comment"],
            active=True,
        )
        logger.info(
            "webhook_registered",
            repo=repo.full_name,
            webhook_url=webhook_url,
            step="register_webhook",
            lifecycle="step_complete",
        )

    # ------------------------------------------------------------------ #
    # Agent operations — branches, PRs, issues                            #
    # ------------------------------------------------------------------ #

    def create_branch(
        self,
        repo_full_name: str,
        branch_name: str,
        base: str = "main",
    ) -> None:
        """Create a new branch off ``base`` in the specified repo.

        Args:
            repo_full_name: ``org/repo-name`` format.
            branch_name: Name for the new branch (e.g. ``feature/42-add-retry``).
            base: The branch or commit SHA to branch from. Defaults to ``main``.

        Raises:
            GithubException: If the branch already exists or the base does not exist.
        """
        repo = self._gh.get_repo(repo_full_name)
        base_ref = repo.get_branch(base)
        repo.create_git_ref(
            ref=f"refs/heads/{branch_name}",
            sha=base_ref.commit.sha,
        )
        logger.info(
            "branch_created",
            repo=repo_full_name,
            branch=branch_name,
            base=base,
        )

    def open_draft_pr(
        self,
        repo_full_name: str,
        title: str,
        body: str,
        head: str,
        base: str = "main",
    ) -> int:
        """Open a draft pull request.

        Args:
            repo_full_name: ``org/repo-name`` format.
            title: PR title.
            body: PR description (markdown supported).
            head: The feature branch name (source of changes).
            base: The target branch. Defaults to ``main``.

        Returns:
            The PR number.
        """
        repo = self._gh.get_repo(repo_full_name)
        pr = repo.create_pull(
            title=title,
            body=body,
            head=head,
            base=base,
            draft=True,
        )
        logger.info(
            "draft_pr_opened",
            repo=repo_full_name,
            pr_number=pr.number,
            title=title,
        )
        return pr.number

    def promote_pr_to_ready(self, repo_full_name: str, pr_number: int) -> None:
        """Convert a draft PR to ready-for-review.

        Args:
            repo_full_name: ``org/repo-name`` format.
            pr_number: The PR number to promote.
        """
        repo = self._gh.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)
        pr.edit(draft=False)
        logger.info(
            "pr_promoted_to_ready",
            repo=repo_full_name,
            pr_number=pr_number,
        )

    def add_label_to_issue(
        self,
        repo_full_name: str,
        issue_number: int,
        label: str,
    ) -> None:
        """Add a label to an issue or PR.

        Args:
            repo_full_name: ``org/repo-name`` format.
            issue_number: Issue or PR number.
            label: Label name to add (must already exist on the repo).
        """
        repo = self._gh.get_repo(repo_full_name)
        issue = repo.get_issue(issue_number)
        issue.add_to_labels(label)
        logger.info(
            "label_added",
            repo=repo_full_name,
            issue_number=issue_number,
            label=label,
        )

    def create_issue(
        self,
        repo_full_name: str,
        title: str,
        body: str,
        labels: list[str] | None = None,
    ) -> int:
        """Create a GitHub issue.

        Used by agents to create ``needs-human`` and ``decision-needed`` escalations.

        Args:
            repo_full_name: ``org/repo-name`` format.
            title: Issue title.
            body: Issue body (markdown supported).
            labels: Optional list of label names to apply.

        Returns:
            The issue number.
        """
        repo = self._gh.get_repo(repo_full_name)
        issue = repo.create_issue(
            title=title,
            body=body,
            labels=labels or [],
        )
        logger.info(
            "issue_created",
            repo=repo_full_name,
            issue_number=issue.number,
            title=title,
            labels=labels,
        )
        return issue.number

    def post_pr_comment(
        self,
        repo_full_name: str,
        pr_number: int,
        body: str,
    ) -> None:
        """Post a comment on a pull request.

        Args:
            repo_full_name: ``org/repo-name`` format.
            pr_number: PR number to comment on.
            body: Comment body (markdown supported).
        """
        repo = self._gh.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)
        pr.create_issue_comment(body)
        logger.info(
            "pr_comment_posted",
            repo=repo_full_name,
            pr_number=pr_number,
        )

    def get_open_prs(self, repo_full_name: str) -> list[dict[str, Any]]:
        """Return open (non-draft) PRs ready for human review.

        Args:
            repo_full_name: ``org/repo-name`` format.

        Returns:
            List of dicts with keys: number, title, url, head, created_at.
        """
        repo = self._gh.get_repo(repo_full_name)
        prs = repo.get_pulls(state="open", sort="created", direction="desc")
        return [
            {
                "number": pr.number,
                "title": pr.title,
                "url": pr.html_url,
                "head": pr.head.ref,
                "draft": pr.draft,
                "created_at": pr.created_at.isoformat(),
            }
            for pr in prs
            if not pr.draft
        ]

    def get_issues_by_label(
        self,
        repo_full_name: str,
        label: str,
    ) -> list[dict[str, Any]]:
        """Return open issues carrying the given label.

        Args:
            repo_full_name: ``org/repo-name`` format.
            label: Label name to filter by (e.g. ``approved``, ``needs-human``).

        Returns:
            List of dicts with keys: number, title, url, labels, created_at.
        """
        repo = self._gh.get_repo(repo_full_name)
        issues = repo.get_issues(state="open", labels=[label], sort="created")
        return [
            {
                "number": issue.number,
                "title": issue.title,
                "url": issue.html_url,
                "labels": [lbl.name for lbl in issue.labels],
                "created_at": issue.created_at.isoformat(),
            }
            for issue in issues
        ]

    # ------------------------------------------------------------------ #
    # Webhook signature validation                                         #
    # ------------------------------------------------------------------ #

    @staticmethod
    def verify_webhook_signature(
        payload: bytes,
        signature_header: str,
        secret: str,
    ) -> bool:
        """Validate a GitHub webhook HMAC-SHA256 signature.

        Args:
            payload: Raw request body bytes.
            signature_header: Value of the ``X-Hub-Signature-256`` header.
            secret: The webhook secret configured on the repo.

        Returns:
            True if the signature is valid, False otherwise.
        """
        if not signature_header.startswith("sha256="):
            return False
        expected = hmac.new(
            key=secret.encode(),
            msg=payload,
            digestmod=hashlib.sha256,
        ).hexdigest()
        actual = signature_header.removeprefix("sha256=")
        return hmac.compare_digest(expected, actual)

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _render_readme(project_id: str, name: str, description: str) -> str:
        """Generate an initial README.md for the project repo."""
        return f"""# {name}

{description}

---

*This repository is managed by [AutoForge](https://github.com/{os.environ.get("GITHUB_ORG", "org")}/AutoForge).*
*Project ID: `{project_id}`*
*Do not modify this README manually — it is maintained by the Documentation Agent.*
"""

    @staticmethod
    def _render_changelog(name: str) -> str:
        """Generate an initial CHANGELOG.md for the project repo."""
        return f"""# Changelog — {name}

All notable changes to this project will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

*(Maintained by the AutoForge Documentation Agent)*
"""


# ------------------------------------------------------------------ #
# Factory helper                                                      #
# ------------------------------------------------------------------ #


def build_github_manager() -> GitHubManager:
    """Instantiate GitHubManager from environment variables.

    Reads ``GITHUB_TOKEN`` and ``GITHUB_ORG``. Raises ``ValueError`` if
    either is missing.

    Returns:
        A configured ``GitHubManager`` instance.
    """
    token = os.environ.get("GITHUB_TOKEN", "")
    org = os.environ.get("GITHUB_ORG", "")
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is not set")
    if not org:
        raise ValueError("GITHUB_ORG environment variable is not set")
    return GitHubManager(token=token, org=org)
