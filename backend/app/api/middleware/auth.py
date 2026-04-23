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
        "/api/v1/webhooks/customers/data_request",
        "/api/v1/webhooks/customers/redact",
        "/api/v1/webhooks/shop/redact",
        "/api/v1/tracking/pageview",
        "/api/v1/tracking/event",
        "/docs",
        "/openapi.json",
    }
)

# Path prefixes that are public — covers debug routes only mounted
# outside production.
PUBLIC_PREFIXES: tuple[str, ...] = ("/api/v1/debug",)

# Token → (merchant_id, email, expires_at_epoch). TTL kept short so
# revoked sessions don't linger beyond a minute.
_CACHE_TTL_SECONDS = 60
_cache: dict[str, tuple[str, str, float]] = {}


def _cached(token: str) -> tuple[str, str] | None:
    entry = _cache.get(token)
    if not entry:
        return None
    merchant_id, email, expires = entry
    if expires < time.monotonic():
        _cache.pop(token, None)
        return None
    return merchant_id, email


def _store(token: str, merchant_id: str, email: str) -> None:
    _cache[token] = (merchant_id, email, time.monotonic() + _CACHE_TTL_SECONDS)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Validate Supabase-issued access tokens on protected routes."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path
        if (
            path in PUBLIC_PATHS
            or any(path.startswith(p) for p in PUBLIC_PREFIXES)
            or request.method == "OPTIONS"
        ):
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

        cached = _cached(token)
        if cached is None:
            try:
                supabase = get_supabase_anon()
                user_response = await asyncio.to_thread(
                    supabase.auth.get_user, token
                )
                user = getattr(user_response, "user", None)
                if user is None or not getattr(user, "id", None):
                    raise ValueError("no user in response")
                merchant_id = user.id
                # `email` comes straight from auth.users — Supabase signs the
                # JWT against this row, so it can't be forged by mutating the
                # public.merchants table.
                email = (getattr(user, "email", "") or "").lower()
                _store(token, merchant_id, email)
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
        else:
            merchant_id, email = cached

        request.state.merchant_id = merchant_id
        request.state.auth_email = email
        return await call_next(request)
