"""Ghost Billing Detector — Feature #19: apps billing after uninstall."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from app.agent.analyzers.base import BaseScanner, ScannerResult
from app.models.scan import ScanIssue

if TYPE_CHECKING:
    from app.services.shopify import ShopifyClient

logger = structlog.get_logger()

# Returns app installations WITH their active billing subscriptions.
# Shopify retains AppInstallation records (and active billing) even after the
# merchant uninstalls the app, so this query surfaces charges from apps that
# may no longer be active in the merchant's Shopify Admin.
FETCH_BILLING_QUERY = """
query {
  appInstallations(first: 50) {
    edges {
      node {
        app { id title handle }
        activeSubscriptions {
          id
          name
          status
          createdAt
          lineItems {
            plan {
              pricingDetails {
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
  }
}
"""

# Returns only the currently-installed apps (no billing data).
# Used as the reference set to cross-check against the billing query.
FETCH_INSTALLED_QUERY = """
query {
  appInstallations(first: 50) {
    edges {
      node {
        app { id title handle }
      }
    }
  }
}
"""


class GhostBillingDetector(BaseScanner):
    """Detect apps that are no longer installed but still billing.

    Two GraphQL calls:
      1. FETCH_BILLING_QUERY  → all AppInstallation records with active billing
         (includes apps that were uninstalled but whose subscription persists)
      2. FETCH_INSTALLED_QUERY → apps currently installed in the merchant's admin

    Any app with an active recurring charge that is absent from the installed
    set is a ghost charge.
    """

    name = "ghost_billing"
    module = "health"
    group = "shopify_api"
    requires_plan = "starter"

    async def scan(
        self,
        store_id: str,
        shopify: ShopifyClient,
        memory_context: list[dict],
    ) -> ScannerResult:
        # 1. Fetch all billing subscriptions (includes ghost-billing apps).
        try:
            billing_data = await shopify.graphql(FETCH_BILLING_QUERY)
        except Exception as exc:
            logger.warning(
                "ghost_billing_query_failed",
                store_id=store_id,
                error=str(exc),
            )
            return ScannerResult(
                scanner_name=self.name,
                issues=[],
                metrics={"skipped": "graphql_error", "error": str(exc)},
            )

        # 2. Fetch currently installed apps (the reference set).
        try:
            installed_data = await shopify.graphql(FETCH_INSTALLED_QUERY)
            installed_app_ids = {
                edge["node"]["app"]["id"]
                for edge in installed_data["appInstallations"]["edges"]
            }
        except Exception as exc:
            logger.warning(
                "ghost_billing_installed_query_failed",
                store_id=store_id,
                error=str(exc),
            )
            return ScannerResult(
                scanner_name=self.name,
                issues=[],
                metrics={"skipped": "installed_query_error", "error": str(exc)},
            )

        # 3. Cross-reference: billing apps NOT in the installed set = ghost charges.
        issues: list[ScanIssue] = []
        apps_with_billing = 0

        for edge in billing_data["appInstallations"]["edges"]:
            node = edge["node"]
            app = node["app"]

            for sub in node.get("activeSubscriptions", []):
                if sub.get("status") != "ACTIVE":
                    continue

                monthly_total = _sum_monthly_charge(sub)
                if monthly_total == 0:
                    continue

                apps_with_billing += 1

                if app["id"] in installed_app_ids:
                    continue  # Installed and billing — legitimate charge.

                cancel_url = (
                    f"https://{shopify.shop_domain}"
                    "/admin/settings/billing/subscriptions"
                )
                severity = "critical" if monthly_total >= 50 else "major"
                issues.append(ScanIssue(
                    module="health",
                    scanner=self.name,
                    severity=severity,
                    title=f"Ghost billing: {app['title']} (${monthly_total:.2f}/month)",
                    description=(
                        f"'{app['title']}' is no longer installed but still charging "
                        f"${monthly_total:.2f}/month."
                    ),
                    impact=f"${monthly_total:.2f}/month lost",
                    impact_value=monthly_total,
                    impact_unit="dollars",
                    fix_type="manual",
                    fix_description=(
                        f"Steps to cancel:\n"
                        f"1. Open {cancel_url}\n"
                        f"2. Find \"{app['title']}\" in the subscriptions list\n"
                        f"3. Click \"Cancel subscription\" — saves ${monthly_total:.2f}/month immediately"
                    ),
                    auto_fixable=False,
                    context={
                        "charge_id": sub["id"],
                        "app_id": app["id"],
                        "app_handle": app["handle"],
                        "charge_name": app["title"],
                        "charge_amount": f"{monthly_total:.2f}",
                        "charge_since": sub.get("createdAt", ""),
                        "cancel_url": cancel_url,
                        "shop_domain": shopify.shop_domain,
                    },
                ))

        total_ghost_monthly = sum(float(i.context["charge_amount"]) for i in issues)

        logger.info(
            "ghost_billing_scan_complete",
            store_id=store_id,
            apps_with_billing=apps_with_billing,
            ghost_charges=len(issues),
            total_ghost_monthly=total_ghost_monthly,
        )

        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={
                "apps_with_billing": apps_with_billing,
                "ghost_charges": len(issues),
                "total_ghost_monthly": total_ghost_monthly,
            },
        )


def _sum_monthly_charge(subscription: dict) -> float:
    """Sum EVERY_30_DAYS line item amounts for a subscription."""
    total = 0.0
    for item in subscription.get("lineItems", []):
        pricing = item.get("plan", {}).get("pricingDetails", {})
        if pricing.get("interval") == "EVERY_30_DAYS":
            total += float(pricing.get("price", {}).get("amount", 0))
    return total
