"""Security Monitor — Feature #9: SSL, security headers, app permissions."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import structlog

from app.agent.analyzers.base import BaseScanner, ScannerResult
from app.models.scan import ScanIssue

if TYPE_CHECKING:
    from app.services.shopify import ShopifyClient

logger = structlog.get_logger()

APPS_WITH_SCOPES_QUERY = """
query {
    appInstallations(first: 50) {
        edges {
            node {
                app { id title handle }
                accessScopes { handle }
            }
        }
    }
}
"""

# Dangerous scope combinations that warrant attention
SENSITIVE_SCOPES = {
    "write_orders",
    "write_customers",
    "write_checkouts",
    "read_all_orders",
    "write_draft_orders",
}

EXPECTED_SECURITY_HEADERS = {
    "x-content-type-options",
    "x-frame-options",
    "strict-transport-security",
}


class SecurityMonitor(BaseScanner):
    """Monitor store security: SSL, headers, app permissions.

    Checks the storefront for security headers and analyzes
    installed app permissions for excessive scopes.
    """

    name = "security_monitor"
    module = "health"
    group = "shopify_api"
    requires_plan = "starter"

    async def scan(
        self,
        store_id: str,
        shopify: ShopifyClient,
        memory_context: list[dict],
    ) -> ScannerResult:
        issues: list[ScanIssue] = []

        # --- 1. Check app permissions ---
        apps_data = await shopify.graphql(APPS_WITH_SCOPES_QUERY)
        apps_with_sensitive: list[dict] = []

        for edge in apps_data["appInstallations"]["edges"]:
            node = edge["node"]
            app_title = node["app"]["title"]
            scopes = {s["handle"] for s in node.get("accessScopes", [])}
            sensitive = scopes & SENSITIVE_SCOPES

            if sensitive:
                apps_with_sensitive.append({
                    "app_title": app_title,
                    "app_handle": node["app"].get("handle", ""),
                    "sensitive_scopes": sorted(sensitive),
                    "all_scopes": sorted(scopes),
                })

        for app_info in apps_with_sensitive:
            scope_list = ", ".join(app_info["sensitive_scopes"])
            issues.append(ScanIssue(
                module="health",
                scanner=self.name,
                severity="minor",
                title=f"App '{app_info['app_title']}' has sensitive permissions",
                description=(
                    f"App '{app_info['app_title']}' has access to: {scope_list}. "
                    f"Verify this app needs these permissions."
                ),
                impact="Potential security risk",
                fix_type="manual",
                fix_description=(
                    f"Review if '{app_info['app_title']}' needs {scope_list} access"
                ),
                context=app_info,
            ))

        # --- 2. Check storefront security headers ---
        missing_headers: list[str] = []
        ssl_ok = True

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.head(
                    f"https://{shopify.shop_domain}",
                )
                response_headers = {k.lower() for k in response.headers.keys()}

                for header in EXPECTED_SECURITY_HEADERS:
                    if header not in response_headers:
                        missing_headers.append(header)

        except httpx.ConnectError:
            ssl_ok = False
        except Exception as exc:
            logger.warning(
                "security_header_check_failed",
                store_id=store_id,
                error=str(exc),
            )

        if not ssl_ok:
            issues.append(ScanIssue(
                module="health",
                scanner=self.name,
                severity="critical",
                title="SSL connection failed",
                description=(
                    f"Could not establish a secure HTTPS connection to "
                    f"{shopify.shop_domain}. SSL may be misconfigured."
                ),
                impact="Browsers show security warning, SEO penalty",
                impact_value=30.0,
                impact_unit="score_points",
                fix_type="manual",
                fix_description="Check SSL certificate in Shopify Admin -> Domains",
            ))

        if missing_headers:
            issues.append(ScanIssue(
                module="health",
                scanner=self.name,
                severity="minor",
                title=f"{len(missing_headers)} security header(s) missing",
                description=(
                    f"Missing headers: {', '.join(missing_headers)}. "
                    f"These headers help protect against common attacks."
                ),
                impact="Reduced security posture",
                fix_type="developer",
                fix_description="Add security headers via Shopify proxy or theme",
                context={"missing_headers": missing_headers},
            ))

        logger.info(
            "security_scan_complete",
            store_id=store_id,
            sensitive_apps=len(apps_with_sensitive),
            missing_headers=len(missing_headers),
            ssl_ok=ssl_ok,
        )

        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={
                "apps_with_sensitive_scopes": len(apps_with_sensitive),
                "missing_security_headers": len(missing_headers),
                "ssl_ok": ssl_ok,
                "total_apps_checked": len(apps_data["appInstallations"]["edges"]),
            },
        )
