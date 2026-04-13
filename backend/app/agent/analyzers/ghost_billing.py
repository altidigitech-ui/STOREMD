"""Ghost Billing Detector — Feature #19: apps billing after uninstall."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from app.agent.analyzers.base import BaseScanner, ScannerResult
from app.models.scan import ScanIssue

if TYPE_CHECKING:
    from app.services.shopify import ShopifyClient

logger = structlog.get_logger()

FETCH_APPS_QUERY = """
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

    Compares Shopify recurring_application_charges (REST) against
    the installed apps list (GraphQL) to find ghost charges.
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
        # 1. Fetch active charges (REST endpoint).
        # recurring_application_charges requires a scope our public app
        # doesn't currently hold. Surface this as an info issue rather
        # than tanking the whole scan.
        try:
            charges_data = await shopify.rest_get("recurring_application_charges")
        except Exception as exc:  # noqa: BLE001
            logger.warning("ghost_billing_scope_unavailable", error=str(exc))
            return ScannerResult(
                scanner_name=self.name,
                issues=[ScanIssue(
                    module="health",
                    scanner=self.name,
                    severity="info",
                    title="Ghost billing check requires additional permissions",
                    description=(
                        "StoreMD needs the read_all_orders permission to detect "
                        "apps still billing after uninstall. Re-install StoreMD "
                        "to grant this permission."
                    ),
                    fix_type="manual",
                    fix_description="Re-install StoreMD from the Shopify App Store",
                    auto_fixable=False,
                )],
                metrics={"skipped": "missing_scope", "error": str(exc)},
            )

        active_charges = [
            c for c in charges_data.get("recurring_application_charges", [])
            if c["status"] == "active"
        ]

        # 2. Fetch installed apps (GraphQL). Same access constraint as
        # health_scorer — degrade if Shopify denies the scope.
        try:
            apps_data = await shopify.graphql(FETCH_APPS_QUERY)
            installed_app_names = {
                edge["node"]["app"]["title"]
                for edge in apps_data["appInstallations"]["edges"]
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("ghost_billing_apps_unavailable", error=str(exc))
            return ScannerResult(
                scanner_name=self.name,
                issues=[],
                metrics={"skipped": "missing_apps_scope", "error": str(exc)},
            )

        # 3. Compare: charges without a matching installed app = ghost
        issues: list[ScanIssue] = []
        for charge in active_charges:
            if charge["name"] not in installed_app_names:
                amount = float(charge["price"])
                severity = "critical" if amount >= 50 else "major"

                issues.append(ScanIssue(
                    module="health",
                    scanner=self.name,
                    severity=severity,
                    title=f"Ghost billing: {charge['name']} (${charge['price']}/month)",
                    description=(
                        f"App '{charge['name']}' is no longer installed but still "
                        f"charging ${charge['price']}/month since "
                        f"{charge['created_at'][:10]}."
                    ),
                    impact=f"${charge['price']}/month lost",
                    impact_value=amount,
                    impact_unit="dollars",
                    fix_type="manual",
                    fix_description=(
                        "Cancel this charge in Shopify Admin -> Settings -> Billing"
                    ),
                    auto_fixable=False,
                    context={
                        "charge_id": charge["id"],
                        "charge_name": charge["name"],
                        "charge_amount": charge["price"],
                        "charge_since": charge["created_at"],
                    },
                ))

        total_ghost_monthly = sum(
            float(i.context["charge_amount"]) for i in issues
        )

        logger.info(
            "ghost_billing_scan_complete",
            store_id=store_id,
            active_charges=len(active_charges),
            ghost_charges=len(issues),
            total_ghost_monthly=total_ghost_monthly,
        )

        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={
                "active_charges": len(active_charges),
                "ghost_charges": len(issues),
                "total_ghost_monthly": total_ghost_monthly,
            },
        )
