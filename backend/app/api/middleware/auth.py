"""JWT validation middleware for Supabase Auth."""

import jwt
import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings
from app.core.exceptions import ErrorCode

logger = structlog.get_logger()

# Paths that don't require authentication
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


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Validate JWT on protected routes.

    Public paths (health, auth, webhooks) are excluded.
    The decoded merchant_id is stored in request.state.merchant_id.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path

        # Skip auth for public paths
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

        try:
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
            request.state.merchant_id = payload.get("sub")
        except jwt.ExpiredSignatureError:
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": ErrorCode.JWT_EXPIRED.value,
                        "message": "Token expired",
                    }
                },
            )
        except jwt.InvalidTokenError:
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": ErrorCode.JWT_INVALID.value,
                        "message": "Invalid token",
                    }
                },
            )

        return await call_next(request)
