"""FastAPI CRUD router for AutoForge project management.

Provides async endpoints for creating, reading, updating, and deleting
projects in the AutoForge project registry.
"""

from __future__ import annotations

import re
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import AsyncSessionLocal
from db.models import Project

# ============================================================
# CONFIG
# ============================================================

VALID_STATUSES = frozenset(
    {
        "intake",
        "knowledge_building",
        "planning",
        "execution",
        "qa",
        "complete",
        "archived",
    }
)

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")

logger = structlog.get_logger()

router = APIRouter(prefix="/api/projects", tags=["projects"])

# ============================================================
# REQUEST / RESPONSE MODELS
# ============================================================


class ProjectCreate(BaseModel):
    """Request body for creating a new project."""

    project_id: str
    name: str
    client_name: str


class ProjectResponse(BaseModel):
    """Response body representing a project record."""

    project_id: str
    name: str
    client_name: str
    status: str
    manifest_path: str | None
    github_repo: str | None
    created_at: datetime
    updated_at: datetime
    approved_at: datetime | None
    model_config = ConfigDict(from_attributes=True)


class ProjectStatusUpdate(BaseModel):
    """Request body for updating a project's status."""

    status: str


# ============================================================
# DEPENDENCIES
# ============================================================


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session and close it when the request is done."""
    async with AsyncSessionLocal() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]


# ============================================================
# ENDPOINTS
# ============================================================


@router.get("", response_model=list[ProjectResponse], status_code=status.HTTP_200_OK)
async def list_projects(db: DbSession) -> list[Project]:
    """Return all projects in the registry, ordered by creation date descending."""
    result = await db.execute(select(Project).order_by(Project.created_at.desc()))
    projects = result.scalars().all()
    logger.info("projects_listed", count=len(projects))
    return list(projects)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(payload: ProjectCreate, db: DbSession) -> Project:
    """Create a new project.

    Returns 409 if a project with the same project_id already exists.
    Returns 422 if the project_id slug format is invalid.
    """
    if len(payload.project_id) < 2 or not _SLUG_RE.match(payload.project_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "project_id must be lowercase alphanumeric + hyphens, "
                "at least 2 characters, starting and ending with alphanumeric."
            ),
        )

    existing = await db.execute(
        select(Project).where(Project.project_id == payload.project_id)
    )
    if existing.scalars().first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Project '{payload.project_id}' already exists.",
        )

    project = Project(
        project_id=payload.project_id,
        name=payload.name,
        client_name=payload.client_name,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    logger.info(
        "project_created",
        project_id=project.project_id,
        name=project.name,
    )
    return project


@router.get("/{project_id}", response_model=ProjectResponse, status_code=status.HTTP_200_OK)
async def get_project(project_id: str, db: DbSession) -> Project:
    """Return a single project by project_id.

    Returns 404 if the project does not exist.
    """
    result = await db.execute(
        select(Project).where(Project.project_id == project_id)
    )
    project = result.scalars().first()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )
    logger.info("project_fetched", project_id=project_id)
    return project


@router.patch(
    "/{project_id}/status",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
)
async def update_project_status(
    project_id: str,
    payload: ProjectStatusUpdate,
    db: DbSession,
) -> Project:
    """Update the status of an existing project.

    Returns 404 if the project does not exist.
    Returns 422 if the requested status value is not valid.
    """
    if payload.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Invalid status '{payload.status}'. "
                f"Valid values: {sorted(VALID_STATUSES)}"
            ),
        )

    result = await db.execute(
        select(Project).where(Project.project_id == project_id)
    )
    project = result.scalars().first()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )

    old_status = project.status
    project.status = payload.status
    await db.commit()
    await db.refresh(project)

    logger.info(
        "project_status_updated",
        project_id=project_id,
        old_status=old_status,
        new_status=payload.status,
    )
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: str, db: DbSession) -> None:
    """Delete a project by project_id.

    Returns 404 if the project does not exist.
    """
    result = await db.execute(
        select(Project).where(Project.project_id == project_id)
    )
    project = result.scalars().first()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )

    await db.delete(project)
    await db.commit()

    logger.info("project_deleted", project_id=project_id)
