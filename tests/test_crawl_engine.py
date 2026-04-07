"""Tests for agents.research.crawl_engine.

Uses httpx's MockTransport to intercept all HTTP calls without hitting the network.
Tests cover happy paths, error handling, Swagger detection, and the context manager
interface.
"""

from __future__ import annotations

import json
from datetime import UTC

import httpx

from agents.research.crawl_engine import CrawlEngine, CrawlResult

# ============================================================
# CONFIG
# ============================================================
RATE_LIMIT_DELAY_ZERO: float = 0.0  # no sleep during tests


# ============================================================
# TRANSPORT HELPERS
# ============================================================


def _make_transport(handler: httpx.AsyncBaseTransport) -> httpx.AsyncBaseTransport:
    """Return the handler unchanged; named for readability at call sites."""
    return handler


class _StaticResponse(httpx.AsyncBaseTransport):
    """Returns the same response for every request."""

    def __init__(
        self,
        status_code: int = 200,
        content: bytes = b"",
        content_type: str = "text/plain",
    ) -> None:
        self._status_code = status_code
        self._content = content
        self._content_type = content_type

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=self._status_code,
            headers={"content-type": self._content_type},
            content=self._content,
            request=request,
        )


class _RouteTransport(httpx.AsyncBaseTransport):
    """Returns different responses based on URL path."""

    def __init__(self, routes: dict[str, tuple[int, bytes, str]]) -> None:
        # routes: { "/path": (status_code, content, content_type) }
        self._routes = routes

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path in self._routes:
            status_code, content, content_type = self._routes[path]
        else:
            status_code, content, content_type = 404, b"Not Found", "text/plain"
        return httpx.Response(
            status_code=status_code,
            headers={"content-type": content_type},
            content=content,
            request=request,
        )


class _RaisingTransport(httpx.AsyncBaseTransport):
    """Raises a given exception for every request."""

    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        raise self._exc


def _engine(transport: httpx.AsyncBaseTransport) -> CrawlEngine:
    """Construct a CrawlEngine with zero rate-limit delay for fast tests."""
    return CrawlEngine(
        rate_limit_delay=RATE_LIMIT_DELAY_ZERO,
        _transport=transport,
    )


# ============================================================
# TESTS
# ============================================================


async def test_crawl_url_returns_crawl_result_for_200_response() -> None:
    """A 200 JSON response produces a valid CrawlResult with no error."""
    body = json.dumps({"key": "value"}).encode()
    transport = _StaticResponse(200, body, "application/json")
    async with _engine(transport) as engine:
        result = await engine.crawl_url("http://example.com/data")

    assert isinstance(result, CrawlResult)
    assert result.status_code == 200
    assert result.error is None
    assert result.url == "http://example.com/data"


async def test_crawl_url_captures_status_code() -> None:
    """A 404 response is not an error — status_code is recorded accurately."""
    transport = _StaticResponse(404, b"Not Found", "text/plain")
    async with _engine(transport) as engine:
        result = await engine.crawl_url("http://example.com/missing")

    assert result.status_code == 404
    assert result.error is None


async def test_crawl_url_on_timeout_sets_error_field() -> None:
    """A timeout exception sets error='timeout' and status_code=None."""
    transport = _RaisingTransport(
        httpx.TimeoutException("timed out", request=httpx.Request("GET", "http://x.com"))
    )
    async with _engine(transport) as engine:
        result = await engine.crawl_url("http://x.com/slow")

    assert result.status_code is None
    assert result.error == "timeout"
    assert result.is_swagger is False


async def test_crawl_url_on_connection_error_sets_error_field() -> None:
    """A connection error sets the error field with the exception message."""
    exc = httpx.ConnectError("connection refused")
    transport = _RaisingTransport(exc)
    async with _engine(transport) as engine:
        result = await engine.crawl_url("http://unreachable.local/")

    assert result.status_code is None
    assert result.error is not None
    assert len(result.error) > 0
    assert result.is_swagger is False


async def test_crawl_url_detects_swagger_json_v2() -> None:
    """A Swagger 2.0 JSON body is detected with correct version and title."""
    spec = {
        "swagger": "2.0",
        "info": {"title": "Pet Store API", "version": "1.0"},
        "paths": {},
    }
    body = json.dumps(spec).encode()
    transport = _StaticResponse(200, body, "application/json")
    async with _engine(transport) as engine:
        result = await engine.crawl_url("http://api.example.com/swagger.json")

    assert result.is_swagger is True
    assert result.swagger_version == "2.0"
    assert result.title == "Pet Store API"


async def test_crawl_url_detects_swagger_json_v3() -> None:
    """An OpenAPI 3.0.1 JSON body is detected with correct version and title."""
    spec = {
        "openapi": "3.0.1",
        "info": {"title": "Orders API", "version": "2.0"},
        "paths": {},
    }
    body = json.dumps(spec).encode()
    transport = _StaticResponse(200, body, "application/json")
    async with _engine(transport) as engine:
        result = await engine.crawl_url("http://api.example.com/openapi.json")

    assert result.is_swagger is True
    assert result.swagger_version == "3.0.1"
    assert result.title == "Orders API"


async def test_crawl_url_non_swagger_json_is_not_flagged() -> None:
    """Regular JSON without swagger/openapi keys is NOT flagged as Swagger."""
    body = json.dumps({"users": [], "count": 0}).encode()
    transport = _StaticResponse(200, body, "application/json")
    async with _engine(transport) as engine:
        result = await engine.crawl_url("http://api.example.com/users")

    assert result.is_swagger is False
    assert result.swagger_version is None


async def test_crawl_url_html_extracts_title() -> None:
    """HTML response has its <title> tag extracted into result.title."""
    html = b"""
    <html>
      <head><title>My Dashboard</title></head>
      <body><p>Hello world</p></body>
    </html>
    """
    transport = _StaticResponse(200, html, "text/html; charset=utf-8")
    async with _engine(transport) as engine:
        result = await engine.crawl_url("http://example.com/")

    assert result.title == "My Dashboard"
    assert result.is_swagger is False


async def test_crawl_url_elapsed_ms_is_non_negative_int() -> None:
    """elapsed_ms must be a non-negative integer for every successful request."""
    transport = _StaticResponse(200, b"ok", "text/plain")
    async with _engine(transport) as engine:
        result = await engine.crawl_url("http://example.com/ping")

    assert isinstance(result.elapsed_ms, int)
    assert result.elapsed_ms >= 0


async def test_crawl_urls_returns_result_for_each_url() -> None:
    """crawl_urls produces one CrawlResult per URL, in input order."""
    transport = _StaticResponse(200, b"ok", "text/plain")
    urls = [
        "http://example.com/a",
        "http://example.com/b",
        "http://example.com/c",
    ]
    async with _engine(transport) as engine:
        results = await engine.crawl_urls(urls)

    assert len(results) == 3
    assert [r.url for r in results] == urls


async def test_detect_swagger_endpoints_returns_only_200_swagger_results() -> None:
    """Only paths that respond 200 with Swagger content appear in the return list."""
    swagger_body = json.dumps(
        {"openapi": "3.0.0", "info": {"title": "Test API", "version": "1"}, "paths": {}}
    ).encode()

    routes: dict[str, tuple[int, bytes, str]] = {
        "/openapi.json": (200, swagger_body, "application/json"),
        # all other probe paths return 404 (handled by _RouteTransport default)
    }
    transport = _RouteTransport(routes)
    async with _engine(transport) as engine:
        results = await engine.detect_swagger_endpoints("http://api.example.com/some/path")

    assert len(results) == 1
    assert results[0].is_swagger is True
    assert results[0].status_code == 200
    assert "/openapi.json" in results[0].url


async def test_crawl_engine_as_async_context_manager() -> None:
    """CrawlEngine works correctly as an async context manager."""
    transport = _StaticResponse(200, b"hello", "text/plain")
    async with CrawlEngine(rate_limit_delay=0.0, _transport=transport) as engine:
        result = await engine.crawl_url("http://example.com/")

    assert result.status_code == 200


async def test_crawl_result_crawled_at_is_utc() -> None:
    """crawled_at must be a timezone-aware datetime in UTC."""
    transport = _StaticResponse(200, b"x", "text/plain")
    async with _engine(transport) as engine:
        result = await engine.crawl_url("http://example.com/")

    assert result.crawled_at.tzinfo is not None
    assert result.crawled_at.tzinfo == UTC
