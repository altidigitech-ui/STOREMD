"""Healthcheck endpoint — DB + Redis connectivity."""

import structlog
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import settings
from app.dependencies import get_redis, get_supabase_service

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
async def healthcheck() -> JSONResponse:
    """Verify that the backend, DB, and Redis are operational."""
    health: dict = {"status": "healthy", "version": settings.APP_VERSION}

    # DB check
    try:
        supabase = get_supabase_service()
        supabase.table("merchants").select("id").limit(1).execute()
        health["db"] = "connected"
    except Exception as exc:
        health["db"] = f"error: {str(exc)[:100]}"
        health["status"] = "unhealthy"

    # Redis check
    try:
        redis = get_redis()
        await redis.ping()
        health["redis"] = "connected"
    except Exception as exc:
        health["redis"] = f"error: {str(exc)[:100]}"
        health["status"] = "unhealthy"

    status_code = 200 if health["status"] == "healthy" else 503
    return JSONResponse(content=health, status_code=status_code)
