"""Shopify Billing API service — appSubscriptionCreate, query, cancel.

Parallel to Stripe. Used for merchants that install through the
Shopify App Store. Merchants coming from the direct website
(storemd.vercel.app) continue to use Stripe.
"""

from __future__ import annotations

import httpx
import structlog

from app.config import settings
from app.core.exceptions import BillingError, ErrorCode

logger = structlog.get_logger()


SHOPIFY_PLAN_PRICES: dict[str, float] = {
    "starter": 29.0,
    "pro": 79.0,
    "agency": 199.0,
}

PLAN_DISPLAY_NAMES: dict[str, str] = {
    "starter": "StoreMD Starter",
    "pro": "StoreMD Pro",
    "agency": "StoreMD Agency",
}


class ShopifyBillingService:
    """Async client for the Shopify Billing API via Admin GraphQL."""

    def __init__(self, shop_domain: str, access_token: str) -> None:
        self.shop_domain = shop_domain
        self.access_token = access_token
        self.api_version = settings.SHOPIFY_API_VERSION
        self.endpoint = (
            f"https://{shop_domain}/admin/api/{self.api_version}/graphql.json"
        )

    @property
    def headers(self) -> dict[str, str]:
        return {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
        }

    @property
    def is_test_mode(self) -> bool:
        """In dev / staging we create test subscriptions (no real charge)."""
        return not settings.is_production

    async def _graphql(self, query: str, variables: dict) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.endpoint,
                json={"query": query, "variables": variables},
                headers=self.headers,
            )
            if response.status_code != 200:
                raise BillingError(
                    code=ErrorCode.SHOPIFY_BILLING_FAILED,
                    message=(
                        "Shopify Billing API error: "
                        f"HTTP {response.status_code}"
                    ),
                    status_code=502,
                    context={"shop": self.shop_domain},
                )
            data = response.json()
            if "errors" in data:
                raise BillingError(
                    code=ErrorCode.SHOPIFY_BILLING_FAILED,
                    message=f"Shopify Billing GraphQL error: {data['errors']}",
                    status_code=502,
                    context={"shop": self.shop_domain},
                )
            return data["data"]

    # ─── CREATE ───

    async def create_subscription(
        self,
        plan: str,
        return_url: str,
    ) -> dict:
        """Create an app subscription.

        Returns {"confirmation_url": str, "subscription_id": str}.
        The merchant must visit confirmation_url to approve the charge.
        """
        if plan not in SHOPIFY_PLAN_PRICES:
            raise BillingError(
                code=ErrorCode.SHOPIFY_BILLING_FAILED,
                message=f"Invalid plan: {plan}",
                status_code=400,
            )

        query = """
        mutation appSubscriptionCreate(
          $name: String!,
          $lineItems: [AppSubscriptionLineItemInput!]!,
          $returnUrl: URL!,
          $test: Boolean
        ) {
          appSubscriptionCreate(
            name: $name,
            lineItems: $lineItems,
            returnUrl: $returnUrl,
            test: $test
          ) {
            appSubscription { id status }
            confirmationUrl
            userErrors { field message }
          }
        }
        """
        variables = {
            "name": PLAN_DISPLAY_NAMES[plan],
            "returnUrl": return_url,
            "test": self.is_test_mode,
            "lineItems": [
                {
                    "plan": {
                        "appRecurringPricingDetails": {
                            "price": {
                                "amount": SHOPIFY_PLAN_PRICES[plan],
                                "currencyCode": "USD",
                            },
                            "interval": "EVERY_30_DAYS",
                        }
                    }
                }
            ],
        }

        data = await self._graphql(query, variables)
        result = data.get("appSubscriptionCreate") or {}
        user_errors = result.get("userErrors") or []
        if user_errors:
            raise BillingError(
                code=ErrorCode.SHOPIFY_BILLING_FAILED,
                message=f"Shopify Billing rejected: {user_errors}",
                status_code=400,
                context={"shop": self.shop_domain, "plan": plan},
            )

        confirmation_url = result.get("confirmationUrl")
        subscription = result.get("appSubscription") or {}
        if not confirmation_url or not subscription.get("id"):
            raise BillingError(
                code=ErrorCode.SHOPIFY_BILLING_FAILED,
                message="Shopify Billing missing confirmation URL",
                status_code=502,
                context={"shop": self.shop_domain},
            )

        logger.info(
            "shopify_subscription_created",
            shop=self.shop_domain,
            plan=plan,
            subscription_id=subscription["id"],
            test=self.is_test_mode,
        )

        return {
            "confirmation_url": confirmation_url,
            "subscription_id": subscription["id"],
            "status": subscription.get("status"),
        }

    # ─── QUERY ───

    async def get_active_subscription(self) -> dict | None:
        """Return the currently active app subscription, or None."""
        query = """
        query {
          currentAppInstallation {
            activeSubscriptions {
              id
              name
              status
              test
              lineItems {
                plan {
                  pricingDetails {
                    __typename
                    ... on AppRecurringPricing {
                      price { amount currencyCode }
                      interval
                    }
                  }
                }
              }
            }
          }
        }
        """
        data = await self._graphql(query, {})
        installation = data.get("currentAppInstallation") or {}
        subs = installation.get("activeSubscriptions") or []
        if not subs:
            return None
        return subs[0]

    # ─── CANCEL ───

    async def cancel_subscription(self, subscription_id: str) -> None:
        """Cancel the given app subscription."""
        query = """
        mutation appSubscriptionCancel($id: ID!) {
          appSubscriptionCancel(id: $id) {
            appSubscription { id status }
            userErrors { field message }
          }
        }
        """
        data = await self._graphql(query, {"id": subscription_id})
        result = data.get("appSubscriptionCancel") or {}
        user_errors = result.get("userErrors") or []
        if user_errors:
            raise BillingError(
                code=ErrorCode.SHOPIFY_BILLING_FAILED,
                message=f"Shopify subscription cancel failed: {user_errors}",
                status_code=502,
                context={
                    "shop": self.shop_domain,
                    "subscription_id": subscription_id,
                },
            )
        logger.info(
            "shopify_subscription_canceled",
            shop=self.shop_domain,
            subscription_id=subscription_id,
        )


def plan_from_subscription_name(name: str | None) -> str:
    """Infer the plan key ('starter'|'pro'|'agency') from the subscription name."""
    if not name:
        return "free"
    lower = name.lower()
    for key in ("agency", "pro", "starter"):
        if key in lower:
            return key
    return "free"
