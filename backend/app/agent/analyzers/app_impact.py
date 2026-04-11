"""App Impact Scanner — Feature #4: impact of each app on load time."""

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
                app {
                    id
                    title
                    handle
                    developerName
                }
                accessScopes { handle }
            }
        }
    }
}
"""

SCRIPT_TAGS_QUERY = """
query {
    scriptTags(first: 100) {
        edges {
            node {
                id
                src
                displayScope
            }
        }
    }
}
"""


class AppImpactScanner(BaseScanner):
    """Measure the performance impact of each installed app.

    Correlates script tags with installed apps to estimate per-app
    impact on page load time.
    """

    name = "app_impact"
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
        apps = []
        for edge in apps_data["appInstallations"]["edges"]:
            node = edge["node"]
            apps.append({
                "id": node["app"]["id"],
                "title": node["app"]["title"],
                "handle": node["app"].get("handle", ""),
                "developer": node["app"].get("developerName", ""),
                "scopes": [s["handle"] for s in node.get("accessScopes", [])],
            })

        # Fetch script tags
        scripts_data = await shopify.graphql(SCRIPT_TAGS_QUERY)
        script_tags = [
            edge["node"] for edge in scripts_data["scriptTags"]["edges"]
        ]

        # Map scripts to apps by domain heuristic
        app_scripts: dict[str, list[dict]] = {}
        unattributed_scripts: list[dict] = []

        for script in script_tags:
            src = script["src"].lower()
            matched = False
            for app in apps:
                handle = app["handle"].lower()
                title_slug = app["title"].lower().replace(" ", "")
                if handle and (handle in src or title_slug in src):
                    app_scripts.setdefault(app["title"], []).append(script)
                    matched = True
                    break
            if not matched:
                unattributed_scripts.append(script)

        # Estimate impact per app
        total_impact_ms = 0
        app_impacts: list[dict] = []

        for app in apps:
            scripts = app_scripts.get(app["title"], [])
            scripts_count = len(scripts)
            # Estimate: each script adds ~200-400ms depending on scope
            estimated_ms = scripts_count * 300
            has_write_scopes = any(
                s.startswith("write_") for s in app["scopes"]
            )
            if has_write_scopes:
                estimated_ms += 100  # write-scope apps tend to inject more

            total_impact_ms += estimated_ms

            app_impacts.append({
                "app_title": app["title"],
                "app_handle": app["handle"],
                "scripts_count": scripts_count,
                "estimated_impact_ms": estimated_ms,
            })

            # Flag heavy apps
            if estimated_ms > 500:
                severity = "critical" if estimated_ms > 1000 else "major"
                issues.append(ScanIssue(
                    module="health",
                    scanner=self.name,
                    severity=severity,
                    title=f"App '{app['title']}' adds ~{estimated_ms}ms load time",
                    description=(
                        f"App '{app['title']}' by {app['developer']} injects "
                        f"{scripts_count} script(s). Estimated impact: {estimated_ms}ms."
                    ),
                    impact=f"+{estimated_ms / 1000:.1f}s load time",
                    impact_value=estimated_ms / 1000,
                    impact_unit="seconds",
                    fix_type="manual",
                    fix_description=(
                        f"Consider replacing '{app['title']}' with a lighter alternative "
                        f"or removing it if not essential."
                    ),
                    context={
                        "app_title": app["title"],
                        "app_handle": app["handle"],
                        "scripts_count": scripts_count,
                        "impact_ms": estimated_ms,
                    },
                ))

        # Unattributed scripts warning
        if unattributed_scripts:
            issues.append(ScanIssue(
                module="health",
                scanner=self.name,
                severity="minor",
                title=f"{len(unattributed_scripts)} unattributed script(s) detected",
                description=(
                    f"Found {len(unattributed_scripts)} scripts that don't match "
                    f"any installed app. These may be residual code."
                ),
                impact=f"~{len(unattributed_scripts) * 200}ms estimated impact",
                impact_value=len(unattributed_scripts) * 0.2,
                impact_unit="seconds",
                fix_type="developer",
                fix_description="Inspect unattributed scripts and remove unused ones",
                context={
                    "scripts": [s["src"] for s in unattributed_scripts],
                },
            ))

        logger.info(
            "app_impact_scan_complete",
            store_id=store_id,
            apps_count=len(apps),
            total_impact_ms=total_impact_ms,
            issues_count=len(issues),
        )

        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={
                "apps_count": len(apps),
                "total_scripts": len(script_tags),
                "total_impact_ms": total_impact_ms,
                "app_impacts": app_impacts,
            },
        )
