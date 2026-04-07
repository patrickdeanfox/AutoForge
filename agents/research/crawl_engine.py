"""Async URL crawler for the AutoForge Research Agent.

Fetches URLs, detects content types, identifies Swagger/OpenAPI specifications,
and extracts structured metadata from each response.
"""

from __future__ import annotations

# ============================================================
# CONFIG
# ============================================================
import asyncio
import importlib.util
import re
from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import BaseModel

_YAML_AVAILABLE: bool = importlib.util.find_spec("yaml") is not None

if _YAML_AVAILABLE:
    import yaml  # type: ignore[import]

# Maximum bytes to read from a response body by default (512 KB)
_DEFAULT_MAX_CONTENT_BYTES: int = 512 * 1024

# Default seconds to wait between successive requests
_DEFAULT_RATE_LIMIT_DELAY: float = 1.0

# Default request timeout in seconds
_DEFAULT_TIMEOUT: float = 15.0

# Default User-Agent header
_DEFAULT_USER_AGENT: str = "AutoForge-CrawlEngine/1.0 (+https://github.com/autoforge)"

# Maximum characters of stripped body text to store as summary
_SUMMARY_MAX_CHARS: int = 500

# Number of leading characters to inspect for YAML swagger/openapi marker (string fallback)
_YAML_PROBE_CHARS: int = 2000

# Common Swagger/OpenAPI endpoint paths to probe
_SWAGGER_PROBE_PATHS: list[str] = [
    "/openapi.json",
    "/openapi.yaml",
    "/swagger.json",
    "/swagger.yaml",
    "/api-docs",
    "/api/openapi.json",
    "/docs/openapi.json",
    "/v2/api-docs",
]

# HTML tag stripping regex
_HTML_TAG_RE: re.Pattern[str] = re.compile(r"<[^>]+>")

# HTML title tag extraction regex
_HTML_TITLE_RE: re.Pattern[str] = re.compile(
    r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL
)


# ============================================================
# MODELS
# ============================================================


class CrawlResult(BaseModel):
    """Structured result from a single URL crawl operation."""

    url: str
    status_code: int | None  # None if request failed before a response was received
    content_type: str | None  # e.g. "application/json", "text/html"
    content_length: int  # bytes
    is_swagger: bool  # True if detected as a Swagger/OpenAPI specification
    swagger_version: str | None  # "2.0", "3.0.x", etc. if detected
    title: str | None  # <title> if HTML; info.title if Swagger
    summary: str | None  # first 500 chars of stripped body text
    crawled_at: datetime  # UTC timestamp
    error: str | None  # error message if fetch failed, else None
    elapsed_ms: int  # request round-trip time in milliseconds


# ============================================================
# HELPERS
# ============================================================


def _strip_html_tags(raw: str) -> str:
    """Return plain text with all HTML tags removed and whitespace collapsed."""
    text = _HTML_TAG_RE.sub(" ", raw)
    return " ".join(text.split())


def _extract_html_title(raw: str) -> str | None:
    """Return the content of the first <title> tag, or None if absent."""
    match = _HTML_TITLE_RE.search(raw)
    if match:
        return match.group(1).strip() or None
    return None


def _detect_swagger(
    content_type: str | None,
    body: bytes,
) -> tuple[bool, str | None, str | None]:
    """Analyse response body for Swagger/OpenAPI markers.

    Returns:
        (is_swagger, swagger_version, swagger_title)
    """
    if not content_type:
        return False, None, None

    ct_lower = content_type.lower().split(";")[0].strip()

    if ct_lower in ("application/json", "text/json"):
        return _detect_swagger_json(body)

    if ct_lower in ("application/yaml", "text/yaml", "application/x-yaml", "text/x-yaml"):
        return _detect_swagger_yaml(body)

    return False, None, None


def _detect_swagger_json(body: bytes) -> tuple[bool, str | None, str | None]:
    """Parse body as JSON and check for swagger/openapi keys."""
    try:
        import json

        data: Any = json.loads(body)
    except Exception:
        return False, None, None
    return _check_swagger_dict(data)


def _detect_swagger_yaml(body: bytes) -> tuple[bool, str | None, str | None]:
    """Parse body as YAML (or fall back to string detection) and check swagger keys."""
    if _YAML_AVAILABLE:
        try:
            data: Any = yaml.safe_load(body.decode("utf-8", errors="replace"))
            if isinstance(data, dict):
                return _check_swagger_dict(data)
        except Exception:
            pass

    # String-based fallback
    text = body[:_YAML_PROBE_CHARS].decode("utf-8", errors="replace")
    if re.search(r"^swagger\s*:", text, re.MULTILINE):
        version_match = re.search(r"^swagger\s*:\s*['\"]?([^\s'\"]+)", text, re.MULTILINE)
        version = version_match.group(1) if version_match else None
        return True, version, None
    if re.search(r"^openapi\s*:", text, re.MULTILINE):
        version_match = re.search(r"^openapi\s*:\s*['\"]?([^\s'\"]+)", text, re.MULTILINE)
        version = version_match.group(1) if version_match else None
        return True, version, None

    return False, None, None


def _check_swagger_dict(data: Any) -> tuple[bool, str | None, str | None]:
    """Inspect a parsed dict for swagger/openapi top-level keys."""
    if not isinstance(data, dict):
        return False, None, None

    version: str | None = None
    title: str | None = None

    if "swagger" in data:
        version = str(data["swagger"])
    elif "openapi" in data:
        version = str(data["openapi"])
    else:
        return False, None, None

    info = data.get("info")
    if isinstance(info, dict):
        raw_title = info.get("title")
        title = str(raw_title) if raw_title is not None else None

    return True, version, title


def _base_url(url: str) -> str:
    """Return scheme + host + port from a full URL (strip path/query/fragment)."""
    parsed = httpx.URL(url)
    port_part = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{parsed.host}{port_part}"


# ============================================================
# CRAWL ENGINE
# ============================================================


class CrawlEngine:
    """Async URL crawler for the AutoForge Research Agent.

    Fetches URLs, detects content types, identifies Swagger/OpenAPI specs,
    and extracts structured metadata from each response.

    Uses httpx.AsyncClient internally. Must be used as an async context manager
    or explicitly closed via aclose().

    Args:
        rate_limit_delay: Seconds to wait between successive requests. Default 1.0.
        timeout: Request timeout in seconds. Default 15.0.
        user_agent: User-Agent header value sent with every request.
        max_content_bytes: Maximum response body size to read. Default 512 KB.
    """

    def __init__(
        self,
        rate_limit_delay: float = _DEFAULT_RATE_LIMIT_DELAY,
        timeout: float = _DEFAULT_TIMEOUT,
        user_agent: str = _DEFAULT_USER_AGENT,
        max_content_bytes: int = _DEFAULT_MAX_CONTENT_BYTES,
        _transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._rate_limit_delay = rate_limit_delay
        self._max_content_bytes = max_content_bytes
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={"User-Agent": user_agent},
            follow_redirects=True,
            transport=_transport,
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def crawl_url(self, url: str) -> CrawlResult:
        """Fetch a single URL and return a structured CrawlResult.

        Non-200 HTTP status codes are recorded but are NOT treated as errors.
        Network-level failures (timeouts, connection errors) set the error field.

        Args:
            url: Fully-qualified URL to fetch.

        Returns:
            CrawlResult with all available metadata populated.
        """
        crawled_at = datetime.now(UTC)
        start_ms = _now_ms()

        try:
            response = await self._client.get(url)
            elapsed_ms = _now_ms() - start_ms

            body = response.content[: self._max_content_bytes]
            raw_content_type = response.headers.get("content-type")
            content_type = (
                raw_content_type.split(";")[0].strip() if raw_content_type else None
            )

            is_swagger, swagger_version, swagger_title = _detect_swagger(
                raw_content_type, body
            )

            title: str | None = swagger_title
            summary: str | None = None

            if not title and content_type and content_type.startswith("text/html"):
                body_text = body.decode("utf-8", errors="replace")
                title = _extract_html_title(body_text)
                stripped = _strip_html_tags(body_text)
                summary = stripped[:_SUMMARY_MAX_CHARS] if stripped else None
            elif not is_swagger:
                body_text = body.decode("utf-8", errors="replace")
                stripped = _strip_html_tags(body_text)
                summary = stripped[:_SUMMARY_MAX_CHARS] if stripped else None

            return CrawlResult(
                url=url,
                status_code=response.status_code,
                content_type=content_type,
                content_length=len(body),
                is_swagger=is_swagger,
                swagger_version=swagger_version,
                title=title,
                summary=summary,
                crawled_at=crawled_at,
                error=None,
                elapsed_ms=elapsed_ms,
            )

        except httpx.TimeoutException:
            return CrawlResult(
                url=url,
                status_code=None,
                content_type=None,
                content_length=0,
                is_swagger=False,
                swagger_version=None,
                title=None,
                summary=None,
                crawled_at=crawled_at,
                error="timeout",
                elapsed_ms=_now_ms() - start_ms,
            )
        except httpx.RequestError as exc:
            return CrawlResult(
                url=url,
                status_code=None,
                content_type=None,
                content_length=0,
                is_swagger=False,
                swagger_version=None,
                title=None,
                summary=None,
                crawled_at=crawled_at,
                error=str(exc),
                elapsed_ms=_now_ms() - start_ms,
            )
        except Exception as exc:  # noqa: BLE001
            return CrawlResult(
                url=url,
                status_code=None,
                content_type=None,
                content_length=0,
                is_swagger=False,
                swagger_version=None,
                title=None,
                summary=None,
                crawled_at=crawled_at,
                error=str(exc),
                elapsed_ms=_now_ms() - start_ms,
            )

    async def crawl_urls(self, urls: list[str]) -> list[CrawlResult]:
        """Crawl a list of URLs sequentially with rate limiting between each.

        Args:
            urls: List of fully-qualified URLs to fetch.

        Returns:
            List of CrawlResult objects in the same order as the input URLs.
        """
        results: list[CrawlResult] = []
        for index, url in enumerate(urls):
            if index > 0:
                await asyncio.sleep(self._rate_limit_delay)
            result = await self.crawl_url(url)
            results.append(result)
        return results

    async def detect_swagger_endpoints(self, base_url: str) -> list[CrawlResult]:
        """Probe common Swagger/OpenAPI endpoint paths on a base URL.

        Probes the following paths appended to the scheme+host of base_url:
        /openapi.json, /openapi.yaml, /swagger.json, /swagger.yaml,
        /api-docs, /api/openapi.json, /docs/openapi.json, /v2/api-docs

        Args:
            base_url: Any URL whose scheme+host will be used as the probe origin.

        Returns:
            CrawlResults only for paths that returned HTTP 200 with Swagger content.
        """
        origin = _base_url(base_url)
        probe_urls = [f"{origin}{path}" for path in _SWAGGER_PROBE_PATHS]

        swagger_results: list[CrawlResult] = []
        for index, url in enumerate(probe_urls):
            if index > 0:
                await asyncio.sleep(self._rate_limit_delay)
            result = await self.crawl_url(url)
            if result.status_code == 200 and result.is_swagger:
                swagger_results.append(result)

        return swagger_results

    async def aclose(self) -> None:
        """Close the underlying httpx client and release all connections."""
        await self._client.aclose()

    async def __aenter__(self) -> CrawlEngine:
        """Enter the async context manager, returning self."""
        return self

    async def __aexit__(self, *args: object) -> None:
        """Exit the async context manager, closing the client."""
        await self.aclose()


# ============================================================
# INIT (module-level utility)
# ============================================================


def _now_ms() -> int:
    """Return current UTC time in milliseconds since epoch."""
    return int(datetime.now(UTC).timestamp() * 1000)
