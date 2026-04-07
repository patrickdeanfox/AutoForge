"""AutoForge ResearchAgent — Phase 1 skeleton.

The ResearchAgent crawls seed URLs, introspects external APIs and data sources, and
populates the Layer 1 knowledge base for a project. This file contains the Phase 1
skeleton: session logging and per-URL step contexts are wired; the real CrawlEngine
integration will be added in a follow-up PR.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import anthropic

from agents.base.base_agent import BaseAgent


class ResearchAgent(BaseAgent):
    """Research agent responsible for crawling external resources and building Layer 1 knowledge.

    Uses Claude Opus (claude-opus-4-6) for reasoning over crawled content. In Phase 1 this
    agent logs all steps and processes seed URLs but defers actual HTTP crawling to the
    CrawlEngine, which is integrated in a follow-up PR.

    Args:
        project_id: The project slug this agent is researching.
        issue_id: The GitHub Issue identifier authorising this research run.
        manifest_path: Path to the project's ``project_manifest.json``.
        employer_profile_path: Path to ``config/employer_profile.json``.
        seed_urls: Starting URLs the agent will crawl for knowledge resources.
    """

    service_name = "research-agent"

    # Model used for research reasoning tasks
    _MODEL = "claude-opus-4-6"

    def __init__(
        self,
        project_id: str,
        issue_id: str,
        manifest_path: Path,
        employer_profile_path: Path,
        seed_urls: list[str],
    ) -> None:
        """Initialise ResearchAgent with seed URLs and Anthropic client.

        Args:
            project_id: The project slug.
            issue_id: GitHub Issue identifier (e.g. ``"GH-12"``).
            manifest_path: Path to ``project_manifest.json``.
            employer_profile_path: Path to ``config/employer_profile.json``.
            seed_urls: List of URLs to crawl during the research run.
        """
        super().__init__(
            project_id=project_id,
            issue_id=issue_id,
            manifest_path=manifest_path,
            employer_profile_path=employer_profile_path,
        )
        self._seed_urls: list[str] = seed_urls
        self._anthropic = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY"),
        )

    async def run(self) -> dict[str, Any]:
        """Execute the research agent's primary task.

        Phase 1 behaviour:
        - Emits a ``session_start`` log event.
        - Iterates over ``seed_urls``, emitting a ``step_start`` / ``step_complete``
          pair per URL via ``step_context()``.
        - Returns a summary dict with status and counts.

        Returns:
            A dict with keys:
            - ``"status"``: ``"complete"``
            - ``"urls_processed"``: number of seed URLs iterated
            - ``"findings"``: empty list (populated by CrawlEngine in follow-up PR)
        """
        # structlog uses the first positional argument as the "event" field.
        self.logger.info(
            "session_start",
            step="session_start",
            duration_ms=0,
            tokens_used=0,
            outcome="success",
            metadata={"seed_url_count": len(self._seed_urls)},
        )

        findings: list[dict[str, Any]] = []

        for url in self._seed_urls:
            # TODO: Wire CrawlEngine here when available
            async with self.step_context("crawl_url", metadata={"url": url}):
                # Phase 1: log the URL and yield — real crawl logic lives in CrawlEngine
                self.logger.info(
                    "crawl_url_placeholder",
                    step="crawl_url",
                    duration_ms=0,
                    tokens_used=0,
                    outcome="success",
                    metadata={"url": url, "note": "CrawlEngine not yet wired"},
                )

        self.logger.info(
            "session_complete",
            step="session_complete",
            duration_ms=0,
            tokens_used=0,
            outcome="success",
            metadata={
                "urls_processed": len(self._seed_urls),
                "findings_count": len(findings),
            },
        )

        return {
            "status": "complete",
            "urls_processed": len(self._seed_urls),
            "findings": findings,
        }
