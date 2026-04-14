"""Shopify OAuth install/callback routes."""

import re
import secrets
from datetime import UTC, datetime
from urllib.parse import urlencode

import httpx
import structlog
from fastapi import APIRouter, Depends

from fastapi.responses import RedirectResponse

from app.config import settings
from app.core.exceptions import AuthError, ErrorCode
from app.core.security import encrypt_token
from app.dependencies import get_redis, get_supabase_service
from app.services.shopify import ShopifyClient
from app.services.webhook_registration import register_webhooks

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

SHOP_DOMAIN_REGEX = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9\-]*\.myshopify\.com$")


@router.get("/install")
async def install(
    shop: str,
    redis=Depends(get_redis),
):
    """Validate shop domain, generate state, redirect to Shopify consent."""
    # Validate shop domain
    if not SHOP_DOMAIN_REGEX.match(shop):
        raise AuthError(
            code=ErrorCode.INVALID_SHOP_DOMAIN,
            message=f"Invalid shop domain: {shop}",
            status_code=400,
        )

    # Generate anti-CSRF state nonce, store in Redis with 5 min TTL
    state = secrets.token_urlsafe(32)
    await redis.setex(f"oauth_state:{state}", 300, shop)

    # Build Shopify consent URL
    scopes = settings.SHOPIFY_SCOPES
    redirect_uri = f"{settings.BACKEND_URL}/api/v1/auth/callback"

    auth_url = (
        f"https://{shop}/admin/oauth/authorize"
        f"?client_id={settings.SHOPIFY_API_KEY}"
        f"&scope={scopes}"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
    )

    logger.info("oauth_install_redirect", shop=shop)
    return RedirectResponse(auth_url)


@router.get("/callback")
async def callback(
    code: str,
    state: str,
    shop: str,
    charge_id: str | None = None,
    redis=Depends(get_redis),
    supabase=Depends(get_supabase_service),
):
    """Validate state, exchange code for token, store encrypted, redirect to dashboard."""
    # Validate state (anti-CSRF)
    stored_shop = await redis.get(f"oauth_state:{state}")
    if not stored_shop or stored_shop != shop:
        raise AuthError(
            code=ErrorCode.OAUTH_STATE_INVALID,
            message="Invalid or expired OAuth state",
            status_code=403,
        )
    await redis.delete(f"oauth_state:{state}")

    # Validate shop domain
    if not SHOP_DOMAIN_REGEX.match(shop):
        raise AuthError(
            code=ErrorCode.INVALID_SHOP_DOMAIN,
            message=f"Invalid shop domain: {shop}",
            status_code=400,
        )

    # Exchange code for access token
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"https://{shop}/admin/oauth/access_token",
            json={
                "client_id": settings.SHOPIFY_API_KEY,
                "client_secret": settings.SHOPIFY_API_SECRET,
                "code": code,
            },
        )

        if response.status_code != 200:
            raise AuthError(
                code=ErrorCode.OAUTH_CODE_EXCHANGE_FAILED,
                message=f"Code exchange failed: {response.status_code}",
                status_code=502,
            )

        data = response.json()

    access_token = data.get("access_token")
    granted_scopes = data.get("scope", "").split(",")

    if not access_token:
        raise AuthError(
            code=ErrorCode.OAUTH_TOKEN_MISSING,
            message="No access token in Shopify response",
            status_code=502,
        )

    # Encrypt the token with Fernet
    encrypted_token = encrypt_token(access_token)

    # Upsert merchant
    existing_res = (
        supabase.table("merchants")
        .select("*")
        .eq("shopify_shop_domain", shop)
        .limit(1)
        .execute()
    )
    existing_merchant = (
        existing_res.data[0] if existing_res and existing_res.data else None
    )

    if existing_merchant:
        # Existing merchant — update token and scopes
        supabase.table("merchants").update(
            {
                "shopify_access_token_encrypted": encrypted_token,
                "shopify_scopes": granted_scopes,
                "shopify_installed_at": datetime.now(UTC).isoformat(),
            }
        ).eq("id", existing_merchant["id"]).execute()
        merchant = existing_merchant
    else:
        # New merchant — create via Supabase Auth
        # The trigger on_auth_user_created will create the merchant profile
        auth_response = supabase.auth.admin.create_user(
            {
                "email": f"{shop.replace('.myshopify.com', '')}@storemd.app",
                "email_confirm": True,
            }
        )
        merchant_id = auth_response.user.id

        supabase.table("merchants").update(
            {
                "shopify_shop_domain": shop,
                "shopify_access_token_encrypted": encrypted_token,
                "shopify_scopes": granted_scopes,
                "shopify_installed_at": datetime.now(UTC).isoformat(),
            }
        ).eq("id", merchant_id).execute()

        merchant_result = (
            supabase.table("merchants")
            .select("*")
            .eq("id", merchant_id)
            .single()
            .execute()
        )
        merchant = merchant_result.data

    # Upsert store
    existing_store_res = (
        supabase.table("stores")
        .select("id")
        .eq("shopify_shop_domain", shop)
        .eq("merchant_id", merchant["id"])
        .limit(1)
        .execute()
    )
    existing_store = (
        existing_store_res.data[0]
        if existing_store_res and existing_store_res.data
        else None
    )

    store_data = {
        "merchant_id": merchant["id"],
        "shopify_shop_domain": shop,
        "status": "active",
    }

    if existing_store:
        supabase.table("stores").update(store_data).eq(
            "id", existing_store["id"]
        ).execute()
        store_id = existing_store["id"]
    else:
        inserted = supabase.table("stores").insert(store_data).execute()
        store_id = inserted.data[0]["id"]

    # Register Shopify webhooks + fetch basic shop metadata so the
    # dashboard has real values before the first scan runs.
    shopify_client = ShopifyClient(shop, encrypted_token)
    try:
        await register_webhooks(shopify_client)
        logger.info("webhooks_registered", shop=shop)
    except Exception as exc:
        logger.warning("webhook_registration_failed", shop=shop, error=str(exc))
        # Ne pas bloquer l'installation pour un échec webhook

    try:
        shop_info = await shopify_client.graphql(
            "query { shop { name primaryDomain { url } currencyCode"
            " billingAddress { countryCodeV2 } plan { displayName } } }"
        )
        shop_node = shop_info["shop"]
        meta_update: dict = {
            "name": shop_node.get("name"),
            "primary_domain": (shop_node.get("primaryDomain") or {}).get("url"),
            "currency": shop_node.get("currencyCode"),
            "country": (shop_node.get("billingAddress") or {}).get("countryCodeV2"),
            "shopify_plan": (shop_node.get("plan") or {}).get("displayName", "").lower() or None,
        }
        meta_update = {k: v for k, v in meta_update.items() if v}
        if meta_update:
            supabase.table("stores").update(meta_update).eq(
                "id", store_id
            ).execute()
    except Exception as exc:  # noqa: BLE001 — non-blocking, scan will fill later
        logger.warning("store_name_fetch_failed", shop=shop, error=str(exc))

    # If Shopify appended a charge_id to the callback (merchant confirmed a
    # billing charge before completing OAuth), look up the active subscription
    # and activate the corresponding plan. Non-blocking on failure.
    if charge_id:
        try:
            from app.services.shopify_billing import (
                ShopifyBillingService,
                plan_from_subscription_name,
            )

            billing_service = ShopifyBillingService(shop, access_token)
            active = await billing_service.get_active_subscription()
            if active and active.get("status") == "ACTIVE":
                resolved_plan = plan_from_subscription_name(active.get("name"))
                supabase.table("merchants").update(
                    {
                        "plan": resolved_plan,
                        "billing_provider": "shopify",
                        "shopify_subscription_id": active.get("id"),
                    }
                ).eq("id", merchant["id"]).execute()
                logger.info(
                    "oauth_billing_activated",
                    shop=shop,
                    merchant_id=merchant["id"],
                    plan=resolved_plan,
                    charge_id=charge_id,
                )
        except Exception as exc:  # noqa: BLE001 — non-blocking
            logger.warning(
                "oauth_billing_activation_failed",
                shop=shop,
                charge_id=charge_id,
                error=str(exc),
            )

    # Stash the resolved store_id in app_metadata so the frontend can read it
    # from session.user.app_metadata.active_store_id after Supabase signs the
    # session. Also gives PostgREST RLS policies a route to the active store.
    supabase.auth.admin.update_user_by_id(
        merchant["id"],
        {"app_metadata": {"active_store_id": store_id, "provider": "shopify"}},
    )

    # Ask Supabase to mint a magic-link OTP. We intentionally skip Supabase's
    # /verify redirect flow here because the project's Site URL is inherited
    # from an older project and cannot be updated via API. Instead we hand the
    # email + OTP to our own /auth/verify page, which calls verifyOtp in JS
    # and lands the merchant on the target route on our own domain.
    target = "/dashboard" if merchant.get("onboarding_completed") else "/onboarding"
    link = supabase.auth.admin.generate_link(
        {
            "type": "magiclink",
            "email": merchant["email"],
        }
    )
    otp = link.properties.email_otp
    query = urlencode(
        {"email": merchant["email"], "token": otp, "target": target}
    )
    redirect_url = f"{settings.APP_URL}/auth/verify?{query}"

    logger.info("oauth_completed", shop=shop, merchant_id=merchant["id"])
    return RedirectResponse(redirect_url)
