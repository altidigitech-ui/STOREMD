"""Shopify OAuth install/callback routes."""

import json
import re
import secrets
from datetime import UTC, datetime
from urllib.parse import urlencode

import httpx
import structlog
from fastapi import APIRouter, Depends, Request

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
# RFC 4122 UUID and our short fallback IDs from frontend tracking.ts.
SESSION_ID_REGEX = re.compile(r"^[A-Za-z0-9_\-]{8,128}$")
INSTALL_RATE_LIMIT_PER_MINUTE = 20


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _enforce_install_rate_limit(request: Request, redis) -> None:
    """Cap repeated /install hits per IP — anti enumeration / abuse."""
    ip = _client_ip(request)
    key = f"install_rl:{ip}"
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 60)
        if count > INSTALL_RATE_LIMIT_PER_MINUTE:
            raise AuthError(
                code=ErrorCode.RATE_LIMIT_EXCEEDED,
                message="Too many install attempts — try again in a minute",
                status_code=429,
            )
    except AuthError:
        raise
    except Exception as exc:  # noqa: BLE001 — never block install on Redis hiccup
        logger.warning("install_rate_limit_error", error=str(exc))


@router.get("/install")
async def install(
    request: Request,
    shop: str,
    utm_source: str | None = None,
    utm_medium: str | None = None,
    utm_campaign: str | None = None,
    utm_content: str | None = None,
    utm_term: str | None = None,
    session_id: str | None = None,
    redis=Depends(get_redis),
):
    """Validate shop domain, generate state, redirect to Shopify consent."""
    await _enforce_install_rate_limit(request, redis)

    # Validate shop domain
    if not SHOP_DOMAIN_REGEX.match(shop):
        raise AuthError(
            code=ErrorCode.INVALID_SHOP_DOMAIN,
            message="Invalid shop domain",
            status_code=400,
        )

    # Drop session_id if it doesn't look like one our frontend would mint.
    # This blocks attackers from injecting arbitrary attribution payloads.
    if session_id and not SESSION_ID_REGEX.match(session_id):
        session_id = None

    # Cap UTM lengths so a 1MB query string can't bloat Redis state payloads.
    def _trim(v: str | None) -> str | None:
        return v[:128] if isinstance(v, str) else None

    utm_source = _trim(utm_source)
    utm_medium = _trim(utm_medium)
    utm_campaign = _trim(utm_campaign)
    utm_content = _trim(utm_content)
    utm_term = _trim(utm_term)

    # Generate anti-CSRF state nonce, stash shop + UTM payload in Redis
    # so the callback can attribute the install. 5 min TTL.
    state = secrets.token_urlsafe(32)
    state_payload = {
        "shop": shop,
        "utm_source": utm_source,
        "utm_medium": utm_medium,
        "utm_campaign": utm_campaign,
        "utm_content": utm_content,
        "utm_term": utm_term,
        "session_id": session_id,
    }
    await redis.setex(f"oauth_state:{state}", 300, json.dumps(state_payload))

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
    # Validate state (anti-CSRF). Stored value is JSON {shop, utm_*, session_id}
    # but legacy installs stored only the bare shop string — handle both.
    raw_state = await redis.get(f"oauth_state:{state}")
    if not raw_state:
        raise AuthError(
            code=ErrorCode.OAUTH_STATE_INVALID,
            message="Invalid or expired OAuth state",
            status_code=403,
        )

    try:
        state_payload = json.loads(raw_state)
        if not isinstance(state_payload, dict):
            raise ValueError("state payload is not a dict")
    except (ValueError, json.JSONDecodeError):
        state_payload = {"shop": raw_state}

    if state_payload.get("shop") != shop:
        raise AuthError(
            code=ErrorCode.OAUTH_STATE_INVALID,
            message="Invalid or expired OAuth state",
            status_code=403,
        )
    await redis.delete(f"oauth_state:{state}")

    utm_payload = {
        k: state_payload.get(k)
        for k in ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term")
    }
    install_session_id = state_payload.get("session_id")

    # Validate shop domain
    if not SHOP_DOMAIN_REGEX.match(shop):
        raise AuthError(
            code=ErrorCode.INVALID_SHOP_DOMAIN,
            message="Invalid shop domain",
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

        new_merchant_update: dict = {
            "shopify_shop_domain": shop,
            "shopify_access_token_encrypted": encrypted_token,
            "shopify_scopes": granted_scopes,
            "shopify_installed_at": datetime.now(UTC).isoformat(),
        }
        # Only record UTM attribution on the *first* install of a merchant.
        for k, v in utm_payload.items():
            if v:
                new_merchant_update[k] = v
        supabase.table("merchants").update(new_merchant_update).eq(
            "id", merchant_id
        ).execute()

        # Fire an install_complete tracking event so the funnel in the admin
        # dashboard can join landing visits → install. Best-effort.
        if install_session_id:
            try:
                supabase.table("tracking_events").insert(
                    {
                        "session_id": install_session_id,
                        "event_name": "install_complete",
                        "event_data": {
                            "shop": shop,
                            "merchant_id": merchant_id,
                        },
                        "utm_source": utm_payload.get("utm_source"),
                        "utm_medium": utm_payload.get("utm_medium"),
                        "utm_campaign": utm_payload.get("utm_campaign"),
                    }
                ).execute()
            except Exception as exc:  # noqa: BLE001 — non-blocking
                logger.warning("install_complete_event_failed", error=str(exc))

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
