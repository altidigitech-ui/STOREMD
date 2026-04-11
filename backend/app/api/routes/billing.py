"""Billing API routes — checkout, portal, usage."""

from __future__ import annotations

from datetime import date

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.config import settings
from app.dependencies import get_current_merchant, get_supabase_service
from app.services.stripe_billing import StripeBillingService

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    plan: str = Field(..., pattern="^(starter|pro|agency)$")


@router.post("/checkout")
async def create_checkout(
    request: CheckoutRequest,
    merchant: dict = Depends(get_current_merchant),
) -> dict:
    """Create a Stripe Checkout session for upgrading."""
    billing = StripeBillingService(get_supabase_service())
    url = billing.create_checkout_session(
        merchant_id=merchant["id"],
        plan=request.plan,
        return_url=f"{settings.APP_URL}/dashboard/settings",
    )
    return {"checkout_url": url}


@router.get("/portal")
async def get_portal(
    merchant: dict = Depends(get_current_merchant),
) -> dict:
    """Get the Stripe Customer Portal URL."""
    billing = StripeBillingService(get_supabase_service())
    url = billing.create_portal_session(
        merchant_id=merchant["id"],
        return_url=f"{settings.APP_URL}/dashboard/settings",
    )
    return {"portal_url": url}


@router.get("/usage")
async def get_usage(
    merchant: dict = Depends(get_current_merchant),
) -> dict:
    """Get current usage for all resource types."""
    billing = StripeBillingService(get_supabase_service())
    today = date.today()
    period_start = today.replace(day=1)
    from datetime import timedelta
    period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    usage = billing.get_current_usage(merchant["id"])

    return {
        "plan": merchant.get("plan", "free"),
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "usage": usage,
    }
