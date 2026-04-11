"""Redis-based rate limiter per plan tier."""

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.exceptions import ErrorCode
from app.dependencies import get_redis

logger = structlog.get_logger()

# Rate limits per plan (requests per minute)
PLAN_LIMITS: dict[str, int] = {
    "free": 30,
    "starter": 60,
    "pro": 120,
    "agency": 300,
}

DEFAULT_LIMIT = 30  # fallback for unknown plans


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter using Redis.

    Uses the merchant_id from request.state (set by JWTAuthMiddleware).
    Public endpoints are not rate-limited.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Only rate-limit authenticated requests
        merchant_id = getattr(request.state, "merchant_id", None)
        if not merchant_id:
            return await call_next(request)

        try:
            redis = get_redis()
            key = f"rate_limit:{merchant_id}"

            current = await redis.incr(key)
            if current == 1:
                await redis.expire(key, 60)

            # Get plan from request state (set by auth) or use default
            plan = getattr(request.state, "plan", "free")
            limit = PLAN_LIMITS.get(plan, DEFAULT_LIMIT)

            if current > limit:
                ttl = await redis.ttl(key)
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": ErrorCode.RATE_LIMIT_EXCEEDED.value,
                            "message": "Rate limit exceeded",
                        }
                    },
                    headers={"Retry-After": str(max(ttl, 1))},
                )
        except Exception:
            # If Redis is down, don't block the request
            logger.warning("rate_limit_redis_error", merchant_id=merchant_id)

        return await call_next(request)
