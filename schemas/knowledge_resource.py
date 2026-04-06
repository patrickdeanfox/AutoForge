"""Pydantic v2 schema for AutoForge Knowledge Resources.

Knowledge Resources are the artifacts gathered during the research phase of a project:
API docs, Swagger specs, database schemas, sample data, legacy code, environment
templates, Postman collections, ERDs, and anything else the Research Agent crawls.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


# ============================================================
# Enums
# ============================================================


class ResourceType(str, Enum):
    """The nature of the knowledge resource."""

    api_docs = "api_docs"
    swagger_spec = "swagger_spec"
    database_schema = "database_schema"
    sample_data = "sample_data"
    legacy_code = "legacy_code"
    env_template = "env_template"
    postman_collection = "postman_collection"
    erd = "erd"
    other = "other"


class ResourceStatus(str, Enum):
    """Current crawl/ingestion status of the resource."""

    pending_crawl = "pending_crawl"
    crawled = "crawled"
    stale = "stale"
    failed = "failed"


# ============================================================
# Root model
# ============================================================


class KnowledgeResource(BaseModel):
    """A single knowledge artifact associated with a project.

    Either ``source_url`` or ``file_path`` (or both) must be supplied — a resource
    with neither cannot be located or crawled.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    resource_type: ResourceType
    title: str
    description: str
    source_url: str | None = None
    file_path: str | None = None
    crawled_at: datetime | None = None
    status: ResourceStatus = ResourceStatus.pending_crawl
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="after")
    def require_source_url_or_file_path(self) -> "KnowledgeResource":
        """Ensure at least one locator (source_url or file_path) is provided."""
        if self.source_url is None and self.file_path is None:
            raise ValueError(
                "At least one of source_url or file_path must be set on a KnowledgeResource"
            )
        return self
