"""Debug routes — dev/staging only.

These endpoints expose service connectivity status and a test-scan
trigger to make local development and staging smoke testing easier.
The router is *only* mounted in main.py when APP_ENV != "production".

As a defense-in-depth measure each handler also checks at request
time and returns 404 if production is somehow set after the import.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.dependencies import (
    get_current_merchant,
    get_redis,
    get_supabase_service,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/debug", tags=["debug"])


def _guard_production() -> None:
    if settings.is_production:
        # 404 — never reveal the existence of debug endpoints in prod.
        raise HTTPException(status_code=404)


# ---------------------------------------------------------------------------
# GET /debug/config — service health, NO secrets
# ---------------------------------------------------------------------------


@router.get("/config")
async def debug_config() -> dict:
    """Return the connectivity status of every external dependency.

    Never returns secrets — only booleans / connection state.
    """
    _guard_production()

    out: dict = {
        "env": settings.APP_ENV,
        "version": settings.APP_VERSION,
        "services": {},
    }

    # DB
    try:
        supabase = get_supabase_service()
        supabase.table("merchants").select("id").limit(1).execute()
        out["services"]["db"] = {"status": "connected"}
    except Exception as exc:  # noqa: BLE001
        out["services"]["db"] = {
            "status": "error",
            "error": str(exc)[:120],
        }

    # Redis
    try:
        redis = get_redis()
        await redis.ping()
        out["services"]["redis"] = {"status": "connected"}
    except Exception as exc:  # noqa: BLE001
        out["services"]["redis"] = {
            "status": "error",
            "error": str(exc)[:120],
        }

    # Mem0
    try:
        from app.agent.memory import get_store_memory

        memory = get_store_memory()
        out["services"]["mem0"] = {
            "status": "available" if memory.is_available else "unavailable",
            "mode": "hosted" if settings.MEM0_API_KEY else "self_hosted",
        }
    except Exception as exc:  # noqa: BLE001
        out["services"]["mem0"] = {
            "status": "error",
            "error": str(exc)[:120],
        }

    # Celery — just check the broker URL is set; pinging the worker
    # would be heavy and is not the point of this endpoint.
    out["services"]["celery"] = {
        "broker": "configured" if settings.REDIS_URL else "missing",
    }

    # Anthropic / Claude — presence of API key only.
    out["services"]["anthropic"] = {
        "configured": bool(settings.ANTHROPIC_API_KEY),
    }

    # Stripe / Resend / Sentry — presence only.
    out["services"]["stripe"] = {"configured": bool(settings.STRIPE_SECRET_KEY)}
    out["services"]["resend"] = {"configured": bool(settings.RESEND_API_KEY)}
    out["services"]["sentry"] = {"configured": bool(settings.SENTRY_DSN)}

    # Push / VAPID
    out["services"]["push"] = {
        "configured": bool(settings.VAPID_PRIVATE_KEY),
    }

    return out


# ---------------------------------------------------------------------------
# POST /debug/test-scan — trigger a test scan
# ---------------------------------------------------------------------------


@router.post("/test-scan")
async def debug_test_scan(
    store_id: str,
    merchant: dict = Depends(get_current_merchant),
) -> dict:
    """Dispatch a Celery test scan for the given store.

    Returns the scan_id immediately. Useful for local end-to-end
    verification without going through the dashboard.
    """
    _guard_production()
    supabase = get_supabase_service()

    # Verify ownership.
    store_row = (
        supabase.table("stores")
        .select("id, status")
        .eq("id", store_id)
        .eq("merchant_id", merchant["id"])
        .maybe_single()
        .execute()
    )
    if not store_row or not store_row.data:
        raise HTTPException(status_code=404, detail="Store not found")

    scan = (
        supabase.table("scans")
        .insert(
            {
                "store_id": store_id,
                "merchant_id": merchant["id"],
                "status": "pending",
                "trigger": "manual",
                "modules": ["health"],
            }
        )
        .execute()
    )
    scan_id = scan.data[0]["id"]

    try:
        from tasks.scan_tasks import run_scan

        run_scan.delay(scan_id, store_id, merchant["id"], ["health"], "manual")
    except Exception as exc:  # noqa: BLE001
        logger.warning("debug_test_scan_dispatch_failed", error=str(exc))
        return {"scan_id": scan_id, "dispatched": False, "error": str(exc)}

    return {"scan_id": scan_id, "dispatched": True}
