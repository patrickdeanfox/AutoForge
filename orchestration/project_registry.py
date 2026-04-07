"""Project Registry — database-backed lookup of all managed project repositories.

Agents look up a project's GitHub repo URL here before cloning and working.
All write operations go through the FastAPI layer; the registry is read-only
from Celery workers.
"""

from __future__ import annotations

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Project

logger = structlog.get_logger()


# ============================================================
# PROJECT REGISTRY
# ============================================================


class ProjectRegistry:
    """Async interface to the AutoForge project registry table.

    All methods require a live ``AsyncSession`` which callers are responsible
    for providing and closing. This keeps the registry stateless and compatible
    with both FastAPI dependency injection and Celery task contexts.
    """

    async def register_repo(
        self,
        project_id: str,
        github_repo: str,
        session: AsyncSession,
    ) -> Project:
        """Record the GitHub repo URL for an existing project.

        Called after ``GitHubManager.scaffold_project_repo`` succeeds.
        Updates the ``github_repo`` column on the project row.

        Args:
            project_id: The kebab-case project slug.
            github_repo: Full GitHub repo URL (e.g. ``https://github.com/org/slug``).
            session: An open async SQLAlchemy session.

        Returns:
            The updated Project ORM instance.

        Raises:
            ValueError: If the project does not exist in the registry.
        """
        result = await session.execute(
            select(Project).where(Project.project_id == project_id)
        )
        project = result.scalars().first()
        if project is None:
            raise ValueError(
                f"Project '{project_id}' not found in registry. "
                "Create it via POST /api/projects before registering a repo."
            )

        project.github_repo = github_repo
        await session.commit()
        await session.refresh(project)

        logger.info(
            "repo_registered",
            project_id=project_id,
            github_repo=github_repo,
        )
        return project

    async def get_repo_url(
        self,
        project_id: str,
        session: AsyncSession,
    ) -> str | None:
        """Return the GitHub repo URL for a project, or None if not yet scaffolded.

        Args:
            project_id: The kebab-case project slug.
            session: An open async SQLAlchemy session.

        Returns:
            The GitHub repo URL string, or None if the project has no repo yet.

        Raises:
            ValueError: If the project does not exist in the registry.
        """
        result = await session.execute(
            select(Project.github_repo).where(Project.project_id == project_id)
        )
        row = result.first()
        if row is None:
            raise ValueError(
                f"Project '{project_id}' not found in registry."
            )
        url: str | None = row[0]
        return url

    async def list_active_repos(
        self,
        session: AsyncSession,
    ) -> list[Project]:
        """Return all projects that have a GitHub repo and are not archived.

        Used by the scheduler to enumerate repos for overnight run eligibility.

        Args:
            session: An open async SQLAlchemy session.

        Returns:
            List of Project ORM instances with github_repo set, ordered by project_id.
        """
        result = await session.execute(
            select(Project)
            .where(
                Project.github_repo.isnot(None),
                Project.status != "archived",
            )
            .order_by(Project.project_id)
        )
        projects = list(result.scalars().all())
        logger.info("active_repos_listed", count=len(projects))
        return projects

    async def get_project(
        self,
        project_id: str,
        session: AsyncSession,
    ) -> Project | None:
        """Return a Project by project_id, or None if not found.

        Args:
            project_id: The kebab-case project slug.
            session: An open async SQLAlchemy session.

        Returns:
            Project ORM instance or None.
        """
        result = await session.execute(
            select(Project).where(Project.project_id == project_id)
        )
        return result.scalars().first()


# ============================================================
# MODULE-LEVEL SINGLETON
# ============================================================

registry = ProjectRegistry()
