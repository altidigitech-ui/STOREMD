"""Fix routes — apply and revert one-click fixes via Shopify Admin API."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends

from app.core.exceptions import ErrorCode, FixError, ShopifyError
from app.dependencies import (
    get_current_merchant,
    get_current_store,
    get_supabase_service,
)
from app.services.shopify import ShopifyClient

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/stores/{store_id}/fixes", tags=["fixes"])


def _shopify_client(store: dict, merchant: dict) -> ShopifyClient:
    encrypted = merchant.get("shopify_access_token_encrypted")
    if not encrypted:
        raise FixError(
            code=ErrorCode.SHOPIFY_TOKEN_EXPIRED,
            message="Shopify token missing — reinstall the app",
            status_code=502,
        )
    return ShopifyClient(store["shopify_shop_domain"], encrypted)


async def _dispatch_fix(
    *,
    fix: dict,
    fixer,
) -> tuple[dict, dict]:
    """Route a fix row to the right OneClickFixer method based on fix_type."""
    fix_type = fix.get("fix_type")
    after_state = fix.get("after_state") or {}
    target_id = fix.get("target_id") or ""

    if fix_type == "alt_text":
        image = (after_state.get("image") or {}) if isinstance(after_state, dict) else {}
        return await fixer.apply_alt_text(
            product_id=image.get("product_id") or target_id,
            image_id=image.get("image_id"),
            alt_text=after_state.get("alt_text") or image.get("alt_text", ""),
        )

    if fix_type == "metafield":
        meta = after_state.get("metafield") or {}
        return await fixer.apply_metafield(
            owner_id=target_id,
            namespace=meta.get("namespace", "custom"),
            key=meta.get("key", ""),
            value=meta.get("value") or "",
            type_=meta.get("type", "single_line_text_field"),
        )

    if fix_type == "redirect":
        redirect = after_state.get("redirect") or {}
        return await fixer.apply_redirect(
            from_path=redirect.get("path") or redirect.get("from", ""),
            to_path=redirect.get("target") or redirect.get("to", ""),
        )

    if fix_type in ("residue_script", "remove_script"):
        return await fixer.remove_residue_script(
            script_tag_id=target_id or after_state.get("script_tag_id", "")
        )

    if fix_type in ("description", "rewrite_description"):
        return await fixer.rewrite_description(
            product_id=target_id,
            new_description_html=after_state.get("description_html", ""),
        )

    raise FixError(
        code=ErrorCode.FIX_APPLY_FAILED,
        message=f"Unsupported fix_type: {fix_type}",
        status_code=400,
        context={"fix_type": fix_type},
    )


@router.post("/{fix_id}/apply")
async def apply_fix(
    store_id: str,
    fix_id: str,
    merchant: dict = Depends(get_current_merchant),
    store: dict = Depends(get_current_store),
) -> dict:
    """Apply a one-click fix via the Shopify Admin API."""
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

    if fix["status"] == "applied":
        raise FixError(
            code=ErrorCode.FIX_ALREADY_APPLIED,
            message="Fix already applied",
            status_code=409,
        )

    if fix["status"] not in ("pending", "approved", "pending_approval"):
        raise FixError(
            code=ErrorCode.FIX_APPROVAL_REQUIRED,
            message="Fix must be pending or approved before applying",
            status_code=403,
        )

    # Call Shopify Admin API through the OneClickFixer.
    from app.agent.actors.one_click_fixer import OneClickFixer

    shopify = _shopify_client(store, merchant)
    fixer = OneClickFixer(shopify)

    try:
        before_state, after_state = await _dispatch_fix(fix=fix, fixer=fixer)
    except ShopifyError as exc:
        logger.warning(
            "fix_apply_shopify_error",
            fix_id=fix_id,
            fix_type=fix.get("fix_type"),
            error=exc.message,
        )
        raise FixError(
            code=ErrorCode.FIX_APPLY_FAILED,
            message=f"Shopify refused the fix: {exc.message}",
            status_code=502,
        ) from exc

    now = datetime.now(UTC).isoformat()
    supabase.table("fixes").update(
        {
            "status": "applied",
            "before_state": before_state,
            "after_state": after_state,
            "applied_at": now,
        }
    ).eq("id", fix_id).execute()

    logger.info(
        "fix_applied_shopify",
        fix_id=fix_id,
        store_id=store_id,
        fix_type=fix["fix_type"],
        target_id=fix.get("target_id"),
    )

    return {
        "fix_id": fix_id,
        "status": "applied",
        "fix_type": fix["fix_type"],
        "before_state": before_state,
        "after_state": after_state,
        "revertable": bool(before_state),
        "applied_at": now,
    }


@router.post("/{fix_id}/revert")
async def revert_fix(
    store_id: str,
    fix_id: str,
    merchant: dict = Depends(get_current_merchant),
    store: dict = Depends(get_current_store),
) -> dict:
    """Revert a previously applied fix — restore the before_state."""
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

    from app.agent.actors.one_click_fixer import OneClickFixer

    shopify = _shopify_client(store, merchant)
    fixer = OneClickFixer(shopify)

    try:
        if fix["fix_type"] == "redirect":
            # Revert redirect = DELETE the created redirect (Shopify doesn't
            # support "undo create" via another create with empty paths).
            # The redirect GID is stored in after_state.redirect.id.
            after_state_data = fix.get("after_state") or {}
            redirect_id = (after_state_data.get("redirect") or {}).get("id")
            if redirect_id:
                await fixer.delete_redirect(redirect_id)
            # If redirect_id is None the redirect was never created — nothing to do.
        else:
            reverse_fix: dict[str, Any] = {
                "fix_type": fix["fix_type"],
                "target_id": fix.get("target_id"),
                "after_state": fix.get("before_state"),
            }
            await _dispatch_fix(fix=reverse_fix, fixer=fixer)
    except ShopifyError as exc:
        logger.warning(
            "fix_revert_shopify_error",
            fix_id=fix_id,
            fix_type=fix.get("fix_type"),
            error=exc.message,
        )
        raise FixError(
            code=ErrorCode.FIX_REVERT_FAILED,
            message=f"Shopify refused the revert: {exc.message}",
            status_code=502,
        ) from exc

    now = datetime.now(UTC).isoformat()
    supabase.table("fixes").update(
        {"status": "reverted", "reverted_at": now}
    ).eq("id", fix_id).execute()

    logger.info(
        "fix_reverted",
        fix_id=fix_id,
        store_id=store_id,
        fix_type=fix.get("fix_type"),
    )

    return {
        "fix_id": fix_id,
        "status": "reverted",
        "reverted_at": now,
    }
