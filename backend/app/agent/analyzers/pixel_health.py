"""Pixel Health Check — Feature #15: GA4, Meta Pixel, TikTok Pixel."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import structlog

from app.agent.analyzers.base import BaseScanner, ScannerResult
from app.models.scan import ScanIssue

if TYPE_CHECKING:
    from app.services.shopify import ShopifyClient

logger = structlog.get_logger()

THEME_ID_QUERY = """
query {
    themes(first: 1, roles: MAIN) {
        edges { node { id name } }
    }
}
"""

THEME_FILES_QUERY = """
query ThemeFiles($themeId: ID!) {
    theme(id: $themeId) {
        files(first: 250) {
            edges {
                node {
                    filename
                    contentType
                    body { ... on OnlineStoreThemeFileBodyText { content } }
                }
            }
        }
    }
}
"""

# Pixel detection patterns
PIXEL_PATTERNS = {
    "ga4": {
        "name": "Google Analytics 4",
        "patterns": [
            re.compile(r"gtag\(", re.IGNORECASE),
            re.compile(r"G-[A-Z0-9]{6,}", re.IGNORECASE),
            re.compile(r"googletagmanager\.com/gtag", re.IGNORECASE),
        ],
    },
    "meta_pixel": {
        "name": "Meta Pixel (Facebook)",
        "patterns": [
            re.compile(r"fbq\(", re.IGNORECASE),
            re.compile(r"connect\.facebook\.net/en_US/fbevents\.js", re.IGNORECASE),
        ],
    },
    "tiktok_pixel": {
        "name": "TikTok Pixel",
        "patterns": [
            re.compile(r"ttq\.", re.IGNORECASE),
            re.compile(r"analytics\.tiktok\.com", re.IGNORECASE),
        ],
    },
}


class PixelHealthScanner(BaseScanner):
    """Check tracking pixel health in the store theme."""

    name = "pixel_health"
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

        # Get main theme
        theme_data = await shopify.graphql(THEME_ID_QUERY)
        themes = theme_data["themes"]["edges"]
        if not themes:
            return ScannerResult(
                scanner_name=self.name,
                issues=[],
                metrics={"error": "no_main_theme"},
            )

        theme_id = themes[0]["node"]["id"]

        # Fetch theme files with content
        files_data = await shopify.graphql(THEME_FILES_QUERY, {"themeId": theme_id})
        files = [e["node"] for e in files_data["theme"]["files"]["edges"]]

        # Concatenate all liquid/HTML content for pixel search
        all_content = ""
        for f in files:
            body = f.get("body")
            if body and isinstance(body, dict):
                content = body.get("content", "")
                if content:
                    all_content += content + "\n"

        # Detect pixels
        detected_pixels: dict[str, int] = {}

        for pixel_key, pixel_info in PIXEL_PATTERNS.items():
            count = 0
            for pattern in pixel_info["patterns"]:
                matches = pattern.findall(all_content)
                count += len(matches)
            if count > 0:
                detected_pixels[pixel_key] = count

        # Report missing pixels
        for pixel_key, pixel_info in PIXEL_PATTERNS.items():
            if pixel_key not in detected_pixels:
                issues.append(ScanIssue(
                    module="health",
                    scanner=self.name,
                    severity="minor",
                    title=f"{pixel_info['name']} not detected",
                    description=(
                        f"No {pixel_info['name']} tracking code found in your theme. "
                        f"This pixel helps track conversions and optimize ads."
                    ),
                    impact="No conversion tracking for this platform",
                    fix_type="manual",
                    fix_description=f"Install {pixel_info['name']} via Shopify Settings or theme",
                    context={"pixel": pixel_key, "status": "missing"},
                ))

        # Report duplicate pixels
        for pixel_key, count in detected_pixels.items():
            if count > 2:  # More than 2 matches suggests duplicates
                pixel_name = PIXEL_PATTERNS[pixel_key]["name"]
                issues.append(ScanIssue(
                    module="health",
                    scanner=self.name,
                    severity="major",
                    title=f"Duplicate {pixel_name} detected ({count} instances)",
                    description=(
                        f"Found {count} instances of {pixel_name} in your theme. "
                        f"Duplicate pixels cause inflated analytics and slower load times."
                    ),
                    impact="Inflated analytics data + extra load time",
                    impact_value=count * 0.1,
                    impact_unit="seconds",
                    fix_type="developer",
                    fix_description=f"Remove duplicate {pixel_name} instances from theme",
                    context={"pixel": pixel_key, "count": count, "status": "duplicate"},
                ))

        logger.info(
            "pixel_health_scan_complete",
            store_id=store_id,
            detected=list(detected_pixels.keys()),
            missing=[k for k in PIXEL_PATTERNS if k not in detected_pixels],
        )

        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={
                "detected_pixels": detected_pixels,
                "missing_pixels": [k for k in PIXEL_PATTERNS if k not in detected_pixels],
                "files_scanned": len(files),
            },
        )
