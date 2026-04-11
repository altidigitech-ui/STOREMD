"""Residue Detector — Feature #14: dead code from uninstalled apps."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from app.agent.analyzers.base import BaseScanner, ScannerResult
from app.models.scan import ScanIssue

if TYPE_CHECKING:
    from app.services.shopify import ShopifyClient

logger = structlog.get_logger()

APPS_QUERY = """
query {
    appInstallations(first: 50) {
        edges {
            node {
                app { title handle }
            }
        }
    }
}
"""

SCRIPT_TAGS_QUERY = """
query {
    scriptTags(first: 100) {
        edges {
            node { id src displayScope }
        }
    }
}
"""

# Known third-party script domains and their associated apps
KNOWN_APP_DOMAINS: dict[str, str] = {
    "privy.com": "Privy",
    "klaviyo.com": "Klaviyo",
    "judge.me": "Judge.me",
    "loox.io": "Loox",
    "stamped.io": "Stamped",
    "yotpo.com": "Yotpo",
    "omnisend.com": "Omnisend",
    "mailchimp.com": "Mailchimp",
    "tidio.co": "Tidio",
    "zendesk.com": "Zendesk",
    "tawk.to": "Tawk.to",
    "hotjar.com": "Hotjar",
    "pushowl.com": "PushOwl",
    "bold.co": "Bold",
    "recharge.com": "Recharge",
}


class ResidueDetector(BaseScanner):
    """Detect residual code from uninstalled apps.

    Compares scriptTags against installed apps to find scripts
    that belong to apps no longer installed.
    """

    name = "residue_detector"
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

        # Fetch installed apps
        apps_data = await shopify.graphql(APPS_QUERY)
        installed_handles = set()
        installed_titles = set()
        for edge in apps_data["appInstallations"]["edges"]:
            app = edge["node"]["app"]
            if app.get("handle"):
                installed_handles.add(app["handle"].lower())
            installed_titles.add(app["title"].lower())

        # Fetch script tags
        scripts_data = await shopify.graphql(SCRIPT_TAGS_QUERY)
        script_tags = [edge["node"] for edge in scripts_data["scriptTags"]["edges"]]

        residual_scripts: list[dict] = []

        for script in script_tags:
            src = script["src"].lower()

            # Check against known app domains
            for domain, app_name in KNOWN_APP_DOMAINS.items():
                if domain in src:
                    # Script belongs to a known app — is it installed?
                    app_lower = app_name.lower()
                    if (
                        app_lower not in installed_titles
                        and app_lower.replace(" ", "") not in installed_handles
                        and app_lower.replace(".", "") not in installed_handles
                    ):
                        residual_scripts.append({
                            "src": script["src"],
                            "script_id": script["id"],
                            "attributed_app": app_name,
                        })
                    break

        # Create issues for residual scripts
        for residual in residual_scripts:
            issues.append(ScanIssue(
                module="health",
                scanner=self.name,
                severity="major",
                title=f"Residual script from uninstalled app: {residual['attributed_app']}",
                description=(
                    f"Script '{residual['src']}' belongs to '{residual['attributed_app']}' "
                    f"which is no longer installed. This dead code still loads on every page."
                ),
                impact="+200-400ms load time per page",
                impact_value=0.3,
                impact_unit="seconds",
                fix_type="one_click",
                fix_description=f"Remove residual script from {residual['attributed_app']}",
                auto_fixable=True,
                context={
                    "script_src": residual["src"],
                    "script_id": residual["script_id"],
                    "app_name": residual["attributed_app"],
                },
            ))

        logger.info(
            "residue_scan_complete",
            store_id=store_id,
            total_scripts=len(script_tags),
            residual_found=len(residual_scripts),
        )

        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={
                "total_scripts": len(script_tags),
                "residual_scripts": len(residual_scripts),
                "installed_apps": len(installed_titles),
            },
        )
