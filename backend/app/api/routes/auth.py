"""Shopify OAuth install/callback routes."""

import re
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx
import jwt as pyjwt
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

SESSION_TTL_SECONDS = 60 * 60 * 24  # 24h


def sign_session_token(merchant_id: str, email: str, store_id: str) -> str:
    """Sign a Supabase-compatible session JWT with SUPABASE_JWT_SECRET.

    The same secret is used by JWTAuthMiddleware to validate incoming
    Bearer tokens, so sessions issued here authenticate downstream API
    calls without further exchange. user_metadata.active_store_id is
    consumed by the frontend's useCurrentStore hook.
    """
    now = datetime.now(UTC)
    payload = {
        "sub": merchant_id,
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
        "iss": f"{settings.SUPABASE_URL}/auth/v1",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=SESSION_TTL_SECONDS)).timestamp()),
        "user_metadata": {"active_store_id": store_id},
        "app_metadata": {"provider": "shopify"},
    }
    return pyjwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")


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

    # Register Shopify webhooks
    try:
        shopify_client = ShopifyClient(shop, encrypted_token)
        await register_webhooks(shopify_client)
        logger.info("webhooks_registered", shop=shop)
    except Exception as exc:
        logger.warning("webhook_registration_failed", shop=shop, error=str(exc))
        # Ne pas bloquer l'installation pour un échec webhook

    # Sign a session JWT the frontend can install via supabase.auth.setSession
    session_token = sign_session_token(merchant["id"], merchant["email"], store_id)

    target = "/dashboard" if merchant.get("onboarding_completed") else "/onboarding"
    query = urlencode(
        {
            "access_token": session_token,
            "refresh_token": session_token,
            "expires_in": SESSION_TTL_SECONDS,
            "token_type": "bearer",
        }
    )
    redirect_url = f"{settings.APP_URL}{target}?{query}"

    logger.info("oauth_completed", shop=shop, merchant_id=merchant["id"])
    return RedirectResponse(redirect_url)
