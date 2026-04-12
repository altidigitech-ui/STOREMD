"""JWT validation middleware for Supabase Auth.

Tokens are issued and signed by Supabase (via admin.generate_link in
auth/callback). Since the Supabase JWT secret is not available to this
service, we validate incoming tokens by calling Supabase's /auth/v1/user
endpoint via the anon client. Results are cached briefly in-process to
avoid a round-trip per request.
"""

from __future__ import annotations

import asyncio
import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.exceptions import ErrorCode
from app.dependencies import get_supabase_anon

logger = structlog.get_logger()

PUBLIC_PATHS = frozenset(
    {
        "/api/v1/health",
        "/api/v1/auth/install",
        "/api/v1/auth/callback",
        "/api/v1/webhooks/shopify",
        "/api/v1/webhooks/stripe",
        "/docs",
        "/openapi.json",
    }
)

# Token → (merchant_id, expires_at_epoch). TTL kept short so revoked
# sessions don't linger beyond a minute.
_CACHE_TTL_SECONDS = 60
_cache: dict[str, tuple[str, float]] = {}


def _cached(token: str) -> str | None:
    entry = _cache.get(token)
    if not entry:
        return None
    merchant_id, expires = entry
    if expires < time.monotonic():
        _cache.pop(token, None)
        return None
    return merchant_id


def _store(token: str, merchant_id: str) -> None:
    _cache[token] = (merchant_id, time.monotonic() + _CACHE_TTL_SECONDS)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Validate Supabase-issued access tokens on protected routes."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path
        if path in PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": ErrorCode.JWT_INVALID.value,
                        "message": "Missing or invalid Authorization header",
                    }
                },
            )

        token = auth_header.removeprefix("Bearer ")

        merchant_id = _cached(token)
        if merchant_id is None:
            try:
                supabase = get_supabase_anon()
                user_response = await asyncio.to_thread(
                    supabase.auth.get_user, token
                )
                user = getattr(user_response, "user", None)
                if user is None or not getattr(user, "id", None):
                    raise ValueError("no user in response")
                merchant_id = user.id
                _store(token, merchant_id)
            except Exception as exc:
                logger.info(
                    "jwt_validation_failed",
                    error=str(exc),
                    path=path,
                )
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": {
                            "code": ErrorCode.JWT_INVALID.value,
                            "message": "Invalid or expired token",
                        }
                    },
                )

        request.state.merchant_id = merchant_id
        return await call_next(request)
