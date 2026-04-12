"""Browser API routes — Visual Store Test, Real User Simulation.

Surface the latest results from the `screenshots` and `user_simulations`
tables to the frontend dashboard. Pro+ only.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends

from app.core.exceptions import AuthError, ErrorCode
from app.dependencies import (
    get_current_merchant,
    get_current_store,
    get_supabase_service,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/stores/{store_id}", tags=["browser"])

PLAN_HIERARCHY = {"free": 0, "starter": 1, "pro": 2, "agency": 3}


def _require_plan(merchant: dict, required: str, feature: str) -> None:
    plan = merchant.get("plan", "free")
    if PLAN_HIERARCHY.get(plan, 0) < PLAN_HIERARCHY.get(required, 0):
        raise AuthError(
            code=ErrorCode.PLAN_REQUIRED,
            message=f"Feature '{feature}' requires {required} plan or above",
            status_code=403,
            context={"feature": feature, "required_plan": required},
        )


# ---------------------------------------------------------------------------
# GET /visual/diff — latest visual store test screenshots + diff
# ---------------------------------------------------------------------------


@router.get("/visual/diff")
async def get_visual_diff(
    store_id: str,
    merchant: dict = Depends(get_current_merchant),
    store: dict = Depends(get_current_store),
) -> dict:
    """Return the most recent mobile + desktop screenshots and diff data."""
    _require_plan(merchant, "pro", "visual_store_test")
    supabase = get_supabase_service()

    screenshots: dict[str, dict] = {}
    diff_regions: list[dict] = []
    scan_id: str | None = None
    scanned_at: str | None = None

    for device in ("mobile", "desktop"):
        try:
            result = (
                supabase.table("screenshots")
                .select("*")
                .eq("store_id", store_id)
                .eq("device", device)
                .order("created_at", desc=True)
                .limit(2)
                .execute()
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "visual_diff_query_failed",
                store_id=store_id,
                device=device,
                error=str(exc),
            )
            continue

        rows = result.data or []
        if not rows:
            screenshots[device] = {
                "current_url": None,
                "previous_url": None,
                "diff_pct": None,
                "significant_change": False,
            }
            continue

        current = rows[0]
        previous = rows[1] if len(rows) > 1 else None
        screenshots[device] = {
            "current_url": _public_url(supabase, current.get("storage_path")),
            "previous_url": _public_url(
                supabase, previous.get("storage_path") if previous else None
            ),
            "diff_pct": current.get("diff_pct"),
            "significant_change": bool(current.get("significant_change")),
        }
        diff_regions.extend(current.get("diff_regions") or [])
        scanned_at = scanned_at or current.get("created_at")

    # The scan_id link comes from the most recent scan that ran the
    # browser module (best-effort).
    try:
        scan_row = (
            supabase.table("scans")
            .select("id, completed_at")
            .eq("store_id", store_id)
            .eq("merchant_id", merchant["id"])
            .eq("status", "completed")
            .contains("modules", ["browser"])
            .order("completed_at", desc=True)
            .limit(1)
            .execute()
        )
        if scan_row.data:
            scan_id = scan_row.data[0]["id"]
            scanned_at = scan_row.data[0].get("completed_at") or scanned_at
    except Exception:  # noqa: BLE001
        pass

    return {
        "screenshots": screenshots,
        "diff_regions": diff_regions,
        "scan_id": scan_id,
        "scanned_at": scanned_at,
    }


# ---------------------------------------------------------------------------
# GET /simulation — latest Real User Simulation
# ---------------------------------------------------------------------------


@router.get("/simulation")
async def get_simulation(
    store_id: str,
    merchant: dict = Depends(get_current_merchant),
    store: dict = Depends(get_current_store),
) -> dict:
    """Return the most recent purchase-path simulation."""
    _require_plan(merchant, "pro", "user_simulation")
    supabase = get_supabase_service()

    try:
        result = (
            supabase.table("user_simulations")
            .select("*")
            .eq("store_id", store_id)
            .order("created_at", desc=True)
            .limit(1)
            .maybe_single()
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "simulation_query_failed",
            store_id=store_id,
            error=str(exc),
        )
        result = type("R", (), {"data": None})()

    row = result.data if result and result.data else None
    if not row:
        return {
            "total_time_ms": 0,
            "bottleneck_step": None,
            "bottleneck_cause": None,
            "steps": [],
            "scan_id": None,
            "scanned_at": None,
        }

    return {
        "total_time_ms": row.get("total_time_ms", 0),
        "bottleneck_step": row.get("bottleneck_step"),
        "bottleneck_cause": row.get("bottleneck_cause"),
        "steps": row.get("steps") or [],
        "scan_id": row.get("scan_id"),
        "scanned_at": row.get("created_at"),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _public_url(supabase, storage_path: str | None) -> str | None:
    if not storage_path:
        return None
    try:
        return supabase.storage.from_("screenshots").get_public_url(storage_path)
    except Exception:  # noqa: BLE001
        return None
