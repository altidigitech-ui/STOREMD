"""Stripe webhook receiver — signature validation, idempotency, event routing."""

from __future__ import annotations

from datetime import UTC, datetime

import stripe
import structlog
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.exceptions import AuthError, ErrorCode
from app.dependencies import get_supabase_service
from app.services.stripe_billing import STRIPE_PRICE_IDS

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def receive_stripe_webhook(request: Request) -> JSONResponse:
    """Receive and process Stripe webhooks."""
    body = await request.body()
    sig_header = request.headers.get("Stripe-Signature", "")

    # --- Signature validation ---
    try:
        event = stripe.Webhook.construct_event(
            body, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise AuthError(
            code=ErrorCode.STRIPE_PAYLOAD_INVALID,
            message="Invalid Stripe payload",
            status_code=400,
        )
    except stripe.SignatureVerificationError:
        raise AuthError(
            code=ErrorCode.STRIPE_SIGNATURE_INVALID,
            message="Invalid Stripe signature",
            status_code=401,
        )

    supabase = get_supabase_service()
    event_id = event["id"]
    event_type = event["type"]

    # --- Idempotency ---
    existing = (
        supabase.table("webhook_events")
        .select("id, processed")
        .eq("source", "stripe")
        .eq("external_id", event_id)
        .maybe_single()
        .execute()
    )

    if existing.data:
        return JSONResponse({"status": "already_processed"})

    # --- Store event ---
    supabase.table("webhook_events").insert({
        "source": "stripe",
        "external_id": event_id,
        "topic": event_type,
        "payload": event["data"],
        "processed": False,
    }).execute()

    # --- Process ---
    try:
        await _process_event(event_type, event["data"], supabase)

        supabase.table("webhook_events").update({
            "processed": True,
            "processed_at": datetime.now(UTC).isoformat(),
        }).eq("source", "stripe").eq("external_id", event_id).execute()

    except Exception as exc:
        logger.error("stripe_webhook_failed", event_type=event_type, error=str(exc))
        supabase.table("webhook_events").update({
            "processing_error": str(exc)[:500],
        }).eq("source", "stripe").eq("external_id", event_id).execute()

    logger.info("stripe_webhook_processed", event_type=event_type)
    return JSONResponse({"status": "accepted"})


async def _process_event(event_type: str, data: dict, supabase) -> None:
    handlers = {
        "checkout.session.completed": _handle_checkout_completed,
        "invoice.paid": _handle_invoice_paid,
        "invoice.payment_failed": _handle_invoice_payment_failed,
        "customer.subscription.updated": _handle_subscription_updated,
        "customer.subscription.deleted": _handle_subscription_deleted,
    }
    handler = handlers.get(event_type)
    if handler:
        await handler(data, supabase)


async def _handle_checkout_completed(data: dict, supabase) -> None:
    """New checkout completed — activate plan."""
    session = data.get("object", {})
    metadata = session.get("metadata", {})
    merchant_id = metadata.get("merchant_id")
    plan = metadata.get("plan")
    subscription_id = session.get("subscription")

    if not merchant_id or not plan:
        logger.warning("checkout_missing_metadata", session_id=session.get("id"))
        return

    # Update merchant plan
    supabase.table("merchants").update({
        "plan": plan,
        "stripe_subscription_id": subscription_id,
    }).eq("id", merchant_id).execute()

    # Create subscription record
    supabase.table("subscriptions").insert({
        "merchant_id": merchant_id,
        "stripe_subscription_id": subscription_id,
        "stripe_customer_id": session.get("customer", ""),
        "plan": plan,
        "status": "active",
    }).execute()

    logger.info("plan_activated", merchant_id=merchant_id, plan=plan)


async def _handle_invoice_paid(data: dict, supabase) -> None:
    """Invoice paid — confirm payment."""
    invoice = data.get("object", {})
    subscription_id = invoice.get("subscription")
    if subscription_id:
        logger.info("invoice_paid", subscription_id=subscription_id)


async def _handle_invoice_payment_failed(data: dict, supabase) -> None:
    """Payment failed — mark past_due."""
    invoice = data.get("object", {})
    subscription_id = invoice.get("subscription")
    if not subscription_id:
        return

    supabase.table("subscriptions").update({
        "status": "past_due",
    }).eq("stripe_subscription_id", subscription_id).execute()

    logger.warning("invoice_payment_failed", subscription_id=subscription_id)


async def _handle_subscription_updated(data: dict, supabase) -> None:
    """Subscription updated — plan change (upgrade/downgrade)."""
    subscription = data.get("object", {})
    subscription_id = subscription.get("id")
    items = subscription.get("items", {}).get("data", [])
    if not items:
        return

    new_price_id = items[0].get("price", {}).get("id")
    new_plan = None
    for plan, price_id in STRIPE_PRICE_IDS.items():
        if price_id == new_price_id:
            new_plan = plan
            break

    if not new_plan:
        logger.warning("unknown_price_id", price_id=new_price_id)
        return

    # Update subscription
    supabase.table("subscriptions").update({
        "plan": new_plan,
        "status": subscription.get("status", "active"),
        "cancel_at_period_end": subscription.get("cancel_at_period_end", False),
    }).eq("stripe_subscription_id", subscription_id).execute()

    # Update merchant
    sub = (
        supabase.table("subscriptions")
        .select("merchant_id")
        .eq("stripe_subscription_id", subscription_id)
        .maybe_single()
        .execute()
    )
    if sub.data:
        supabase.table("merchants").update({
            "plan": new_plan,
        }).eq("id", sub.data["merchant_id"]).execute()

        logger.info("plan_changed", merchant_id=sub.data["merchant_id"], plan=new_plan)


async def _handle_subscription_deleted(data: dict, supabase) -> None:
    """Subscription canceled — revert to free."""
    subscription = data.get("object", {})
    subscription_id = subscription.get("id")

    supabase.table("subscriptions").update({
        "status": "canceled",
        "canceled_at": datetime.now(UTC).isoformat(),
    }).eq("stripe_subscription_id", subscription_id).execute()

    sub = (
        supabase.table("subscriptions")
        .select("merchant_id")
        .eq("stripe_subscription_id", subscription_id)
        .maybe_single()
        .execute()
    )
    if sub.data:
        supabase.table("merchants").update({
            "plan": "free",
            "stripe_subscription_id": None,
        }).eq("id", sub.data["merchant_id"]).execute()

        logger.info("plan_canceled", merchant_id=sub.data["merchant_id"])
