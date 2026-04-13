"""GDPR compliance webhooks required by Shopify for public apps.

Shopify requires three dedicated HTTPS endpoints:
- customers/data_request : merchant-mediated customer data request
- customers/redact       : customer deletion request (48h after order activity stop)
- shop/redact            : full shop data deletion (48h after uninstall)

All three are HMAC-signed with SHOPIFY_API_SECRET and must return 2xx.
StoreMD does NOT store customer PII, so customer endpoints are acknowledgement-only.
"""

from __future__ import annotations

import json

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.api.middleware.hmac import verify_shopify_webhook_hmac
from app.dependencies import get_supabase_service

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/webhooks", tags=["gdpr"])


def _extract_shop(request: Request, payload: dict) -> str:
    """Shopify sends shop domain in header; fall back to payload field."""
    return (
        request.headers.get("X-Shopify-Shop-Domain")
        or payload.get("shop_domain")
        or ""
    )


@router.post("/customers/data_request")
async def customers_data_request(request: Request) -> JSONResponse:
    """Customer requests their data. StoreMD stores no customer PII — ack only."""
    body = await request.body()
    await verify_shopify_webhook_hmac(
        body, request.headers.get("X-Shopify-Hmac-Sha256")
    )

    payload = json.loads(body) if body else {}
    logger.info("gdpr_data_request", shop=_extract_shop(request, payload))
    return JSONResponse({"status": "ok"}, status_code=200)


@router.post("/customers/redact")
async def customers_redact(request: Request) -> JSONResponse:
    """Customer deletion request. StoreMD stores no customer PII — ack only."""
    body = await request.body()
    await verify_shopify_webhook_hmac(
        body, request.headers.get("X-Shopify-Hmac-Sha256")
    )

    payload = json.loads(body) if body else {}
    logger.info("gdpr_customers_redact", shop=_extract_shop(request, payload))
    return JSONResponse({"status": "ok"}, status_code=200)


@router.post("/shop/redact")
async def shop_redact(request: Request) -> JSONResponse:
    """Shop uninstalled — purge all merchant/store data (fired 48h after uninstall)."""
    body = await request.body()
    await verify_shopify_webhook_hmac(
        body, request.headers.get("X-Shopify-Hmac-Sha256")
    )

    payload = json.loads(body) if body else {}
    shop_domain = _extract_shop(request, payload)
    logger.info("gdpr_shop_redact_received", shop=shop_domain)

    supabase = get_supabase_service()

    try:
        store_result = (
            supabase.table("stores")
            .select("id, merchant_id")
            .eq("shopify_shop_domain", shop_domain)
            .execute()
        )
        if store_result.data:
            store = store_result.data[0]
            store_id = store["id"]
            merchant_id = store["merchant_id"]

            supabase.table("scan_issues").delete().eq("store_id", store_id).execute()
            supabase.table("scans").delete().eq("store_id", store_id).execute()
            supabase.table("store_apps").delete().eq("store_id", store_id).execute()
            supabase.table("stores").delete().eq("id", store_id).execute()
            supabase.table("merchants").delete().eq("id", merchant_id).execute()

            logger.info(
                "gdpr_shop_data_deleted",
                shop=shop_domain,
                store_id=store_id,
                merchant_id=merchant_id,
            )
        else:
            logger.info("gdpr_shop_redact_no_store", shop=shop_domain)
    except Exception as exc:  # noqa: BLE001
        # Always 200 — Shopify retries on non-2xx and we've logged for manual cleanup.
        logger.error(
            "gdpr_shop_redact_failed", shop=shop_domain, error=str(exc)
        )

    return JSONResponse({"status": "ok"}, status_code=200)
