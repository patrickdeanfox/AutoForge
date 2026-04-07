"""FastAPI router for manifest merge operations.

Provides an endpoint that merges a project intake form submission with the
Layer 0 EmployerProfile to produce a validated ProjectManifest.

The produced manifest is written to disk under ``manifests/{project_id}/`` and
the project's ``manifest_path`` DB field is updated. The manifest is unapproved
(``approved_at=None``) — approval is a separate human action.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import AsyncSessionLocal
from db.models import Project
from orchestration.manifest_merger import ManifestMergeError, ManifestMerger
from schemas.project_intake import ProjectIntake
from schemas.project_manifest import ProjectManifest

# ============================================================
# CONFIG
# ============================================================

# Path to the employer profile — used to initialise ManifestMerger.
_EMPLOYER_PROFILE_PATH = Path(
    os.environ.get("EMPLOYER_PROFILE_PATH", "config/employer_profile.json")
)

# Directory where merged manifests are written, one subdir per project.
_MANIFESTS_DIR = Path(os.environ.get("MANIFESTS_DIR", "manifests"))

logger = structlog.get_logger()

router = APIRouter(prefix="/api/projects", tags=["manifests"])


# ============================================================
# DEPENDENCIES
# ============================================================


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    async with AsyncSessionLocal() as session:
        yield session


def get_merger() -> ManifestMerger:
    """Return a ManifestMerger initialised from the employer profile on disk.

    Raises:
        HTTPException 503: If the employer profile file is missing.
    """
    if not _EMPLOYER_PROFILE_PATH.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"Employer profile not found at '{_EMPLOYER_PROFILE_PATH}'. "
                "Cannot merge manifest without Layer 0."
            ),
        )
    return ManifestMerger(_EMPLOYER_PROFILE_PATH)


DbSession = Annotated[AsyncSession, Depends(get_db)]
MergerDep = Annotated[ManifestMerger, Depends(get_merger)]


# ============================================================
# ENDPOINTS
# ============================================================


@router.post(
    "/{project_id}/manifest",
    response_model=ProjectManifest,
    status_code=status.HTTP_201_CREATED,
    summary="Merge intake form with Layer 0 to produce a project manifest",
)
async def create_manifest(
    project_id: str,
    intake: ProjectIntake,
    db: DbSession,
    merger: MergerDep,
) -> ProjectManifest:
    """Merge a project intake submission with the employer profile to produce a manifest.

    The ``project_id`` in the URL must match the ``project_id`` in the request body.
    The project must already exist in the registry (created via POST /api/projects).

    The merged manifest is:
    - Validated against Layer 0 constraints (forbidden technologies, etc.)
    - Written to ``manifests/{project_id}/project_manifest.json``
    - Linked to the project DB record via ``manifest_path``
    - Returned as JSON for the engineer to review

    The manifest is unapproved (``approved_at=None``). Approval is a separate
    human-in-the-loop step.

    Returns:
        The fully validated ProjectManifest.

    Raises:
        400: If the URL project_id does not match the intake body project_id.
        404: If the project does not exist in the registry.
        409: If a manifest already exists for this project.
        422: If the intake violates employer profile constraints (forbidden tools, etc.).
        503: If the employer profile file is missing.
    """
    log = logger.bind(project_id=project_id)

    if intake.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"URL project_id '{project_id}' does not match "
                f"body project_id '{intake.project_id}'."
            ),
        )

    result = await db.execute(select(Project).where(Project.project_id == project_id))
    project = result.scalars().first()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found. Create it first via POST /api/projects.",
        )

    if project.manifest_path is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Project '{project_id}' already has a manifest at '{project.manifest_path}'. "
                "Delete it or use a new project_id."
            ),
        )

    try:
        manifest = merger.merge(intake)
    except ManifestMergeError as exc:
        log.warning("manifest_merge_rejected", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    manifest_dir = _MANIFESTS_DIR / project_id
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_file = manifest_dir / "project_manifest.json"
    manifest_file.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2)
    )

    project.manifest_path = str(manifest_file)
    await db.commit()
    await db.refresh(project)

    log.info(
        "manifest_created",
        manifest_path=str(manifest_file),
        employer_standards_version=manifest.employer_standards_version,
    )
    return manifest
