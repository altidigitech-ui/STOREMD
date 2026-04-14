"""Public tracking endpoints for the marketing landing page.

Built-in UTM tracking system. No GA4, no Plausible. Everything is stored
in Supabase via these endpoints. Endpoints are PUBLIC (no JWT) because
they fire before the visitor is authenticated. Rate limited per IP via
Redis to keep noise out.
"""

from __future__ import annotations

import hashlib

import structlog
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.core.exceptions import AppError, ErrorCode
from app.dependencies import get_redis, get_supabase_service

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/tracking", tags=["tracking"])

RATE_LIMIT_PER_MINUTE = 60


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _hash_ip(ip: str) -> str:
    """Hash + truncate to 16 chars — GDPR safe pseudonym, not a raw IP."""
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()[:16]


async def _enforce_rate_limit(request: Request, redis) -> None:
    ip = _client_ip(request)
    key = f"track_rl:{ip}"
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 60)
        if count > RATE_LIMIT_PER_MINUTE:
            raise AppError(
                code=ErrorCode.RATE_LIMIT_EXCEEDED,
                message="Tracking rate limit exceeded",
                status_code=429,
                context={"ip_hash": _hash_ip(ip)},
            )
    except AppError:
        raise
    except Exception as exc:  # noqa: BLE001 — never block on Redis failure
        logger.warning("tracking_rate_limit_redis_error", error=str(exc))


class PageViewIn(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    path: str = Field(..., min_length=1, max_length=2048)
    referrer: str | None = Field(default=None, max_length=2048)
    utm_source: str | None = Field(default=None, max_length=128)
    utm_medium: str | None = Field(default=None, max_length=128)
    utm_campaign: str | None = Field(default=None, max_length=128)
    utm_content: str | None = Field(default=None, max_length=128)
    utm_term: str | None = Field(default=None, max_length=128)
    device: str | None = Field(default=None, max_length=32)
    browser: str | None = Field(default=None, max_length=64)
    os: str | None = Field(default=None, max_length=64)
    screen_width: int | None = Field(default=None, ge=0, le=20000)


class TrackingEventIn(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    event_name: str = Field(..., min_length=1, max_length=64)
    event_data: dict = Field(default_factory=dict)
    utm_source: str | None = Field(default=None, max_length=128)
    utm_medium: str | None = Field(default=None, max_length=128)
    utm_campaign: str | None = Field(default=None, max_length=128)


@router.post("/pageview", status_code=204)
async def track_pageview(
    payload: PageViewIn,
    request: Request,
    redis=Depends(get_redis),
    supabase=Depends(get_supabase_service),
):
    await _enforce_rate_limit(request, redis)

    ip = _client_ip(request)
    row = payload.model_dump()
    row["ip_hash"] = _hash_ip(ip)

    try:
        supabase.table("page_views").insert(row).execute()
    except Exception as exc:  # noqa: BLE001 — fire-and-forget, never break the landing
        logger.warning(
            "pageview_insert_failed",
            error=str(exc),
            path=payload.path,
        )
    return None


@router.post("/event", status_code=204)
async def track_event(
    payload: TrackingEventIn,
    request: Request,
    redis=Depends(get_redis),
    supabase=Depends(get_supabase_service),
):
    await _enforce_rate_limit(request, redis)

    try:
        supabase.table("tracking_events").insert(payload.model_dump()).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "tracking_event_insert_failed",
            error=str(exc),
            event_name=payload.event_name,
        )
    return None
