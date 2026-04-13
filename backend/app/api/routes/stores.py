"""Store API routes — store info, installed apps."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends

from app.dependencies import get_current_merchant, get_current_store, get_supabase_service

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/stores/{store_id}", tags=["stores"])


@router.get("")
async def get_store(
    store_id: str,
    merchant: dict = Depends(get_current_merchant),
    store: dict = Depends(get_current_store),
) -> dict:
    """Get store information."""
    return {
        "id": store["id"],
        "shopify_shop_domain": store.get("shopify_shop_domain"),
        "name": store.get("name"),
        "primary_domain": store.get("primary_domain"),
        "theme_name": store.get("theme_name"),
        "products_count": store.get("products_count", 0),
        "apps_count": store.get("apps_count", 0),
        "currency": store.get("currency", "USD"),
        "country": store.get("country"),
        "shopify_plan": store.get("shopify_plan"),
        "status": store.get("status", "active"),
        "created_at": store.get("created_at"),
    }


@router.get("/apps")
async def get_store_apps(
    store_id: str,
    merchant: dict = Depends(get_current_merchant),
    store: dict = Depends(get_current_store),
) -> dict:
    """Get installed apps with their impact metrics."""
    supabase = get_supabase_service()

    apps_result = (
        supabase.table("store_apps")
        .select("*")
        .eq("store_id", store_id)
        .eq("merchant_id", merchant["id"])
        .order("impact_ms", desc=True)
        .execute()
    )

    apps = apps_result.data or []

    total_impact_ms = sum(a.get("impact_ms") or 0 for a in apps)

    data = [
        {
            "id": a["id"],
            "name": a["name"],
            "handle": a.get("handle"),
            "status": a.get("status", "active"),
            "impact_ms": a.get("impact_ms"),
            "scripts_count": a.get("scripts_count", 0),
            "scripts_size_kb": a.get("scripts_size_kb", 0),
            "css_size_kb": a.get("css_size_kb", 0),
            "billing_amount": a.get("billing_amount"),
            "scopes": a.get("scopes", []),
            "developer": a.get("developer"),
            "first_detected_at": a.get("first_detected_at"),
        }
        for a in apps
    ]

    apps_count_from_scan = store.get("apps_count") or 0
    # "Known" = we either persisted rows OR the last scan told us a real count.
    apps_count_known = len(apps) > 0 or apps_count_from_scan > 0

    return {
        "data": data,
        "total_apps": len(apps),
        "total_impact_ms": total_impact_ms,
        "apps_count_known": apps_count_known,
        "apps_count_from_scan": apps_count_from_scan,
    }
