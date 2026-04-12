"""Listing Analyzer — Feature #21: score /100 per product listing."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import structlog

from app.agent.analyzers.base import BaseScanner, ScannerResult
from app.models.scan import ScanIssue

if TYPE_CHECKING:
    from app.services.shopify import ShopifyClient

logger = structlog.get_logger()

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
                seo { title description }
                images(first: 10) {
                    edges {
                        node { id altText url width height }
                    }
                }
                variants(first: 10) {
                    edges {
                        node { id title sku barcode price }
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

        logger.info(
            "listing_scan_complete",
            store_id=store_id,
            products_scanned=len(products),
            avg_score=avg_score,
            below_50=products_below_50,
        )

        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={
                "products_scanned": len(products),
                "avg_score": avg_score,
                "products_below_50": products_below_50,
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

        if len(images) < 2:
            score -= 30
        elif len(images) < 3:
            score -= 10

        # Alt text check
        missing_alt = sum(1 for img in images if not img.get("altText"))
        if missing_alt == len(images):
            score -= 40
        elif missing_alt > 0:
            score -= int(20 * missing_alt / len(images))

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
