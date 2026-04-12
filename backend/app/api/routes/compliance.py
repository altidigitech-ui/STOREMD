"""Compliance API routes — accessibility scan + broken links."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Query

from app.core.exceptions import AuthError, ErrorCode
from app.dependencies import (
    get_current_merchant,
    get_current_store,
    get_supabase_service,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/stores/{store_id}", tags=["compliance"])

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


def _latest_compliance_scan(supabase, store_id: str, merchant_id: str) -> dict:
    """Fetch the most recent scanner_results blob for the compliance module."""
    try:
        scans = (
            supabase.table("scans")
            .select("id, scanner_results")
            .eq("store_id", store_id)
            .eq("merchant_id", merchant_id)
            .eq("status", "completed")
            .contains("modules", ["compliance"])
            .order("completed_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("compliance_query_failed", error=str(exc))
        return {}

    rows = scans.data or []
    return rows[0] if rows else {}


# ---------------------------------------------------------------------------
# GET /accessibility
# ---------------------------------------------------------------------------


@router.get("/accessibility")
async def get_accessibility(
    store_id: str,
    live: bool = Query(default=False),
    merchant: dict = Depends(get_current_merchant),
    store: dict = Depends(get_current_store),
) -> dict:
    """WCAG 2.1 scan results.

    `?live=true` requires Pro and would include the Playwright-based
    findings (delivered by the browser scanner group, Phase 6).
    """
    _require_plan(merchant, "starter", "accessibility_scan")
    if live:
        _require_plan(merchant, "pro", "accessibility_live")

    supabase = get_supabase_service()
    scan = _latest_compliance_scan(supabase, store_id, merchant["id"])
    if not scan:
        return {
            "score": 0,
            "eaa_compliant": False,
            "violations_count": 0,
            "violations": [],
            "live_test_included": False,
            "live_test_available": True,
        }

    metrics = (
        (scan.get("scanner_results") or {})
        .get("accessibility", {})
        .get("metrics", {})
    )

    # Pull issues for nicer breakdown.
    try:
        issues = (
            supabase.table("scan_issues")
            .select("title, fix_description, severity, context, auto_fixable")
            .eq("scan_id", scan["id"])
            .eq("scanner", "accessibility")
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("compliance_issues_failed", error=str(exc))
        issues = type("R", (), {"data": []})()

    violations = [
        {
            "rule": (i.get("context") or {}).get("rule", "unknown"),
            "severity": i.get("severity"),
            "count": (i.get("context") or {}).get("count", 1),
            "fix_description": i.get("fix_description"),
            "auto_fixable": i.get("auto_fixable", False),
        }
        for i in (issues.data or [])
    ]

    return {
        "score": metrics.get("score", 0),
        "eaa_compliant": metrics.get("eaa_compliant", False),
        "violations_count": len(violations),
        "violations": violations,
        "live_test_included": live,
        "live_test_available": True,
    }


# ---------------------------------------------------------------------------
# GET /links/broken
# ---------------------------------------------------------------------------


@router.get("/links/broken")
async def get_broken_links(
    store_id: str,
    merchant: dict = Depends(get_current_merchant),
    store: dict = Depends(get_current_store),
) -> dict:
    """Most recent broken-links scan results."""
    _require_plan(merchant, "starter", "broken_links")
    supabase = get_supabase_service()

    scan = _latest_compliance_scan(supabase, store_id, merchant["id"])
    if not scan:
        return {"broken_count": 0, "pages_crawled": 0, "data": []}

    metrics = (
        (scan.get("scanner_results") or {})
        .get("broken_links", {})
        .get("metrics", {})
    )

    try:
        issues = (
            supabase.table("scan_issues")
            .select("title, context, auto_fixable, fix_description")
            .eq("scan_id", scan["id"])
            .eq("scanner", "broken_links")
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("broken_links_issues_failed", error=str(exc))
        issues = type("R", (), {"data": []})()

    data = [
        {
            "url": (i.get("context") or {}).get("url"),
            "source_page": (i.get("context") or {}).get("source_page"),
            "status_code": (i.get("context") or {}).get("status_code"),
            "type": (i.get("context") or {}).get("type", "internal"),
            "auto_fixable": i.get("auto_fixable", False),
            "fix_description": i.get("fix_description"),
        }
        for i in (issues.data or [])
    ]

    return {
        "broken_count": metrics.get("broken_count", len(data)),
        "pages_crawled": metrics.get("pages_crawled", 0),
        "data": data,
    }
