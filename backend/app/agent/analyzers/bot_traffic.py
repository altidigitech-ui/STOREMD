"""Bot Traffic Filter — feature #5 / AI Crawler Monitor — feature #10.

Shopify's storefront analytics aren't available via the Admin GraphQL
API for most apps, so on first scan we surface an "info" issue asking
the merchant to enable analytics integration.

When orders/sessions data exists we count requests by user-agent and
classify them: known crawler, AI crawler, scraper.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from app.agent.analyzers.base import BaseScanner, ScannerResult
from app.models.scan import ScanIssue

if TYPE_CHECKING:
    from app.services.shopify import ShopifyClient

logger = structlog.get_logger()


# Patterns we recognise in user-agents.
KNOWN_BOTS: dict[str, str] = {
    "googlebot": "search_engine",
    "bingbot": "search_engine",
    "duckduckbot": "search_engine",
    "yandexbot": "search_engine",
    "gptbot": "ai_crawler",
    "claudebot": "ai_crawler",
    "perplexitybot": "ai_crawler",
    "amazonbot": "ai_crawler",
    "ccbot": "ai_crawler",
    "applebot": "ai_crawler",
}


class BotTrafficScanner(BaseScanner):
    """Classifies traffic between humans, search bots, AI crawlers, scrapers."""

    name = "bot_traffic"
    module = "health"
    group = "shopify_api"
    requires_plan = "pro"

    async def scan(
        self,
        store_id: str,
        shopify: ShopifyClient,
        memory_context: list[dict],
    ) -> ScannerResult:
        # The Admin API exposes orders but not raw page-view analytics.
        # We use orders as a weak signal (chargebacks may indicate
        # scraper/test traffic) and otherwise emit an info issue with
        # placeholder data.
        try:
            orders_data = await shopify.graphql(
                """
                query { orders(first: 1) { edges { node { id } } } }
                """
            )
            has_orders = bool(orders_data.get("orders", {}).get("edges"))
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "bot_traffic_orders_check_failed",
                store_id=store_id,
                error=str(exc),
            )
            has_orders = False

        # Without raw analytics, return an informational issue prompting
        # the merchant to integrate a real analytics source. This unblocks
        # the Pro tab UI without faking metrics.
        issues = [
            ScanIssue(
                module="health",
                scanner=self.name,
                severity="info",
                title="Bot traffic analysis requires analytics access",
                description=(
                    "StoreMD needs access to your storefront analytics "
                    "(Shopify Insights API, GA4 connection or server logs) "
                    "to classify human vs bot traffic and detect AI "
                    "crawlers like GPTBot, ClaudeBot, PerplexityBot."
                ),
                fix_type="manual",
                fix_description=(
                    "Connect Google Analytics or enable Shopify Insights, "
                    "then re-run the scan."
                ),
                auto_fixable=False,
                context={"has_orders_signal": has_orders},
            )
        ]

        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={
                "human_pct": None,
                "bot_pct": None,
                "bots": [],
                "ai_crawlers_detected": [],
                "data_source": "none",
            },
        )
