"""Shopify Billing API routes — subscribe, confirm, status, cancel.

Parallel to /api/v1/billing (Stripe). Used for merchants who installed via
the Shopify App Store.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.core.exceptions import AuthError, BillingError, ErrorCode
from app.core.security import decrypt_token
from app.dependencies import get_current_merchant, get_supabase_service
from app.services.shopify_billing import (
    ShopifyBillingService,
    plan_from_subscription_name,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/shopify-billing", tags=["shopify-billing"])


class SubscribeRequest(BaseModel):
    plan: str = Field(..., pattern="^(starter|pro|agency)$")


def _require_shopify_merchant(merchant: dict) -> tuple[str, str]:
    """Return (shop_domain, decrypted_access_token) for a Shopify-connected merchant."""
    shop = merchant.get("shopify_shop_domain")
    encrypted = merchant.get("shopify_access_token_encrypted")
    if not shop or not encrypted:
        raise AuthError(
            code=ErrorCode.SHOPIFY_STORE_NOT_FOUND,
            message="Merchant is not connected to a Shopify store",
            status_code=400,
        )
    return shop, decrypt_token(encrypted)


@router.post("/subscribe")
async def subscribe(
    request: SubscribeRequest,
    merchant: dict = Depends(get_current_merchant),
) -> dict:
    """Create a Shopify app subscription. Returns the confirmation URL."""
    shop, access_token = _require_shopify_merchant(merchant)

    return_url = (
        f"{settings.BACKEND_URL}/api/v1/shopify-billing/confirm"
        f"?shop={shop}&plan={request.plan}&merchant_id={merchant['id']}"
    )

    service = ShopifyBillingService(shop, access_token)
    result = await service.create_subscription(request.plan, return_url)

    return {
        "confirmation_url": result["confirmation_url"],
        "subscription_id": result["subscription_id"],
    }


@router.get("/confirm")
async def confirm(
    shop: str = Query(...),
    charge_id: str | None = Query(default=None),
    plan: str = Query(...),
    merchant_id: str = Query(...),
    supabase=Depends(get_supabase_service),
):
    """Callback after the merchant confirms a Shopify subscription.

    Shopify redirects here with ?charge_id=<id>. We verify the active
    subscription on Shopify, then activate the plan in the DB and
    redirect back to the dashboard settings page.
    """
    result = (
        supabase.table("merchants")
        .select("id, shopify_shop_domain, shopify_access_token_encrypted")
        .eq("id", merchant_id)
        .eq("shopify_shop_domain", shop)
        .limit(1)
        .execute()
    )
    if not result or not result.data:
        raise AuthError(
            code=ErrorCode.MERCHANT_NOT_FOUND,
            message="Merchant not found for this shop",
            status_code=404,
        )
    merchant = result.data[0]
    access_token = decrypt_token(merchant["shopify_access_token_encrypted"])

    service = ShopifyBillingService(shop, access_token)
    active = await service.get_active_subscription()

    if not active or active.get("status") != "ACTIVE":
        # Merchant declined or subscription is pending.
        logger.warning(
            "shopify_billing_not_active",
            shop=shop,
            merchant_id=merchant_id,
            charge_id=charge_id,
            status=(active or {}).get("status"),
        )
        redirect = f"{settings.APP_URL}/dashboard/settings?billing=declined"
        return RedirectResponse(redirect)

    # Resolve plan from the active subscription name (authoritative)
    resolved_plan = plan_from_subscription_name(active.get("name")) or plan

    supabase.table("merchants").update(
        {
            "plan": resolved_plan,
            "billing_provider": "shopify",
            "shopify_subscription_id": active.get("id"),
        }
    ).eq("id", merchant_id).execute()

    logger.info(
        "shopify_billing_confirmed",
        shop=shop,
        merchant_id=merchant_id,
        plan=resolved_plan,
        subscription_id=active.get("id"),
    )

    redirect = f"{settings.APP_URL}/dashboard/settings?billing=success"
    return RedirectResponse(redirect)


@router.get("/status")
async def status(
    merchant: dict = Depends(get_current_merchant),
) -> dict:
    """Return the current plan + Shopify subscription status for this merchant."""
    shop = merchant.get("shopify_shop_domain")
    subscription_id = merchant.get("shopify_subscription_id")
    encrypted = merchant.get("shopify_access_token_encrypted")

    active_subscription: dict | None = None
    if shop and encrypted and merchant.get("billing_provider") == "shopify":
        try:
            service = ShopifyBillingService(shop, decrypt_token(encrypted))
            active_subscription = await service.get_active_subscription()
        except BillingError as exc:
            logger.warning(
                "shopify_billing_status_query_failed",
                shop=shop,
                error=exc.message,
            )

    return {
        "plan": merchant.get("plan", "free"),
        "billing_provider": merchant.get("billing_provider"),
        "subscription_id": subscription_id,
        "active_subscription": active_subscription,
    }


@router.delete("/cancel")
async def cancel(
    merchant: dict = Depends(get_current_merchant),
    supabase=Depends(get_supabase_service),
) -> dict:
    """Cancel the merchant's Shopify subscription and reset to the Free plan."""
    shop, access_token = _require_shopify_merchant(merchant)
    subscription_id = merchant.get("shopify_subscription_id")

    if not subscription_id:
        raise BillingError(
            code=ErrorCode.STRIPE_SUBSCRIPTION_NOT_FOUND,
            message="No active Shopify subscription to cancel",
            status_code=404,
        )

    service = ShopifyBillingService(shop, access_token)
    await service.cancel_subscription(subscription_id)

    supabase.table("merchants").update(
        {
            "plan": "free",
            "shopify_subscription_id": None,
        }
    ).eq("id", merchant["id"]).execute()

    return {"status": "canceled"}
