"""Shopify webhook receiver — HMAC validation, idempotency, topic routing."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import AuthError, ErrorCode
from app.core.security import validate_shopify_hmac
from app.config import settings
from app.dependencies import get_supabase_service

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post("/shopify")
async def receive_shopify_webhook(request: Request) -> JSONResponse:
    """Receive and process Shopify webhooks.

    1. Validate HMAC
    2. Check idempotency (webhook_events table)
    3. Store event and process
    """
    body = await request.body()

    # --- HMAC validation ---
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256")
    if not hmac_header:
        raise AuthError(
            code=ErrorCode.HMAC_MISSING,
            message="Missing X-Shopify-Hmac-Sha256 header",
            status_code=401,
        )

    if not validate_shopify_hmac(body, hmac_header, settings.SHOPIFY_API_SECRET):
        raise AuthError(
            code=ErrorCode.HMAC_INVALID,
            message="Invalid HMAC — possible tampered webhook",
            status_code=401,
        )

    # --- Extract headers ---
    topic = request.headers.get("X-Shopify-Topic", "")
    shop_domain = request.headers.get("X-Shopify-Shop-Domain", "")
    webhook_id = request.headers.get("X-Shopify-Webhook-Id", "")

    if not webhook_id:
        raise AuthError(
            code=ErrorCode.HMAC_MISSING,
            message="Missing X-Shopify-Webhook-Id header",
            status_code=401,
        )

    supabase = get_supabase_service()

    # --- Idempotency check ---
    existing = (
        supabase.table("webhook_events")
        .select("id, processed")
        .eq("source", "shopify")
        .eq("external_id", webhook_id)
        .limit(1)
        .execute()
    )

    if existing and existing.data:
        logger.info("webhook_duplicate", topic=topic, webhook_id=webhook_id)
        return JSONResponse({"status": "already_processed"})

    # --- Store event ---
    import json
    payload = json.loads(body) if body else {}

    supabase.table("webhook_events").insert({
        "source": "shopify",
        "external_id": webhook_id,
        "topic": topic,
        "shop_domain": shop_domain,
        "payload": payload,
        "processed": False,
    }).execute()

    # --- Process synchronously (lightweight handlers) ---
    try:
        await _process_topic(topic, shop_domain, payload, supabase)

        supabase.table("webhook_events").update({
            "processed": True,
            "processed_at": datetime.now(UTC).isoformat(),
        }).eq("source", "shopify").eq("external_id", webhook_id).execute()

    except Exception as exc:
        logger.error("webhook_processing_failed", topic=topic, error=str(exc))
        supabase.table("webhook_events").update({
            "processing_error": str(exc)[:500],
            "retry_count": 1,
        }).eq("source", "shopify").eq("external_id", webhook_id).execute()

    logger.info("webhook_received", topic=topic, shop=shop_domain)
    return JSONResponse({"status": "accepted"})


async def _process_topic(
    topic: str, shop_domain: str, payload: dict, supabase
) -> None:
    """Route webhook to the appropriate handler."""
    handlers = {
        "app/uninstalled": _handle_app_uninstalled,
        "customers/data_request": _handle_gdpr_data_request,
        "customers/redact": _handle_gdpr_customers_redact,
        "shop/redact": _handle_gdpr_shop_redact,
        "products/create": _handle_product_created,
        "products/update": _handle_product_updated,
        "themes/update": _handle_theme_updated,
        "app_subscriptions/update": _handle_app_subscription_updated,
    }

    handler = handlers.get(topic)
    if handler:
        await handler(shop_domain, payload, supabase)
    else:
        logger.warning("unknown_webhook_topic", topic=topic, shop=shop_domain)


async def _handle_app_uninstalled(shop: str, payload: dict, supabase) -> None:
    """Cleanup: cancel Stripe, mark uninstalled, delete token."""
    store = _get_store_by_domain(shop, supabase)
    if not store:
        return

    merchant_id = store["merchant_id"]

    # Grab the merchant's email *before* we strip the token / mark uninstalled
    # so the feedback email below has a recipient to write to.
    merchant_row = (
        supabase.table("merchants")
        .select("email, notification_email")
        .eq("id", merchant_id)
        .maybe_single()
        .execute()
    )
    merchant_data = getattr(merchant_row, "data", None) or {}
    recipient = (
        merchant_data.get("notification_email") or merchant_data.get("email")
    )

    # Cancel Stripe subscription
    from app.services.stripe_billing import StripeBillingService
    billing = StripeBillingService(supabase)
    billing.cancel_subscription(merchant_id)

    # Mark store as uninstalled
    supabase.table("stores").update({
        "status": "uninstalled",
        "uninstalled_at": datetime.now(UTC).isoformat(),
    }).eq("id", store["id"]).execute()

    # Delete Shopify token
    supabase.table("merchants").update({
        "shopify_access_token_encrypted": None,
    }).eq("id", merchant_id).execute()

    # Uninstall feedback email — best-effort, never fail the webhook on it.
    if recipient and not recipient.endswith("@storemd.app"):
        try:
            from app.services import email_service

            email_service.send_uninstall_feedback(
                merchant_email=recipient,
                shop_domain=shop,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "uninstall_feedback_email_failed",
                shop=shop,
                error=str(exc),
            )

    # Mem0 GDPR cleanup — best-effort.
    try:
        from app.agent.memory import get_store_memory

        memory = get_store_memory()
        await memory.forget_merchant(merchant_id)
        await memory.forget_store(store["id"])
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "mem0_uninstall_cleanup_failed",
            shop=shop,
            error=str(exc),
        )

    logger.info("app_uninstalled_cleanup", shop=shop, merchant_id=merchant_id)


async def _handle_gdpr_data_request(shop: str, payload: dict, supabase) -> None:
    """GDPR: Shopify asks for customer data. StoreMD stores no customer data."""
    logger.info("gdpr_data_request", shop=shop)


async def _handle_gdpr_customers_redact(shop: str, payload: dict, supabase) -> None:
    """GDPR: Shopify asks to delete customer data."""
    logger.info("gdpr_customers_redact", shop=shop)


async def _handle_gdpr_shop_redact(shop: str, payload: dict, supabase) -> None:
    """GDPR: 48h after uninstall — delete ALL store data."""
    store = _get_store_by_domain(shop, supabase)
    if store:
        supabase.table("stores").delete().eq("id", store["id"]).execute()
        logger.info("gdpr_shop_redacted", shop=shop, store_id=store["id"])


async def _handle_product_created(shop: str, payload: dict, supabase) -> None:
    """New product: trigger listing analysis (Starter+)."""
    store = _get_store_by_domain(shop, supabase)
    if not store:
        return

    merchant = _get_merchant(store["merchant_id"], supabase)
    if merchant and merchant.get("plan") in ("starter", "pro", "agency"):
        logger.info("product_created_trigger", shop=shop, product_id=payload.get("id"))


async def _handle_product_updated(shop: str, payload: dict, supabase) -> None:
    """Product updated: check agentic readiness (Pro+)."""
    store = _get_store_by_domain(shop, supabase)
    if not store:
        return

    merchant = _get_merchant(store["merchant_id"], supabase)
    if merchant and merchant.get("plan") in ("pro", "agency"):
        logger.info("product_updated_trigger", shop=shop, product_id=payload.get("id"))


async def _handle_theme_updated(shop: str, payload: dict, supabase) -> None:
    """Theme updated: create a collection backup (feature #7) + trigger rescan (Pro+)."""
    store = _get_store_by_domain(shop, supabase)
    if not store:
        return

    merchant = _get_merchant(store["merchant_id"], supabase)
    if not merchant:
        return

    plan = merchant.get("plan")

    # Collection backup (Starter+) — best-effort.
    if plan in ("starter", "pro", "agency"):
        try:
            from app.services.backup import create_collection_backup
            from app.services.shopify import ShopifyClient

            encrypted = merchant.get("shopify_access_token_encrypted")
            if encrypted:
                shopify = ShopifyClient(
                    store["shopify_shop_domain"], encrypted
                )
                await create_collection_backup(
                    store_id=store["id"],
                    shopify=shopify,
                    supabase=supabase,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "theme_update_backup_failed",
                shop=shop,
                error=str(exc),
            )

    # Trigger a light rescan (Pro+).
    if plan in ("pro", "agency"):
        logger.info("theme_updated_trigger", shop=shop)


async def _handle_app_subscription_updated(
    shop: str, payload: dict, supabase
) -> None:
    """App subscription change: log for ghost billing detection."""
    logger.info("app_subscription_updated", shop=shop)


def _get_store_by_domain(shop: str, supabase) -> dict | None:
    result = (
        supabase.table("stores")
        .select("id, merchant_id")
        .eq("shopify_shop_domain", shop)
        .maybe_single()
        .execute()
    )
    return result.data


def _get_merchant(merchant_id: str, supabase) -> dict | None:
    result = (
        supabase.table("merchants")
        .select("id, plan")
        .eq("id", merchant_id)
        .maybe_single()
        .execute()
    )
    return result.data
