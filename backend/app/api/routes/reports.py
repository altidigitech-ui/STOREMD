"""Reports API route — latest weekly digest."""

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

router = APIRouter(prefix="/api/v1/stores/{store_id}", tags=["reports"])

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


@router.get("/reports/latest")
async def get_latest_report(
    store_id: str,
    merchant: dict = Depends(get_current_merchant),
    store: dict = Depends(get_current_store),
) -> dict:
    """Return the most recent weekly_report notification for the store.

    The body of the report is reconstructed from the latest scan data
    on the fly — same logic as `report_generator.generate_weekly_report`
    but read-only.
    """
    _require_plan(merchant, "starter", "weekly_report")
    supabase = get_supabase_service()

    try:
        notif = (
            supabase.table("notifications")
            .select("title, body, action_url, sent_at")
            .eq("merchant_id", merchant["id"])
            .eq("store_id", store_id)
            .eq("category", "weekly_report")
            .order("sent_at", desc=True)
            .limit(1)
            .maybe_single()
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "reports_query_failed",
            store_id=store_id,
            error=str(exc),
        )
        notif = type("R", (), {"data": None})()

    notif_row = notif.data if notif and notif.data else None

    # Pull the most recent completed scan for the score & deltas.
    try:
        scans = (
            supabase.table("scans")
            .select(
                "id, score, issues_count, completed_at"
            )
            .eq("store_id", store_id)
            .eq("merchant_id", merchant["id"])
            .eq("status", "completed")
            .order("completed_at", desc=True)
            .limit(2)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "reports_scans_failed",
            store_id=store_id,
            error=str(exc),
        )
        scans = type("R", (), {"data": []})()

    rows = scans.data or []
    if not rows:
        return {
            "period": "",
            "score": 0,
            "score_delta": 0,
            "trend": "stable",
            "issues_resolved": 0,
            "new_issues": 0,
            "top_action": (
                "Your first weekly report will be generated Sunday 09:00 UTC."
            ),
            "report_pdf_url": None,
            "generated_at": notif_row.get("sent_at") if notif_row else None,
        }

    latest = rows[0]
    previous = rows[1] if len(rows) > 1 else None
    score = latest.get("score") or 0
    delta = (
        score - (previous.get("score") or 0) if previous else 0
    )
    trend = "up" if delta > 0 else ("down" if delta < 0 else "stable")
    new_issues = max(
        0,
        latest.get("issues_count", 0) - (previous or {}).get("issues_count", 0),
    )
    resolved = max(
        0,
        (previous or {}).get("issues_count", 0) - latest.get("issues_count", 0),
    )

    # Top action — most-impactful unresolved issue from the latest scan.
    top_action = (
        notif_row["body"]
        if notif_row and notif_row.get("body")
        else "Your store is in good shape. Keep monitoring."
    )
    try:
        issues = (
            supabase.table("scan_issues")
            .select("title, fix_description, impact_value")
            .eq("scan_id", latest["id"])
            .eq("dismissed", False)
            .order("impact_value", desc=True)
            .limit(1)
            .execute()
        )
        if issues.data:
            issue = issues.data[0]
            top_action = (
                issue.get("fix_description") or issue.get("title") or top_action
            )
    except Exception:  # noqa: BLE001
        pass

    completed_at = latest.get("completed_at") or ""
    period = f"week ending {completed_at[:10]}" if completed_at else ""

    return {
        "period": period,
        "score": score,
        "score_delta": delta,
        "trend": trend,
        "issues_resolved": resolved,
        "new_issues": new_issues,
        "top_action": top_action,
        "report_pdf_url": None,
        "generated_at": (
            notif_row.get("sent_at") if notif_row else completed_at
        ),
    }
