"""Health Scorer — Feature #1: composite health score /100."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from app.agent.analyzers.base import BaseScanner, ScannerResult
from app.models.scan import ScanIssue

if TYPE_CHECKING:
    from app.services.shopify import ShopifyClient

logger = structlog.get_logger()

SHOP_QUERY = """
query {
    shop {
        name
        primaryDomain { url host }
        plan { displayName }
        currencyCode
        billingAddress { countryCodeV2 }
    }
    productsCount { count }
}
"""

THEME_QUERY = """
query {
    themes(first: 1, roles: MAIN) {
        edges {
            node { id name role }
        }
    }
}
"""


class HealthScorer(BaseScanner):
    """Compute a composite health score (0-100) for the store.

    Gathers basic shop info, theme data, and apps count to provide
    a baseline score. Detailed sub-scores come from other scanners.
    """

    name = "health_scorer"
    module = "health"
    group = "shopify_api"
    requires_plan = "free"

    async def scan(
        self,
        store_id: str,
        shopify: ShopifyClient,
        memory_context: list[dict],
    ) -> ScannerResult:
        issues: list[ScanIssue] = []

        # Fetch shop info
        shop_data = await shopify.graphql(SHOP_QUERY)
        shop = shop_data["shop"]

        products_count = shop_data["productsCount"]["count"]
        shopify_plan = shop["plan"]["displayName"].lower()

        # Fetch main theme
        theme_data = await shopify.graphql(THEME_QUERY)
        themes = theme_data["themes"]["edges"]
        theme_name = themes[0]["node"]["name"] if themes else "Unknown"

        # Fetch apps count — AppInstallationConnection.totalCount was
        # removed in API 2026-01, so we page through edges.
        apps_count = 0
        cursor: str | None = None
        while True:
            after = f', after: "{cursor}"' if cursor else ""
            apps_data = await shopify.graphql(
                "query { appInstallations(first: 250"
                + after
                + ") { edges { cursor } pageInfo { hasNextPage } } }"
            )
            edges = apps_data["appInstallations"]["edges"]
            apps_count += len(edges)
            page_info = apps_data["appInstallations"]["pageInfo"]
            if not page_info["hasNextPage"] or not edges:
                break
            cursor = edges[-1]["cursor"]

        # --- Rules-based scoring ---
        # App bloat penalty
        app_penalty = 0
        if apps_count > 20:
            app_penalty = 25
            issues.append(ScanIssue(
                module="health", scanner=self.name, severity="critical",
                title=f"App bloat: {apps_count} apps installed",
                description=(
                    f"Your store has {apps_count} apps. The average is 14. "
                    f"Each app adds 200-500ms of load time."
                ),
                impact=f"~{apps_count * 300}ms estimated total app impact",
                impact_value=apps_count * 0.3,
                impact_unit="seconds",
                fix_type="manual",
                fix_description="Audit your apps and remove unused ones",
            ))
        elif apps_count > 14:
            app_penalty = 10
            issues.append(ScanIssue(
                module="health", scanner=self.name, severity="major",
                title=f"Above-average app count: {apps_count} apps",
                description=(
                    f"Your store has {apps_count} apps (average is 14). "
                    f"Consider auditing for redundant apps."
                ),
                impact=f"~{apps_count * 300}ms estimated total app impact",
                impact_value=apps_count * 0.3,
                impact_unit="seconds",
                fix_type="manual",
                fix_description="Review each app's ROI vs performance impact",
            ))

        # Product count factor (stores with more products have more to scan)
        product_factor = min(100, max(50, 100 - (products_count // 100)))

        # Baseline scores (refined by other scanners)
        mobile_score = max(0, product_factor - app_penalty)
        desktop_score = max(0, min(100, product_factor - app_penalty + 15))
        composite = round(mobile_score * 0.6 + desktop_score * 0.4)

        logger.info(
            "health_score_calculated",
            store_id=store_id,
            composite=composite,
            mobile=mobile_score,
            desktop=desktop_score,
            apps=apps_count,
        )

        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={
                "composite_score": composite,
                "mobile_score": mobile_score,
                "desktop_score": desktop_score,
                "apps_count": apps_count,
                "products_count": products_count,
                "shopify_plan": shopify_plan,
                "theme_name": theme_name,
            },
        )
