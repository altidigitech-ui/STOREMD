"""Admin dashboard endpoints — only altidigitech@gmail.com.

KPIs, traffic analytics, recent merchants/scans/errors. All endpoints
read service_role to bypass RLS but are gated by the email guard.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter, Depends

from app.core.exceptions import AuthError, ErrorCode
from app.dependencies import get_current_merchant, get_supabase_service

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

ADMIN_EMAIL = "altidigitech@gmail.com"

PLAN_PRICING_EUR = {
    "starter": 29,
    "pro": 79,
    "agency": 199,
}


def _require_admin(merchant: dict) -> None:
    if (merchant.get("email") or "").lower() != ADMIN_EMAIL:
        raise AuthError(
            code=ErrorCode.STORE_ACCESS_DENIED,
            message="Admin access required",
            status_code=403,
        )


def _today_utc_start() -> datetime:
    now = datetime.now(UTC)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _date_n_days_ago(n: int) -> datetime:
    return _today_utc_start() - timedelta(days=n)


def _count_table(supabase, table: str, *, gte_col: str | None = None, gte_value=None) -> int:
    """Count rows with optional time filter — uses head=True for efficiency."""
    q = supabase.table(table).select("id", count="exact", head=True)
    if gte_col and gte_value is not None:
        q = q.gte(gte_col, gte_value)
    res = q.execute()
    return getattr(res, "count", 0) or 0


@router.get("/overview")
async def admin_overview(merchant: dict = Depends(get_current_merchant)) -> dict:
    _require_admin(merchant)
    supabase = get_supabase_service()

    today = _today_utc_start()
    week_ago = _date_n_days_ago(7)
    month_ago = _date_n_days_ago(30)

    total_merchants = _count_table(supabase, "merchants")
    total_stores = _count_table(supabase, "stores")
    total_scans = _count_table(supabase, "scans")
    scans_today = _count_table(supabase, "scans", gte_col="created_at", gte_value=today.isoformat())
    scans_this_week = _count_table(
        supabase, "scans", gte_col="created_at", gte_value=week_ago.isoformat()
    )

    plans_res = supabase.table("merchants").select("plan").execute()
    plans = [(r.get("plan") or "free") for r in (plans_res.data or [])]
    active_subscriptions = sum(1 for p in plans if p in PLAN_PRICING_EUR)
    mrr = sum(PLAN_PRICING_EUR.get(p, 0) for p in plans)

    score_res = (
        supabase.table("scans")
        .select("score")
        .eq("status", "completed")
        .not_.is_("score", "null")
        .order("created_at", desc=True)
        .limit(500)
        .execute()
    )
    scores = [r["score"] for r in (score_res.data or []) if r.get("score") is not None]
    avg_health_score = round(sum(scores) / len(scores), 1) if scores else None

    visits_today = _count_table(
        supabase, "page_views", gte_col="created_at", gte_value=today.isoformat()
    )
    visits_this_week = _count_table(
        supabase, "page_views", gte_col="created_at", gte_value=week_ago.isoformat()
    )
    visits_this_month = _count_table(
        supabase, "page_views", gte_col="created_at", gte_value=month_ago.isoformat()
    )

    unique_today_res = (
        supabase.table("page_views")
        .select("session_id")
        .gte("created_at", today.isoformat())
        .limit(50000)
        .execute()
    )
    unique_visitors_today = len(
        {r["session_id"] for r in (unique_today_res.data or []) if r.get("session_id")}
    )

    installs_today = _count_table(
        supabase, "merchants", gte_col="created_at", gte_value=today.isoformat()
    )

    conversion_rate = (
        round((installs_today / unique_visitors_today) * 100, 2)
        if unique_visitors_today > 0
        else 0.0
    )

    return {
        "total_merchants": total_merchants,
        "total_stores": total_stores,
        "total_scans": total_scans,
        "scans_today": scans_today,
        "scans_this_week": scans_this_week,
        "active_subscriptions": active_subscriptions,
        "mrr": mrr,
        "avg_health_score": avg_health_score,
        "visits_today": visits_today,
        "visits_this_week": visits_this_week,
        "visits_this_month": visits_this_month,
        "unique_visitors_today": unique_visitors_today,
        "installs_today": installs_today,
        "conversion_rate": conversion_rate,
    }


@router.get("/merchants")
async def admin_merchants(merchant: dict = Depends(get_current_merchant)) -> dict:
    _require_admin(merchant)
    supabase = get_supabase_service()

    res = (
        supabase.table("merchants")
        .select(
            "id,email,plan,billing_provider,utm_source,utm_medium,utm_campaign,"
            "shopify_shop_domain,created_at"
        )
        .order("created_at", desc=True)
        .limit(200)
        .execute()
    )
    merchants = res.data or []

    # Best-effort enrichment: last scan score per merchant (one bulk query).
    if merchants:
        merchant_ids = [m["id"] for m in merchants]
        scans_res = (
            supabase.table("scans")
            .select("merchant_id,score,created_at")
            .in_("merchant_id", merchant_ids)
            .eq("status", "completed")
            .order("created_at", desc=True)
            .limit(2000)
            .execute()
        )
        latest: dict[str, int] = {}
        for s in scans_res.data or []:
            mid = s.get("merchant_id")
            if mid and mid not in latest and s.get("score") is not None:
                latest[mid] = s["score"]
        for m in merchants:
            m["last_scan_score"] = latest.get(m["id"])

    return {"merchants": merchants}


@router.get("/scans")
async def admin_scans(
    limit: int = 50,
    merchant: dict = Depends(get_current_merchant),
) -> dict:
    _require_admin(merchant)
    supabase = get_supabase_service()
    limit = max(1, min(limit, 200))

    res = (
        supabase.table("scans")
        .select("id,store_id,status,score,duration_ms,created_at")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    scans = res.data or []

    if scans:
        store_ids = list({s["store_id"] for s in scans if s.get("store_id")})
        stores_res = (
            supabase.table("stores")
            .select("id,shopify_shop_domain")
            .in_("id", store_ids)
            .execute()
        )
        domain_by_id = {s["id"]: s.get("shopify_shop_domain") for s in stores_res.data or []}
        for s in scans:
            s["shopify_shop_domain"] = domain_by_id.get(s.get("store_id"))
            s["duration_seconds"] = (
                round(s["duration_ms"] / 1000, 1) if s.get("duration_ms") else None
            )

    return {"scans": scans}


@router.get("/errors")
async def admin_errors(
    limit: int = 50,
    merchant: dict = Depends(get_current_merchant),
) -> dict:
    _require_admin(merchant)
    supabase = get_supabase_service()
    limit = max(1, min(limit, 200))

    res = (
        supabase.table("webhook_events")
        .select("id,source,topic,shop_domain,processing_error,retry_count,created_at")
        .not_.is_("processing_error", "null")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return {"errors": res.data or []}


@router.get("/analytics")
async def admin_analytics(merchant: dict = Depends(get_current_merchant)) -> dict:
    _require_admin(merchant)
    supabase = get_supabase_service()

    thirty_days_ago = _date_n_days_ago(30)

    # Pull last 30 days of page_views once and aggregate in Python — avoids
    # firing 5+ separate queries. Capped at 100k rows which is plenty for now.
    pv_res = (
        supabase.table("page_views")
        .select("session_id,path,utm_source,utm_campaign,device,created_at")
        .gte("created_at", thirty_days_ago.isoformat())
        .limit(100000)
        .execute()
    )
    page_views = pv_res.data or []

    # Visits + unique by day
    by_day_visits: dict[str, int] = defaultdict(int)
    by_day_sessions: dict[str, set] = defaultdict(set)
    by_source: dict[str, int] = defaultdict(int)
    by_campaign: dict[str, int] = defaultdict(int)
    by_device: dict[str, int] = defaultdict(int)
    by_path: dict[str, int] = defaultdict(int)

    for pv in page_views:
        created = pv.get("created_at") or ""
        day = created[:10]
        by_day_visits[day] += 1
        if pv.get("session_id"):
            by_day_sessions[day].add(pv["session_id"])
        by_source[pv.get("utm_source") or "(direct)"] += 1
        if pv.get("utm_campaign"):
            by_campaign[pv["utm_campaign"]] += 1
        by_device[pv.get("device") or "unknown"] += 1
        by_path[pv.get("path") or "/"] += 1

    # Installs per source/campaign — count merchants created in the same window
    merch_res = (
        supabase.table("merchants")
        .select("utm_source,utm_campaign,created_at")
        .gte("created_at", thirty_days_ago.isoformat())
        .limit(100000)
        .execute()
    )
    installs_by_source: dict[str, int] = defaultdict(int)
    installs_by_campaign: dict[str, int] = defaultdict(int)
    installs_total = 0
    for m in merch_res.data or []:
        installs_total += 1
        installs_by_source[m.get("utm_source") or "(direct)"] += 1
        if m.get("utm_campaign"):
            installs_by_campaign[m["utm_campaign"]] += 1

    visits_by_day = [
        {
            "date": day,
            "visits": by_day_visits[day],
            "unique_visitors": len(by_day_sessions[day]),
        }
        for day in sorted(by_day_visits.keys())
    ]

    visits_by_source = sorted(
        [
            {"source": s, "visits": v, "installs": installs_by_source.get(s, 0)}
            for s, v in by_source.items()
        ],
        key=lambda r: r["visits"],
        reverse=True,
    )
    visits_by_campaign = sorted(
        [
            {"campaign": c, "visits": v, "installs": installs_by_campaign.get(c, 0)}
            for c, v in by_campaign.items()
        ],
        key=lambda r: r["visits"],
        reverse=True,
    )
    visits_by_device = sorted(
        [{"device": d, "visits": v} for d, v in by_device.items()],
        key=lambda r: r["visits"],
        reverse=True,
    )
    top_pages = sorted(
        [{"path": p, "visits": v} for p, v in by_path.items()],
        key=lambda r: r["visits"],
        reverse=True,
    )[:20]

    # Funnel — events in the same 30-day window.
    landing_visits = len(page_views)

    def _event_count(name: str) -> int:
        r = (
            supabase.table("tracking_events")
            .select("id", count="exact", head=True)
            .eq("event_name", name)
            .gte("created_at", thirty_days_ago.isoformat())
            .execute()
        )
        return getattr(r, "count", 0) or 0

    cta_clicks = _event_count("cta_click")
    install_starts = _event_count("install_start")
    install_completes = _event_count("install_complete")

    paid_res = (
        supabase.table("merchants")
        .select("id", count="exact", head=True)
        .neq("plan", "free")
        .gte("created_at", thirty_days_ago.isoformat())
        .execute()
    )
    paid_conversions = getattr(paid_res, "count", 0) or 0

    return {
        "visits_by_day": visits_by_day,
        "visits_by_source": visits_by_source,
        "visits_by_campaign": visits_by_campaign,
        "visits_by_device": visits_by_device,
        "top_pages": top_pages,
        "funnel": {
            "landing_visits": landing_visits,
            "cta_clicks": cta_clicks,
            "install_starts": install_starts,
            "install_completes": install_completes,
            "paid_conversions": paid_conversions,
            "installs_total": installs_total,
        },
    }
