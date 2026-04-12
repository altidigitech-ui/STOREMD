"""Agentic Readiness API routes — score, fixes, HS codes."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.core.exceptions import AuthError, ErrorCode
from app.dependencies import (
    get_current_merchant,
    get_current_store,
    get_supabase_service,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/stores/{store_id}", tags=["agentic"])

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
# GET /agentic/score
# ---------------------------------------------------------------------------


@router.get("/agentic/score")
async def get_agentic_score(
    store_id: str,
    merchant: dict = Depends(get_current_merchant),
    store: dict = Depends(get_current_store),
) -> dict:
    """Latest agentic readiness score + 6 checks."""
    _require_plan(merchant, "starter", "agentic_score")
    supabase = get_supabase_service()

    # Pull the most recent scan that ran the agentic module.
    try:
        scans = (
            supabase.table("scans")
            .select("id, scanner_results")
            .eq("store_id", store_id)
            .eq("merchant_id", merchant["id"])
            .eq("status", "completed")
            .contains("modules", ["agentic"])
            .order("completed_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("agentic_score_query_failed", error=str(exc))
        scans = type("R", (), {"data": []})()

    rows = scans.data or []
    if not rows:
        return {
            "score": 0,
            "products_scanned": 0,
            "checks": [],
        }

    scanner_results = (rows[0].get("scanner_results") or {}).get(
        "agentic_readiness", {}
    )
    metrics = scanner_results.get("metrics", {}) or scanner_results

    raw_checks = metrics.get("checks", {}) or {}
    checks = []
    fix_descriptions = {
        "gtin_present": "Add GTIN/barcode to product variants",
        "metafields_filled": "Fill material, dimensions, weight metafields",
        "structured_description": "Restructure descriptions for AI agents",
        "schema_markup": "Add JSON-LD Product schema to the theme",
        "google_category": "Assign Google product categories",
        "shopify_catalog": "Publish products to the Shopify Catalog channel",
    }
    for name, data in raw_checks.items():
        checks.append(
            {
                "name": name,
                "status": data.get("status", "fail"),
                "affected_products": data.get("affected_products", 0),
                "pass_rate": round((data.get("pass_rate") or 0) * 100, 1),
                "fix_description": fix_descriptions.get(name, ""),
            }
        )

    return {
        "score": metrics.get("score", 0),
        "products_scanned": metrics.get("products_scanned", 0),
        "checks": checks,
    }


# ---------------------------------------------------------------------------
# POST /agentic/fixes
# ---------------------------------------------------------------------------


class AgenticFixesRequest(BaseModel):
    checks: list[str] = Field(min_length=1, max_length=10)
    product_ids: list[str] = Field(default_factory=list, max_length=100)
    auto_apply: bool = False


@router.post("/agentic/fixes")
async def generate_agentic_fixes(
    store_id: str,
    request: AgenticFixesRequest,
    merchant: dict = Depends(get_current_merchant),
    store: dict = Depends(get_current_store),
) -> dict:
    """Generate one-click fix previews for the requested agentic checks."""
    _require_plan(merchant, "starter", "agentic_fix")
    supabase = get_supabase_service()

    fixes: list[dict] = []
    for product_id in request.product_ids[:50]:
        for check in request.checks:
            if check == "metafields_filled":
                # Real Claude API call would happen in a service —
                # here we record the fix request so the apply route
                # can pick it up later.
                try:
                    record = (
                        supabase.table("fixes")
                        .insert(
                            {
                                "merchant_id": merchant["id"],
                                "store_id": store_id,
                                "fix_type": "metafield",
                                "target_id": product_id,
                                "status": "pending_approval",
                                "before_state": {},
                                "after_state": {
                                    "metafield": {
                                        "namespace": "custom",
                                        "key": "material",
                                    }
                                },
                            }
                        )
                        .execute()
                    )
                    fixes.append(
                        {
                            "fix_id": record.data[0]["id"],
                            "product_id": product_id,
                            "check": check,
                            "field": "material",
                            "suggested_value": "TBD (rendered at apply time)",
                            "status": "pending_approval",
                            "auto_fixable": True,
                        }
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "agentic_fix_persist_failed",
                        product_id=product_id,
                        error=str(exc),
                    )

    return {"fixes": fixes}


# ---------------------------------------------------------------------------
# GET /products/hs-codes
# ---------------------------------------------------------------------------


@router.get("/products/hs-codes")
async def get_hs_codes(
    store_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    merchant: dict = Depends(get_current_merchant),
    store: dict = Depends(get_current_store),
) -> dict:
    """Latest HS code validation results."""
    _require_plan(merchant, "pro", "hs_code")
    supabase = get_supabase_service()

    try:
        scans = (
            supabase.table("scans")
            .select("id, scanner_results")
            .eq("store_id", store_id)
            .eq("merchant_id", merchant["id"])
            .eq("status", "completed")
            .contains("modules", ["agentic"])
            .order("completed_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("hs_codes_query_failed", error=str(exc))
        scans = type("R", (), {"data": []})()

    rows = scans.data or []
    if not rows:
        return {
            "total_products": 0,
            "missing_count": 0,
            "suspicious_count": 0,
            "valid_count": 0,
            "data": [],
            "pagination": {"has_next": False, "next_cursor": None},
        }

    metrics = (
        (rows[0].get("scanner_results") or {})
        .get("hs_code_validator", {})
        .get("metrics", {})
    )

    return {
        "total_products": metrics.get("total_products", 0),
        "missing_count": metrics.get("missing_hs", 0),
        "suspicious_count": metrics.get("suspicious_hs", 0),
        "valid_count": metrics.get("valid_hs", 0),
        # Per-product breakdown is in scan_issues rather than scanner_results;
        # for now we surface the aggregates and let the dashboard link to the
        # scan detail view for individual products.
        "data": [],
        "pagination": {"has_next": False, "next_cursor": None},
    }
