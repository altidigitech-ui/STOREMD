"""Weekly report generator.

Builds the per-store weekly digest (score, delta, resolved, new issues,
top action) and persists it as a notification row so the dashboard can
surface the banner.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.services.notification import (
    format_weekly_report_notification,
    send_notification,
)

logger = structlog.get_logger()


async def generate_weekly_report(
    store_id: str,
    merchant_id: str,
    supabase: Any | None = None,
) -> dict | None:
    """Build a weekly report dict for one store.

    Returns None if there's not enough data to compute a meaningful diff.
    """
    if supabase is None:
        from app.dependencies import get_supabase_service

        supabase = get_supabase_service()

    now = datetime.now(UTC)
    week_start = now - timedelta(days=7)
    prev_week_start = now - timedelta(days=14)

    # Fetch the most recent scan + the previous-week reference scan.
    try:
        latest = (
            supabase.table("scans")
            .select("*")
            .eq("store_id", store_id)
            .eq("status", "completed")
            .gte("completed_at", week_start.isoformat())
            .order("completed_at", desc=True)
            .limit(1)
            .execute()
        )
        previous = (
            supabase.table("scans")
            .select("*")
            .eq("store_id", store_id)
            .eq("status", "completed")
            .lt("completed_at", week_start.isoformat())
            .gte("completed_at", prev_week_start.isoformat())
            .order("completed_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "weekly_report_query_failed",
            store_id=store_id,
            error=str(exc),
        )
        return None

    latest_scan = (latest.data or [None])[0]
    previous_scan = (previous.data or [None])[0]

    if not latest_scan:
        logger.info("weekly_report_no_scan", store_id=store_id)
        return None

    score = latest_scan.get("score") or 0
    prev_score = (previous_scan or {}).get("score")
    delta = score - prev_score if prev_score is not None else 0
    trend = "up" if delta > 0 else ("down" if delta < 0 else "stable")

    # Resolved / new based on issue counts.
    resolved = max(
        0,
        (previous_scan or {}).get("issues_count", 0)
        - latest_scan.get("issues_count", 0),
    )
    new_issues = max(
        0,
        latest_scan.get("issues_count", 0)
        - (previous_scan or {}).get("issues_count", 0),
    )

    # Top action: pull the most-impactful unresolved critical issue.
    top_action = "Your store is in good shape. Keep monitoring."
    try:
        issues = (
            supabase.table("scan_issues")
            .select("title, severity, fix_description, impact_value")
            .eq("scan_id", latest_scan["id"])
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

    report = {
        "period": (
            f"{week_start.date().isoformat()} to {now.date().isoformat()}"
        ),
        "score": score,
        "score_delta": delta,
        "trend": trend,
        "issues_resolved": resolved,
        "new_issues": new_issues,
        "top_action": top_action,
        "report_pdf_url": None,
        "generated_at": now.isoformat(),
    }

    # Persist as a notification (in_app channel = banner in dashboard).
    payload = format_weekly_report_notification(
        score=score,
        delta=delta,
        resolved=resolved,
        new_issues=new_issues,
    )
    await send_notification(
        merchant_id=merchant_id,
        store_id=store_id,
        channel="in_app",
        category="weekly_report",
        supabase=supabase,
        **payload,
    )

    logger.info(
        "weekly_report_generated",
        store_id=store_id,
        merchant_id=merchant_id,
        score=score,
        delta=delta,
    )

    return report
