"""API key authentication middleware for AutoForge internal endpoints.

All non-public API routes require a valid ``X-AutoForge-API-Key`` header.
The key is compared against the ``AUTOFORGE_API_KEY`` environment variable
using a constant-time comparison to prevent timing attacks.

Public routes (health, status, GitHub webhooks) bypass this middleware.
"""

from __future__ import annotations

import hmac
import os

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

logger = structlog.get_logger()

# ============================================================
# CONFIG
# ============================================================

# Routes that do not require API key authentication.
PUBLIC_PATHS: frozenset[str] = frozenset(
    {
        "/health",
        "/api/status",
        "/api/github/webhook",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
)


# ============================================================
# MIDDLEWARE
# ============================================================


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that enforces X-AutoForge-API-Key on protected routes.

    Reads the expected key from the ``AUTOFORGE_API_KEY`` environment variable
    at startup. If the variable is empty or unset, authentication is disabled
    and a warning is logged — this is acceptable in local dev but must not
    occur in staging or production.
    """

    def __init__(self, app: any, environment: str = "development") -> None:
        super().__init__(app)
        self._api_key = os.environ.get("AUTOFORGE_API_KEY", "")
        self._environment = environment
        if not self._api_key:
            logger.warning(
                "api_key_auth_disabled",
                reason="AUTOFORGE_API_KEY not set",
                environment=environment,
            )

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Allow public paths through; validate API key on all others."""
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        # Auth is disabled in dev if the key is not configured
        if not self._api_key:
            return await call_next(request)

        provided_key = request.headers.get("X-AutoForge-API-Key", "")
        if not _constant_time_equal(provided_key, self._api_key):
            logger.warning(
                "api_auth_failure",
                path=request.url.path,
                method=request.method,
            )
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"},
            )

        return await call_next(request)


def _constant_time_equal(a: str, b: str) -> bool:
    """Compare two strings in constant time to prevent timing attacks."""
    return hmac.compare_digest(a.encode(), b.encode())
