"""Listing Analyzer — Features #21, #26 (dead listings), #27 (images)."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import structlog

from app.agent.analyzers.base import BaseScanner, ScannerResult
from app.models.scan import ScanIssue

if TYPE_CHECKING:
    from app.services.shopify import ShopifyClient

logger = structlog.get_logger()

# Dead-listing thresholds (#26).
_DEAD_OOS_DAYS = 30  # out of stock for > N days
_DEAD_DRAFT_DAYS = 60  # kept in DRAFT for > N days

# Image quality thresholds (#27).
_MIN_IMAGE_DIM_PX = 800  # below → too small for zoom
_MIN_ALT_TEXT_WORDS = 3

PRODUCTS_QUERY = """
query FetchProducts($first: Int!, $after: String) {
    products(first: $first, after: $after) {
        edges {
            cursor
            node {
                id
                title
                handle
                status
                productType
                descriptionHtml
                createdAt
                updatedAt
                totalInventory
                seo { title description }
                images(first: 10) {
                    edges {
                        node { id altText url width height }
                    }
                }
                variants(first: 10) {
                    edges {
                        node {
                            id
                            title
                            sku
                            barcode
                            price
                            inventoryQuantity
                        }
                    }
                }
            }
        }
        pageInfo { hasNextPage endCursor }
    }
}
"""


class ListingAnalyzer(BaseScanner):
    """Analyze product listing quality: title, description, images, SEO."""

    name = "listing_analyzer"
    module = "listings"
    group = "shopify_api"
    requires_plan = "free"

    async def scan(
        self,
        store_id: str,
        shopify: ShopifyClient,
        memory_context: list[dict],
    ) -> ScannerResult:
        issues: list[ScanIssue] = []

        # Fetch products (paginated, max 100 for free, 1000 for paid)
        products = []
        cursor = None
        max_products = 100  # capped for performance

        while len(products) < max_products:
            batch_size = min(50, max_products - len(products))
            data = await shopify.graphql(
                PRODUCTS_QUERY,
                {"first": batch_size, "after": cursor},
            )
            edges = data["products"]["edges"]
            products.extend([e["node"] for e in edges])

            page_info = data["products"]["pageInfo"]
            if not page_info["hasNextPage"]:
                break
            cursor = page_info["endCursor"]

        # Analyze each product
        scores: list[int] = []
        products_below_50 = 0

        for product in products:
            title_score = self._score_title(product)
            desc_score = self._score_description(product)
            images_score = self._score_images(product)
            seo_score = self._score_seo(product)

            composite = round(
                title_score * 0.25 + desc_score * 0.30
                + images_score * 0.25 + seo_score * 0.20
            )
            scores.append(composite)

            if composite < 50:
                products_below_50 += 1

                weak_elements = []
                if title_score < 50:
                    weak_elements.append(f"title ({title_score}/100)")
                if desc_score < 50:
                    weak_elements.append(f"description ({desc_score}/100)")
                if images_score < 50:
                    weak_elements.append(f"images ({images_score}/100)")
                if seo_score < 50:
                    weak_elements.append(f"SEO ({seo_score}/100)")

                issues.append(ScanIssue(
                    module="listings",
                    scanner=self.name,
                    severity="major" if composite < 30 else "minor",
                    title=f"Low listing score: '{product['title']}' ({composite}/100)",
                    description=(
                        f"Product '{product['title']}' scored {composite}/100. "
                        f"Weak areas: {', '.join(weak_elements)}."
                    ),
                    impact=f"Reduced discoverability and conversion",
                    impact_value=50 - composite,
                    impact_unit="score_points",
                    fix_type="one_click",
                    fix_description="Optimize weak listing elements",
                    auto_fixable=True,
                    context={
                        "shopify_product_id": product["id"],
                        "title": product["title"],
                        "handle": product.get("handle"),
                        "composite_score": composite,
                        "title_score": title_score,
                        "description_score": desc_score,
                        "images_score": images_score,
                        "seo_score": seo_score,
                    },
                ))

        avg_score = round(sum(scores) / len(scores)) if scores else 0

        # Feature #26 — Dead listing detector.
        dead_issues, dead_count = self._check_dead_listings(products)
        issues.extend(dead_issues)

        logger.info(
            "listing_scan_complete",
            store_id=store_id,
            products_scanned=len(products),
            avg_score=avg_score,
            below_50=products_below_50,
            dead_listings=dead_count,
        )

        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={
                "products_scanned": len(products),
                "avg_score": avg_score,
                "products_below_50": products_below_50,
                "dead_listings_count": dead_count,
            },
        )

    def _score_title(self, product: dict) -> int:
        title = product.get("title", "")
        score = 100

        # Length check
        if len(title) < 10:
            score -= 40
        elif len(title) < 20:
            score -= 20
        elif len(title) > 150:
            score -= 15

        # All caps penalty
        if title.isupper() and len(title) > 3:
            score -= 20

        # Generic title penalty
        generic = {"product", "item", "test", "untitled", "default title"}
        if title.lower().strip() in generic:
            score -= 50

        return max(0, min(100, score))

    def _score_description(self, product: dict) -> int:
        html = product.get("descriptionHtml", "") or ""
        # Strip HTML tags for word count
        text = re.sub(r"<[^>]+>", " ", html).strip()
        word_count = len(text.split()) if text else 0

        score = 100

        if word_count == 0:
            return 0
        if word_count < 10:
            score -= 50
        elif word_count < 30:
            score -= 30
        elif word_count < 50:
            score -= 10

        # Check for structure (paragraphs, lists)
        if "<ul>" in html or "<ol>" in html:
            score += 5  # bonus for structured content
        if "<h" in html:
            score += 5  # bonus for headings

        return max(0, min(100, score))

    def _score_images(self, product: dict) -> int:
        images = [e["node"] for e in product.get("images", {}).get("edges", [])]
        score = 100

        if not images:
            return 0

        # Count of images.
        if len(images) < 2:
            score -= 30  # single-image listings look amateur
        elif len(images) < 3:
            score -= 10

        # Alt text coverage + descriptiveness (>= _MIN_ALT_TEXT_WORDS).
        missing_alt = 0
        short_alt = 0
        for img in images:
            alt = (img.get("altText") or "").strip()
            if not alt:
                missing_alt += 1
            elif len(alt.split()) < _MIN_ALT_TEXT_WORDS:
                short_alt += 1
        total = len(images)
        if missing_alt == total:
            score -= 40
        elif missing_alt > 0:
            score -= int(20 * missing_alt / total)
        if short_alt > 0:
            score -= min(10, short_alt * 3)

        # Resolution — below 800×800 we can't zoom cleanly.
        small = sum(
            1
            for img in images
            if (img.get("width") or 0) < _MIN_IMAGE_DIM_PX
            or (img.get("height") or 0) < _MIN_IMAGE_DIM_PX
        )
        if small > 0:
            score -= min(15, small * 5)

        # First image aspect ratio — Shopify recommends square (1:1) for grids.
        first = images[0]
        w = first.get("width") or 0
        h = first.get("height") or 0
        if w and h:
            ratio = w / h
            if ratio < 0.9 or ratio > 1.1:
                score -= 5

        return max(0, min(100, score))

    def _score_seo(self, product: dict) -> int:
        seo = product.get("seo", {}) or {}
        score = 100

        seo_title = seo.get("title") or ""
        seo_desc = seo.get("description") or ""

        if not seo_title:
            score -= 30
        elif len(seo_title) < 20:
            score -= 15
        elif len(seo_title) > 60:
            score -= 10

        if not seo_desc:
            score -= 30
        elif len(seo_desc) < 50:
            score -= 15
        elif len(seo_desc) > 160:
            score -= 10

        return max(0, min(100, score))

    # ------------------------------------------------------------------
    # Dead listing detector (#26)
    # ------------------------------------------------------------------

    def _check_dead_listings(
        self, products: list[dict]
    ) -> tuple[list[ScanIssue], int]:
        """Flag out-of-stock / stale-draft products.

        Returns (issues, dead_count).
        """
        issues: list[ScanIssue] = []
        now = datetime.now(UTC)
        count = 0

        for product in products:
            reason = self._dead_reason(product, now)
            if not reason:
                continue
            count += 1
            issues.append(
                ScanIssue(
                    module="listings",
                    scanner=self.name,
                    severity="minor",
                    title=f"Dead listing: '{product.get('title', '')}'",
                    description=reason,
                    impact="Takes catalogue space without generating revenue",
                    impact_value=None,
                    impact_unit=None,
                    fix_type="manual",
                    fix_description=(
                        "Improve, archive, or delete this listing. Dead "
                        "products dilute your catalogue quality signal."
                    ),
                    auto_fixable=False,
                    context={
                        "shopify_product_id": product.get("id"),
                        "title": product.get("title"),
                        "handle": product.get("handle"),
                        "status": product.get("status"),
                        "total_inventory": product.get("totalInventory"),
                        "updated_at": product.get("updatedAt"),
                        "reason": reason,
                    },
                )
            )

        return issues, count

    @staticmethod
    def _dead_reason(product: dict, now: datetime) -> str | None:
        """Return a short reason string if the product qualifies as 'dead'."""
        status = (product.get("status") or "").upper()

        # Condition A — stale DRAFT
        if status == "DRAFT":
            updated_at = _parse_iso(product.get("updatedAt"))
            if updated_at and now - updated_at > timedelta(days=_DEAD_DRAFT_DAYS):
                return (
                    f"Kept in DRAFT status for more than {_DEAD_DRAFT_DAYS} "
                    f"days (last update {updated_at.date().isoformat()})."
                )

        # Condition B — out of stock for a long time
        total_inventory = product.get("totalInventory")
        updated_at = _parse_iso(product.get("updatedAt"))
        if (
            total_inventory is not None
            and total_inventory <= 0
            and updated_at
            and now - updated_at > timedelta(days=_DEAD_OOS_DAYS)
        ):
            return (
                f"Out of stock and untouched for more than {_DEAD_OOS_DAYS} "
                "days."
            )

        return None


def _parse_iso(value: str | None) -> datetime | None:
    """Parse an ISO-8601 timestamp with or without a trailing Z."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
