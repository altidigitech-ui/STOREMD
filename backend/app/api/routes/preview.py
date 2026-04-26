"""Preview scan — public endpoint, no auth required."""

from __future__ import annotations

import re
from dataclasses import asdict

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from app.core.exceptions import ErrorCode
from app.dependencies import get_redis

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/preview", tags=["preview"])

_SHOP_DOMAIN_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9.\-]*\.[a-zA-Z]{2,}$")
_RATE_LIMIT_PER_HOUR = 5
_RATE_LIMIT_WINDOW_S = 3600


class PreviewScanRequest(BaseModel):
    shop_domain: str

    @field_validator("shop_domain")
    @classmethod
    def validate_shop_domain(cls, v: str) -> str:
        v = v.strip().lower()
        # Strip protocol if accidentally included
        v = re.sub(r"^https?://", "", v)
        # Strip trailing slash and path
        v = v.split("/")[0]
        if not _SHOP_DOMAIN_RE.match(v):
            raise ValueError("Invalid store domain — use yourstore.myshopify.com or yourstore.com")
        return v


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/scan")
async def preview_scan(
    request: Request,
    body: PreviewScanRequest,
    redis=Depends(get_redis),
):
    """Run a public preview scan on a Shopify storefront. No auth required."""
    ip = _client_ip(request)
    rl_key = f"preview_rl:{ip}"

    try:
        count = await redis.incr(rl_key)
        if count == 1:
            await redis.expire(rl_key, _RATE_LIMIT_WINDOW_S)
        if count > _RATE_LIMIT_PER_HOUR:
            ttl = await redis.ttl(rl_key)
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": ErrorCode.RATE_LIMIT_EXCEEDED.value,
                        "message": "Preview scan limit reached. Try again in an hour.",
                    }
                },
                headers={"Retry-After": str(max(ttl, 0))},
            )
    except Exception as exc:
        logger.warning("preview_rate_limit_redis_error", error=str(exc))

    from app.agent.preview.runner import run_preview_scan

    result = await run_preview_scan(body.shop_domain)
    return asdict(result)
