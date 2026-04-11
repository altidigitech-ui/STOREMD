"""FastAPI dependency injection — Supabase clients, Redis, auth, billing."""

from __future__ import annotations

import jwt
import redis.asyncio as aioredis
import structlog
from fastapi import Depends, Request
from supabase import Client as SupabaseClient
from supabase import create_client

from app.config import settings
from app.core.exceptions import AuthError, ErrorCode

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Singletons (created once, reused across requests)
# ---------------------------------------------------------------------------

_supabase_service: SupabaseClient | None = None
_supabase_anon: SupabaseClient | None = None
_redis: aioredis.Redis | None = None


def get_supabase_service() -> SupabaseClient:
    """Supabase client with service_role key — bypasses RLS.

    Used for webhooks, admin tasks, cross-store intelligence.
    """
    global _supabase_service
    if _supabase_service is None:
        _supabase_service = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY,
        )
    return _supabase_service


def get_supabase_anon() -> SupabaseClient:
    """Supabase client with anon key — respects RLS."""
    global _supabase_anon
    if _supabase_anon is None:
        _supabase_anon = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_ANON_KEY,
        )
    return _supabase_anon


def get_redis() -> aioredis.Redis:
    """Async Redis client (rate limiting, OAuth state, caching)."""
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
    return _redis


# ---------------------------------------------------------------------------
# Auth dependencies
# ---------------------------------------------------------------------------


async def get_current_merchant(request: Request) -> dict:
    """Extract and validate the JWT from the Authorization header.

    Returns the merchant record from Supabase.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise AuthError(
            code=ErrorCode.JWT_INVALID,
            message="Missing or invalid Authorization header",
            status_code=401,
        )

    token = auth_header.removeprefix("Bearer ")

    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthError(
            code=ErrorCode.JWT_EXPIRED,
            message="Token expired",
            status_code=401,
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError(
            code=ErrorCode.JWT_INVALID,
            message="Invalid token",
            status_code=401,
        ) from exc

    merchant_id = payload.get("sub")
    if not merchant_id:
        raise AuthError(
            code=ErrorCode.JWT_INVALID,
            message="Token missing subject",
            status_code=401,
        )

    supabase = get_supabase_service()
    result = supabase.table("merchants").select("*").eq("id", merchant_id).maybe_single().execute()

    if not result.data:
        raise AuthError(
            code=ErrorCode.MERCHANT_NOT_FOUND,
            message="Merchant profile not found",
            status_code=401,
        )

    return result.data


async def get_current_store(
    store_id: str,
    merchant: dict = Depends(get_current_merchant),
) -> dict:
    """Validate that the store belongs to the current merchant."""
    supabase = get_supabase_service()
    result = (
        supabase.table("stores")
        .select("*")
        .eq("id", store_id)
        .eq("merchant_id", merchant["id"])
        .maybe_single()
        .execute()
    )

    if not result.data:
        raise AuthError(
            code=ErrorCode.STORE_NOT_FOUND,
            message="Store not found or access denied",
            status_code=404,
        )

    return result.data
