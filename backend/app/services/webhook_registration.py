"""Register Shopify webhooks after OAuth install."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from app.config import settings

if TYPE_CHECKING:
    from app.services.shopify import ShopifyClient

logger = structlog.get_logger()

WEBHOOK_TOPICS = [
    "APP_UNINSTALLED",
    "CUSTOMERS_DATA_REQUEST",
    "CUSTOMERS_REDACT",
    "SHOP_REDACT",
    "PRODUCTS_CREATE",
    "PRODUCTS_UPDATE",
    "THEMES_UPDATE",
    "APP_SUBSCRIPTIONS_UPDATE",
]

REGISTER_WEBHOOK_MUTATION = """
mutation RegisterWebhook($topic: WebhookSubscriptionTopic!, $url: URL!) {
    webhookSubscriptionCreate(
        topic: $topic,
        webhookSubscription: { callbackUrl: $url, format: JSON }
    ) {
        webhookSubscription { id }
        userErrors { field message }
    }
}
"""


async def register_webhooks(shopify: ShopifyClient) -> None:
    """Register all required webhooks after OAuth installation."""
    callback_url = f"{settings.BACKEND_URL}/api/v1/webhooks/shopify"

    for topic in WEBHOOK_TOPICS:
        try:
            result = await shopify.graphql(
                REGISTER_WEBHOOK_MUTATION,
                {"topic": topic, "url": callback_url},
            )

            errors = result.get("webhookSubscriptionCreate", {}).get("userErrors", [])
            if errors:
                logger.warning("webhook_registration_error", topic=topic, errors=errors)
            else:
                logger.info("webhook_registered", topic=topic)

        except Exception as exc:
            # Don't block installation for a webhook registration failure
            logger.error("webhook_registration_failed", topic=topic, error=str(exc))
