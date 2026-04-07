"""Unit tests for orchestration.project_registry.

All database calls are mocked — no live PostgreSQL connection required.
Tests cover: register_repo, get_repo_url, list_active_repos, get_project.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from db.models import Project
from orchestration.project_registry import ProjectRegistry, registry


# ============================================================
# FIXTURES
# ============================================================


@pytest.fixture()
def reg() -> ProjectRegistry:
    """Return a fresh ProjectRegistry instance for each test."""
    return ProjectRegistry()


@pytest.fixture()
def mock_session() -> AsyncMock:
    """Return an async mock SQLAlchemy session."""
    return AsyncMock()


def _make_project(
    project_id: str = "test-project",
    github_repo: str | None = None,
    status: str = "intake",
) -> Project:
    """Build a Project instance without a database connection."""
    project = Project(
        project_id=project_id,
        name="Test Project",
        client_name="Test Client",
        status=status,
    )
    project.github_repo = github_repo
    return project


# ============================================================
# REGISTER REPO
# ============================================================


class TestRegisterRepo:
    """Tests for ProjectRegistry.register_repo."""

    async def test_updates_github_repo_url(
        self,
        reg: ProjectRegistry,
        mock_session: AsyncMock,
    ) -> None:
        """register_repo sets github_repo on an existing project and commits."""
        project = _make_project(project_id="my-project")

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = project
        mock_session.execute.return_value = mock_result
        mock_session.refresh = AsyncMock(return_value=None)

        updated = await reg.register_repo("my-project", "https://github.com/org/my-project", mock_session)

        assert updated.github_repo == "https://github.com/org/my-project"
        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(project)

    async def test_raises_if_project_not_found(
        self,
        reg: ProjectRegistry,
        mock_session: AsyncMock,
    ) -> None:
        """register_repo raises ValueError when the project does not exist."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not found in registry"):
            await reg.register_repo("missing-project", "https://github.com/org/missing", mock_session)

        mock_session.commit.assert_not_awaited()


# ============================================================
# GET REPO URL
# ============================================================


class TestGetRepoUrl:
    """Tests for ProjectRegistry.get_repo_url."""

    async def test_returns_github_url_when_set(
        self,
        reg: ProjectRegistry,
        mock_session: AsyncMock,
    ) -> None:
        """get_repo_url returns the stored URL for a scaffolded project."""
        mock_result = MagicMock()
        mock_result.first.return_value = ("https://github.com/org/my-project",)
        mock_session.execute.return_value = mock_result

        url = await reg.get_repo_url("my-project", mock_session)

        assert url == "https://github.com/org/my-project"

    async def test_returns_none_when_repo_not_yet_set(
        self,
        reg: ProjectRegistry,
        mock_session: AsyncMock,
    ) -> None:
        """get_repo_url returns None for a project not yet scaffolded."""
        mock_result = MagicMock()
        mock_result.first.return_value = (None,)
        mock_session.execute.return_value = mock_result

        url = await reg.get_repo_url("unscaffolded-project", mock_session)

        assert url is None

    async def test_raises_when_project_not_found(
        self,
        reg: ProjectRegistry,
        mock_session: AsyncMock,
    ) -> None:
        """get_repo_url raises ValueError when no row exists."""
        mock_result = MagicMock()
        mock_result.first.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not found in registry"):
            await reg.get_repo_url("ghost-project", mock_session)


# ============================================================
# LIST ACTIVE REPOS
# ============================================================


class TestListActiveRepos:
    """Tests for ProjectRegistry.list_active_repos."""

    async def test_returns_projects_with_repos(
        self,
        reg: ProjectRegistry,
        mock_session: AsyncMock,
    ) -> None:
        """list_active_repos returns projects that have a github_repo and are not archived."""
        projects = [
            _make_project("project-a", "https://github.com/org/project-a", "execution"),
            _make_project("project-b", "https://github.com/org/project-b", "planning"),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = projects
        mock_session.execute.return_value = mock_result

        result = await reg.list_active_repos(mock_session)

        assert len(result) == 2
        assert all(p.github_repo is not None for p in result)

    async def test_returns_empty_list_when_none_active(
        self,
        reg: ProjectRegistry,
        mock_session: AsyncMock,
    ) -> None:
        """list_active_repos returns [] when no active repos exist."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await reg.list_active_repos(mock_session)

        assert result == []


# ============================================================
# GET PROJECT
# ============================================================


class TestGetProject:
    """Tests for ProjectRegistry.get_project."""

    async def test_returns_project_when_found(
        self,
        reg: ProjectRegistry,
        mock_session: AsyncMock,
    ) -> None:
        """get_project returns the Project ORM instance when found."""
        project = _make_project("found-project")
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = project
        mock_session.execute.return_value = mock_result

        result = await reg.get_project("found-project", mock_session)

        assert result is project

    async def test_returns_none_when_not_found(
        self,
        reg: ProjectRegistry,
        mock_session: AsyncMock,
    ) -> None:
        """get_project returns None when the project does not exist."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result

        result = await reg.get_project("ghost-project", mock_session)

        assert result is None


# ============================================================
# MODULE-LEVEL SINGLETON
# ============================================================


class TestRegistrySingleton:
    """Tests for the module-level registry singleton."""

    def test_singleton_is_project_registry_instance(self) -> None:
        """The module-level registry is a ProjectRegistry instance."""
        assert isinstance(registry, ProjectRegistry)
