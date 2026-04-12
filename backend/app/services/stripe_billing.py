"""Stripe Billing service — checkout, portal, plan checking, usage metering."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import stripe
import structlog

from app.config import settings
from app.core.exceptions import BillingError, ErrorCode

logger = structlog.get_logger()

stripe.api_key = settings.STRIPE_SECRET_KEY

STRIPE_PRICE_IDS: dict[str, str] = {
    "starter": settings.STRIPE_PRICE_STARTER,
    "pro": settings.STRIPE_PRICE_PRO,
    "agency": settings.STRIPE_PRICE_AGENCY,
}

PLAN_HIERARCHY: dict[str, int] = {
    "free": 0,
    "starter": 1,
    "pro": 2,
    "agency": 3,
}

USAGE_LIMITS: dict[str, dict[str, int]] = {
    "scan": {"free": 3, "starter": 5, "pro": 31, "agency": 310},
    "listing_analysis": {"free": 5, "starter": 100, "pro": 1000, "agency": 999999},
    "browser_test": {"free": 0, "starter": 0, "pro": 31, "agency": 310},
    "one_click_fix": {"free": 0, "starter": 20, "pro": 100, "agency": 999999},
    "bulk_operation": {"free": 0, "starter": 0, "pro": 10, "agency": 999999},
}

FEATURE_PLAN_REQUIREMENTS: dict[str, str] = {
    "health_score": "free",
    "diagnostic_3_layers": "free",
    "app_impact_scanner": "starter",
    "residue_detector": "starter",
    "ghost_billing": "starter",
    "code_weight": "starter",
    "security_monitor": "starter",
    "pixel_health": "starter",
    "listing_analyzer": "free",
    "agentic_readiness": "starter",
    "visual_store_test": "pro",
    "real_user_simulation": "pro",
    "accessibility_live": "pro",
    "bot_traffic": "pro",
    "benchmark": "pro",
    "email_health": "pro",
    "ai_crawler_monitor": "pro",
}


class StripeBillingService:
    """Stripe billing operations — checkout, portal, plan access, usage."""

    def __init__(self, supabase) -> None:
        self.supabase = supabase

    # ─── CHECKOUT ───

    def create_checkout_session(
        self, merchant_id: str, plan: str, return_url: str
    ) -> str:
        """Create a Stripe Checkout session. Returns the checkout URL."""
        if plan not in STRIPE_PRICE_IDS:
            raise BillingError(
                code=ErrorCode.STRIPE_CHECKOUT_FAILED,
                message=f"Invalid plan: {plan}",
                status_code=400,
            )

        customer_id = self.get_or_create_customer(merchant_id)

        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                mode="subscription",
                line_items=[{"price": STRIPE_PRICE_IDS[plan], "quantity": 1}],
                success_url=f"{return_url}?session_id={{CHECKOUT_SESSION_ID}}&status=success",
                cancel_url=f"{return_url}?status=canceled",
                subscription_data={
                    "metadata": {"merchant_id": merchant_id, "plan": plan},
                },
                allow_promotion_codes=True,
            )
            logger.info("checkout_created", merchant_id=merchant_id, plan=plan)
            return session.url
        except stripe.StripeError as exc:
            raise BillingError(
                code=ErrorCode.STRIPE_CHECKOUT_FAILED,
                message=f"Checkout failed: {exc}",
                status_code=502,
            ) from exc

    # ─── CUSTOMER PORTAL ───

    def create_portal_session(self, merchant_id: str, return_url: str) -> str:
        """Create a Stripe Customer Portal session."""
        merchant = self._get_merchant(merchant_id)

        if not merchant.get("stripe_customer_id"):
            raise BillingError(
                code=ErrorCode.STRIPE_CUSTOMER_NOT_FOUND,
                message="No Stripe customer found",
                status_code=404,
            )

        try:
            session = stripe.billing_portal.Session.create(
                customer=merchant["stripe_customer_id"],
                return_url=return_url,
            )
            return session.url
        except stripe.StripeError as exc:
            raise BillingError(
                code=ErrorCode.STRIPE_PORTAL_FAILED,
                message=f"Portal failed: {exc}",
                status_code=502,
            ) from exc

    # ─── CUSTOMER MANAGEMENT ───

    def get_or_create_customer(self, merchant_id: str) -> str:
        """Get or create a Stripe customer for the merchant."""
        merchant = self._get_merchant(merchant_id)

        if merchant.get("stripe_customer_id"):
            return merchant["stripe_customer_id"]

        customer = stripe.Customer.create(
            email=merchant["email"],
            metadata={"merchant_id": merchant_id},
        )

        self.supabase.table("merchants").update(
            {"stripe_customer_id": customer.id}
        ).eq("id", merchant_id).execute()

        return customer.id

    # ─── PLAN CHECKING ───

    def check_plan_access(self, merchant_id: str, feature: str) -> bool:
        """Check if the merchant's plan grants access to a feature."""
        required_plan = FEATURE_PLAN_REQUIREMENTS.get(feature, "pro")
        merchant = self._get_merchant(merchant_id)
        current_plan = merchant.get("plan", "free")
        return PLAN_HIERARCHY.get(current_plan, 0) >= PLAN_HIERARCHY.get(required_plan, 0)

    # ─── USAGE METERING ───

    def increment_usage(
        self, merchant_id: str, store_id: str, usage_type: str
    ) -> dict:
        """Increment usage counter and check against limits."""
        today = date.today()
        period_start = today.replace(day=1)
        period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        limit_count = self.get_usage_limit(merchant_id, usage_type)

        # Try to get existing record
        existing = (
            self.supabase.table("usage_records")
            .select("*")
            .eq("merchant_id", merchant_id)
            .eq("store_id", store_id)
            .eq("usage_type", usage_type)
            .eq("period_start", period_start.isoformat())
            .maybe_single()
            .execute()
        )

        if existing.data:
            new_count = existing.data["count"] + 1
            self.supabase.table("usage_records").update(
                {"count": new_count}
            ).eq("id", existing.data["id"]).execute()
        else:
            new_count = 1
            self.supabase.table("usage_records").insert({
                "merchant_id": merchant_id,
                "store_id": store_id,
                "usage_type": usage_type,
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "count": 1,
                "limit_count": limit_count,
            }).execute()

        return {
            "count": new_count,
            "limit": limit_count,
            "remaining": max(0, limit_count - new_count),
            "exceeded": new_count > limit_count,
        }

    def get_usage_limit(self, merchant_id: str, usage_type: str) -> int:
        """Return the usage limit for a merchant's plan."""
        merchant = self._get_merchant(merchant_id)
        plan = merchant.get("plan", "free")
        return USAGE_LIMITS.get(usage_type, {}).get(plan, 0)

    def get_current_usage(self, merchant_id: str) -> list[dict]:
        """Get all usage records for the current billing period."""
        today = date.today()
        period_start = today.replace(day=1)
        merchant = self._get_merchant(merchant_id)
        plan = merchant.get("plan", "free")

        records = (
            self.supabase.table("usage_records")
            .select("*")
            .eq("merchant_id", merchant_id)
            .eq("period_start", period_start.isoformat())
            .execute()
        )

        # Build usage by type
        usage_by_type = {r["usage_type"]: r["count"] for r in (records.data or [])}
        result = []
        for usage_type, limits in USAGE_LIMITS.items():
            limit = limits.get(plan, 0)
            count = usage_by_type.get(usage_type, 0)
            result.append({
                "type": usage_type,
                "count": count,
                "limit": limit,
                "remaining": max(0, limit - count),
            })
        return result

    # ─── CANCEL ───

    def cancel_subscription(self, merchant_id: str) -> None:
        """Cancel subscription immediately (used on app uninstall)."""
        merchant = self._get_merchant(merchant_id)
        sub_id = merchant.get("stripe_subscription_id")

        if sub_id:
            try:
                stripe.Subscription.cancel(sub_id)
                logger.info("subscription_canceled", merchant_id=merchant_id)
            except stripe.StripeError as exc:
                logger.error(
                    "subscription_cancel_failed",
                    merchant_id=merchant_id,
                    error=str(exc),
                )

        self.supabase.table("merchants").update(
            {"plan": "free", "stripe_subscription_id": None}
        ).eq("id", merchant_id).execute()

    # ─── HELPERS ───

    def _get_merchant(self, merchant_id: str) -> dict:
        result = (
            self.supabase.table("merchants")
            .select("id, email, plan, stripe_customer_id, stripe_subscription_id")
            .eq("id", merchant_id)
            .single()
            .execute()
        )
        return result.data
