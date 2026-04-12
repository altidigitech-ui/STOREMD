"""Fix routes — apply and revert one-click fixes."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends

from app.core.exceptions import ErrorCode, FixError
from app.dependencies import get_current_merchant, get_current_store, get_supabase_service

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/stores/{store_id}/fixes", tags=["fixes"])


@router.post("/{fix_id}/apply")
async def apply_fix(
    store_id: str,
    fix_id: str,
    merchant: dict = Depends(get_current_merchant),
    store: dict = Depends(get_current_store),
) -> dict:
    """Apply a one-click fix."""
    supabase = get_supabase_service()

    # Fetch the fix
    fix_result = (
        supabase.table("fixes")
        .select("*")
        .eq("id", fix_id)
        .eq("store_id", store_id)
        .eq("merchant_id", merchant["id"])
        .maybe_single()
        .execute()
    )

    if not fix_result.data:
        raise FixError(
            code=ErrorCode.FIX_NOT_FOUND,
            message="Fix not found",
            status_code=404,
        )

    fix = fix_result.data

    if fix["status"] == "applied":
        raise FixError(
            code=ErrorCode.FIX_ALREADY_APPLIED,
            message="Fix already applied",
            status_code=409,
        )

    if fix["status"] not in ("pending", "approved"):
        raise FixError(
            code=ErrorCode.FIX_APPROVAL_REQUIRED,
            message="Fix must be pending or approved before applying",
            status_code=403,
        )

    # Apply the fix (placeholder — actual Shopify API write in a future phase)
    now = datetime.now(UTC).isoformat()

    supabase.table("fixes").update({
        "status": "applied",
        "applied_at": now,
    }).eq("id", fix_id).execute()

    logger.info("fix_applied", fix_id=fix_id, store_id=store_id, fix_type=fix["fix_type"])

    return {
        "fix_id": fix_id,
        "status": "applied",
        "fix_type": fix["fix_type"],
        "before_state": fix.get("before_state"),
        "after_state": fix.get("after_state"),
        "revertable": fix.get("before_state") is not None,
        "applied_at": now,
    }


@router.post("/{fix_id}/revert")
async def revert_fix(
    store_id: str,
    fix_id: str,
    merchant: dict = Depends(get_current_merchant),
    store: dict = Depends(get_current_store),
) -> dict:
    """Revert a previously applied fix."""
    supabase = get_supabase_service()

    fix_result = (
        supabase.table("fixes")
        .select("*")
        .eq("id", fix_id)
        .eq("store_id", store_id)
        .eq("merchant_id", merchant["id"])
        .maybe_single()
        .execute()
    )

    if not fix_result.data:
        raise FixError(
            code=ErrorCode.FIX_NOT_FOUND,
            message="Fix not found",
            status_code=404,
        )

    fix = fix_result.data

    if fix["status"] != "applied":
        raise FixError(
            code=ErrorCode.FIX_NOT_REVERTABLE,
            message="Only applied fixes can be reverted",
            status_code=400,
        )

    if not fix.get("before_state"):
        raise FixError(
            code=ErrorCode.FIX_NOT_REVERTABLE,
            message="This fix has no before_state and cannot be reverted",
            status_code=400,
        )

    # Revert (placeholder — actual Shopify API write in a future phase)
    now = datetime.now(UTC).isoformat()

    supabase.table("fixes").update({
        "status": "reverted",
        "reverted_at": now,
    }).eq("id", fix_id).execute()

    logger.info("fix_reverted", fix_id=fix_id, store_id=store_id)

    return {
        "fix_id": fix_id,
        "status": "reverted",
        "reverted_at": now,
    }
