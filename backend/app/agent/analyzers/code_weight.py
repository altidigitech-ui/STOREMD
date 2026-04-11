"""Code Weight Scanner — Feature #18: JS/CSS weight by source."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from app.agent.analyzers.base import BaseScanner, ScannerResult
from app.models.scan import ScanIssue

if TYPE_CHECKING:
    from app.services.shopify import ShopifyClient

logger = structlog.get_logger()

THEME_FILES_QUERY = """
query ThemeFiles($themeId: ID!) {
    theme(id: $themeId) {
        files(first: 250) {
            edges {
                node {
                    filename
                    contentType
                    size
                }
            }
        }
    }
}
"""

THEME_ID_QUERY = """
query {
    themes(first: 1, roles: MAIN) {
        edges {
            node { id name }
        }
    }
}
"""


class CodeWeightScanner(BaseScanner):
    """Analyze JS/CSS weight by source in the store theme.

    Examines theme files to identify heavy assets and total
    code weight that impacts page load time.
    """

    name = "code_weight"
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

        # Get main theme ID
        theme_data = await shopify.graphql(THEME_ID_QUERY)
        themes = theme_data["themes"]["edges"]
        if not themes:
            return ScannerResult(
                scanner_name=self.name,
                issues=[],
                metrics={"error": "no_main_theme"},
            )

        theme_id = themes[0]["node"]["id"]
        theme_name = themes[0]["node"]["name"]

        # Fetch theme files
        files_data = await shopify.graphql(THEME_FILES_QUERY, {"themeId": theme_id})
        files = [edge["node"] for edge in files_data["theme"]["files"]["edges"]]

        # Categorize and sum file sizes
        total_js_bytes = 0
        total_css_bytes = 0
        total_liquid_bytes = 0
        heavy_files: list[dict] = []

        for f in files:
            filename = f["filename"]
            size = f.get("size") or 0
            content_type = f.get("contentType", "")

            if "javascript" in content_type or filename.endswith(".js"):
                total_js_bytes += size
                if size > 50_000:  # > 50KB
                    heavy_files.append({
                        "filename": filename,
                        "size_kb": round(size / 1024, 1),
                        "type": "js",
                    })
            elif "css" in content_type or filename.endswith(".css"):
                total_css_bytes += size
                if size > 30_000:  # > 30KB
                    heavy_files.append({
                        "filename": filename,
                        "size_kb": round(size / 1024, 1),
                        "type": "css",
                    })
            elif filename.endswith(".liquid"):
                total_liquid_bytes += size

        total_js_kb = round(total_js_bytes / 1024, 1)
        total_css_kb = round(total_css_bytes / 1024, 1)

        # Flag excessive JS
        if total_js_kb > 500:
            severity = "critical" if total_js_kb > 1000 else "major"
            issues.append(ScanIssue(
                module="health",
                scanner=self.name,
                severity=severity,
                title=f"Heavy JavaScript: {total_js_kb}KB total in theme",
                description=(
                    f"Your theme '{theme_name}' contains {total_js_kb}KB of JavaScript. "
                    f"Recommended maximum is 500KB for good mobile performance."
                ),
                impact=f"~{total_js_kb / 200:.1f}s estimated load impact",
                impact_value=total_js_kb / 200,
                impact_unit="seconds",
                fix_type="developer",
                fix_description="Audit and minify JavaScript files, remove unused code",
                context={
                    "total_js_kb": total_js_kb,
                    "heavy_files": [f for f in heavy_files if f["type"] == "js"],
                },
            ))

        # Flag excessive CSS
        if total_css_kb > 200:
            issues.append(ScanIssue(
                module="health",
                scanner=self.name,
                severity="minor",
                title=f"Heavy CSS: {total_css_kb}KB total in theme",
                description=(
                    f"Your theme contains {total_css_kb}KB of CSS. "
                    f"Consider removing unused styles."
                ),
                impact="Slow first paint on mobile",
                impact_value=total_css_kb / 300,
                impact_unit="seconds",
                fix_type="developer",
                fix_description="Remove unused CSS and consolidate stylesheets",
                context={
                    "total_css_kb": total_css_kb,
                    "heavy_files": [f for f in heavy_files if f["type"] == "css"],
                },
            ))

        # Flag individual heavy files
        for hf in heavy_files:
            if hf["size_kb"] > 200:
                issues.append(ScanIssue(
                    module="health",
                    scanner=self.name,
                    severity="major",
                    title=f"Heavy file: {hf['filename']} ({hf['size_kb']}KB)",
                    description=(
                        f"File '{hf['filename']}' is {hf['size_kb']}KB. "
                        f"Consider splitting, minifying, or lazy-loading."
                    ),
                    impact=f"+{hf['size_kb'] / 200:.1f}s load time",
                    impact_value=hf["size_kb"] / 200,
                    impact_unit="seconds",
                    fix_type="developer",
                    fix_description=f"Minify or split {hf['filename']}",
                    context=hf,
                ))

        logger.info(
            "code_weight_scan_complete",
            store_id=store_id,
            total_js_kb=total_js_kb,
            total_css_kb=total_css_kb,
            heavy_files=len(heavy_files),
        )

        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={
                "total_js_kb": total_js_kb,
                "total_css_kb": total_css_kb,
                "total_liquid_bytes": total_liquid_bytes,
                "theme_files_count": len(files),
                "heavy_files_count": len(heavy_files),
                "theme_name": theme_name,
            },
        )
