"""FastAPI CRUD router for AutoForge Knowledge Resources.

# REGISTRATION NOTE
# Register this router in api/main.py when branches are merged:
#   from api.routers import knowledge as knowledge_router
#   app.include_router(knowledge_router.router)

Knowledge resources are persisted as JSON files on disk at:
    {KNOWLEDGE_DIR}/{project_id}/resources/{resource_id}.json

The base directory is read from the ``KNOWLEDGE_DIR`` environment variable,
defaulting to ``"knowledge"`` relative to the process working directory.

This router does NOT use a database session — all persistence is file-based.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from schemas.knowledge_resource import KnowledgeResource, ResourceStatus, ResourceType

# ============================================================
# CONFIG
# ============================================================

# Base directory for all knowledge files. Override via env var in production.
_DEFAULT_KNOWLEDGE_DIR = "knowledge"


def _knowledge_dir() -> Path:
    """Return the active knowledge base directory as a Path."""
    return Path(os.environ.get("KNOWLEDGE_DIR", _DEFAULT_KNOWLEDGE_DIR))


def _resource_path(project_id: str, resource_id: str) -> Path:
    """Return the full path for a single resource JSON file."""
    return _knowledge_dir() / project_id / "resources" / f"{resource_id}.json"


def _project_resources_dir(project_id: str) -> Path:
    """Return the directory that holds all resources for a project."""
    return _knowledge_dir() / project_id / "resources"


logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/api/projects/{project_id}/knowledge",
    tags=["knowledge"],
)

# ============================================================
# REQUEST / RESPONSE MODELS
# ============================================================


class KnowledgeResourceCreate(BaseModel):
    """Request body for creating a new knowledge resource.

    The fields ``id``, ``project_id``, ``created_at``, and ``status`` are
    set server-side and must NOT be supplied by the caller.
    """

    resource_type: ResourceType
    title: str
    description: str
    source_url: str | None = None
    file_path: str | None = None
    crawled_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class ResourceStatusUpdate(BaseModel):
    """Request body for updating only the status of a knowledge resource."""

    status: ResourceStatus


# ============================================================
# HELPERS
# ============================================================


def _load_resource(project_id: str, resource_id: str) -> KnowledgeResource:
    """Load a single KnowledgeResource from disk.

    Args:
        project_id: Project slug.
        resource_id: UUID string of the resource.

    Returns:
        Parsed KnowledgeResource.

    Raises:
        HTTPException 404 if the file does not exist.
    """
    path = _resource_path(project_id, resource_id)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge resource '{resource_id}' not found for project '{project_id}'.",
        )
    raw = path.read_text(encoding="utf-8")
    return KnowledgeResource.model_validate_json(raw)


def _save_resource(resource: KnowledgeResource) -> None:
    """Persist a KnowledgeResource to disk, creating parent directories as needed.

    Args:
        resource: The resource to persist.
    """
    path = _resource_path(resource.project_id, resource.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        resource.model_dump_json(indent=2),
        encoding="utf-8",
    )


# ============================================================
# ENDPOINTS
# ============================================================


@router.post(
    "",
    response_model=KnowledgeResource,
    status_code=status.HTTP_201_CREATED,
)
async def create_knowledge_resource(
    project_id: str,
    payload: KnowledgeResourceCreate,
) -> KnowledgeResource:
    """Create a new knowledge resource for the given project.

    Sets ``project_id`` from the URL path, ``created_at`` to the current UTC
    timestamp, and ``status`` to ``pending_crawl``.

    Returns 409 if a resource with the generated ID already exists (extremely
    unlikely with UUID4 but checked for correctness).
    """
    resource = KnowledgeResource(
        project_id=project_id,
        resource_type=payload.resource_type,
        title=payload.title,
        description=payload.description,
        source_url=payload.source_url,
        file_path=payload.file_path,
        crawled_at=payload.crawled_at,
        status=ResourceStatus.pending_crawl,
        metadata=payload.metadata,
        tags=payload.tags,
        created_at=datetime.now(UTC),
    )

    path = _resource_path(project_id, resource.id)
    if path.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Knowledge resource '{resource.id}' already exists.",
        )

    _save_resource(resource)
    logger.info(
        "knowledge_resource_created",
        project_id=project_id,
        resource_id=resource.id,
        resource_type=resource.resource_type,
    )
    return resource


@router.get(
    "",
    response_model=list[KnowledgeResource],
    status_code=status.HTTP_200_OK,
)
async def list_knowledge_resources(project_id: str) -> list[KnowledgeResource]:
    """List all knowledge resources for a project.

    Returns an empty list if the project has no resources or the project
    directory does not exist yet.
    """
    resources_dir = _project_resources_dir(project_id)
    if not resources_dir.exists():
        return []

    resources: list[KnowledgeResource] = []
    for json_file in sorted(resources_dir.glob("*.json")):
        raw = json_file.read_text(encoding="utf-8")
        resources.append(KnowledgeResource.model_validate_json(raw))

    logger.info(
        "knowledge_resources_listed",
        project_id=project_id,
        count=len(resources),
    )
    return resources


@router.get(
    "/{resource_id}",
    response_model=KnowledgeResource,
    status_code=status.HTTP_200_OK,
)
async def get_knowledge_resource(
    project_id: str,
    resource_id: str,
) -> KnowledgeResource:
    """Return a single knowledge resource by ID.

    Returns 404 if the resource does not exist.
    """
    resource = _load_resource(project_id, resource_id)
    logger.info(
        "knowledge_resource_fetched",
        project_id=project_id,
        resource_id=resource_id,
    )
    return resource


@router.patch(
    "/{resource_id}/status",
    response_model=KnowledgeResource,
    status_code=status.HTTP_200_OK,
)
async def update_knowledge_resource_status(
    project_id: str,
    resource_id: str,
    payload: ResourceStatusUpdate,
) -> KnowledgeResource:
    """Update the status of an existing knowledge resource.

    Returns 404 if the resource does not exist.
    Returns 422 if the status value is not a valid ResourceStatus.
    (Pydantic validates the enum automatically.)
    """
    resource = _load_resource(project_id, resource_id)
    old_status = resource.status
    updated = resource.model_copy(update={"status": payload.status})
    _save_resource(updated)

    logger.info(
        "knowledge_resource_status_updated",
        project_id=project_id,
        resource_id=resource_id,
        old_status=old_status,
        new_status=payload.status,
    )
    return updated


@router.delete(
    "/{resource_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_knowledge_resource(
    project_id: str,
    resource_id: str,
) -> None:
    """Delete a knowledge resource.

    Returns 404 if the resource does not exist.
    """
    path = _resource_path(project_id, resource_id)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge resource '{resource_id}' not found for project '{project_id}'.",
        )
    path.unlink()
    logger.info(
        "knowledge_resource_deleted",
        project_id=project_id,
        resource_id=resource_id,
    )
