"""Celery tasks for scan execution."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import structlog

from app.core.exceptions import ErrorCode, ShopifyError
from app.dependencies import get_supabase_service
from tasks.celery_app import celery_app

logger = structlog.get_logger()

# Default modules per plan
PLAN_MODULES: dict[str, list[str]] = {
    "free": ["health"],
    "starter": ["health"],
    "pro": ["health", "listings", "agentic", "compliance", "browser"],
    "agency": ["health", "listings", "agentic", "compliance", "browser"],
}


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_scan(
    self,
    scan_id: str,
    store_id: str,
    merchant_id: str,
    modules: list[str],
    trigger: str = "manual",
) -> None:
    """Main Celery task — run a scan for a store."""
    _run_async(_run_scan_async(self, scan_id, store_id, merchant_id, modules, trigger))


async def _run_scan_async(
    task,
    scan_id: str,
    store_id: str,
    merchant_id: str,
    modules: list[str],
    trigger: str,
) -> None:
    from app.agent.memory import get_store_memory
    from app.agent.orchestrator import ScanOrchestrator
    from app.core.security import decrypt_token  # noqa: F401 — used by ShopifyClient
    from app.models.scan import AgentState
    from app.services.shopify import ShopifyClient

    supabase = get_supabase_service()

    # Mark scan as running
    supabase.table("scans").update({
        "status": "running",
        "started_at": datetime.now(UTC).isoformat(),
    }).eq("id", scan_id).execute()

    try:
        # Get store info for the ShopifyClient
        store = supabase.table("stores").select("*").eq("id", store_id).single().execute()
        merchant = (
            supabase.table("merchants")
            .select("shopify_access_token_encrypted")
            .eq("id", merchant_id)
            .single()
            .execute()
        )

        if not store.data or not merchant.data:
            raise ValueError("Store or merchant not found")

        encrypted_token = merchant.data["shopify_access_token_encrypted"]
        shopify = ShopifyClient(store.data["shopify_shop_domain"], encrypted_token)

        # Optionally load Claude API functions
        claude_analyze_fn = None
        claude_fix_fn = None
        try:
            from app.services.claude import claude_analyze, claude_generate_fix
            claude_analyze_fn = claude_analyze
            claude_fix_fn = claude_generate_fix
        except Exception:
            logger.warning("claude_api_unavailable")

        orchestrator = ScanOrchestrator(
            shopify=shopify,
            supabase=supabase,
            claude_analyze_fn=claude_analyze_fn,
            claude_fix_fn=claude_fix_fn,
            memory=get_store_memory(),
        )

        state = AgentState(
            scan_id=scan_id,
            store_id=store_id,
            merchant_id=merchant_id,
            modules=modules,
            trigger=trigger,
            metadata={
                "store_name": store.data.get("name", ""),
                "shop_domain": store.data["shopify_shop_domain"],
                "theme_name": store.data.get("theme_name", ""),
                "apps_count": store.data.get("apps_count", 0),
                "products_count": store.data.get("products_count", 0),
                "shopify_plan": store.data.get("shopify_plan", ""),
            },
        )

        await orchestrator.run(state)

        logger.info(
            "scan_completed",
            scan_id=scan_id,
            score=state.score,
            issues=len(state.issues),
        )

    except ShopifyError as exc:
        if exc.code == ErrorCode.SHOPIFY_RATE_LIMIT:
            logger.warning("scan_retry_rate_limit", scan_id=scan_id)
            supabase.table("scans").update({"status": "pending"}).eq("id", scan_id).execute()
            task.retry(countdown=120)
        else:
            _mark_failed(supabase, scan_id, str(exc), exc.code.value)
            raise

    except Exception as exc:
        logger.error("scan_failed", scan_id=scan_id, error=str(exc))
        _mark_failed(supabase, scan_id, str(exc), ErrorCode.SCAN_FAILED.value)
        raise


def _mark_failed(supabase, scan_id: str, message: str, code: str) -> None:
    supabase.table("scans").update({
        "status": "failed",
        "error_message": message[:500],
        "error_code": code,
        "completed_at": datetime.now(UTC).isoformat(),
    }).eq("id", scan_id).execute()


@celery_app.task
def run_scheduled_scans(plan: str) -> None:
    """Celery beat: trigger scans for all active stores of a given plan."""
    _run_async(_run_scheduled_scans_async(plan))


async def _run_scheduled_scans_async(plan: str) -> None:
    supabase = get_supabase_service()

    # Query merchants with this plan and active stores
    merchants = (
        supabase.table("merchants")
        .select("id, plan")
        .eq("plan", plan)
        .execute()
    )

    if not merchants.data:
        logger.info("no_merchants_for_plan", plan=plan)
        return

    modules = PLAN_MODULES.get(plan, ["health"])

    for merchant in merchants.data:
        # Get active stores for this merchant
        stores = (
            supabase.table("stores")
            .select("id")
            .eq("merchant_id", merchant["id"])
            .eq("status", "active")
            .execute()
        )

        for store in stores.data or []:
            # Create scan record
            scan_result = supabase.table("scans").insert({
                "store_id": store["id"],
                "merchant_id": merchant["id"],
                "status": "pending",
                "trigger": "cron",
                "modules": modules,
            }).execute()

            scan_id = scan_result.data[0]["id"]

            # Dispatch task
            run_scan.delay(scan_id, store["id"], merchant["id"], modules, "cron")
            logger.info(
                "scheduled_scan_dispatched",
                store_id=store["id"],
                plan=plan,
                scan_id=scan_id,
            )
