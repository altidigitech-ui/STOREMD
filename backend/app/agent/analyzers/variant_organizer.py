"""Product Variant Organizer — feature #28.

Detects common variant structuring problems that confuse merchants
and shoppers alike:
- Duplicate variant titles within the same product
- Variants without SKU
- Identical prices across all variants (options not used to differentiate)
- Products with more than _MAX_VARIANTS variants (Shopify limit + UX)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from app.agent.analyzers.base import BaseScanner, ScannerResult
from app.models.scan import ScanIssue

if TYPE_CHECKING:
    from app.services.shopify import ShopifyClient

logger = structlog.get_logger()


_MAX_VARIANTS = 100  # hard limit before we flag it

VARIANT_QUERY = """
query FetchVariantsForOrganizer($first: Int!, $after: String) {
  products(first: $first, after: $after, query: "status:active") {
    edges {
      cursor
      node {
        id
        title
        handle
        totalVariants
        variants(first: 100) {
          edges {
            node {
              id
              title
              sku
              price
            }
          }
        }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""


class VariantOrganizer(BaseScanner):
    """Flag variant structuring issues (Pro plan)."""

    name = "variant_organizer"
    module = "listings"
    group = "shopify_api"
    requires_plan = "pro"

    async def scan(
        self,
        store_id: str,
        shopify: ShopifyClient,
        memory_context: list[dict],
    ) -> ScannerResult:
        products = await self._fetch_products(shopify)
        issues: list[ScanIssue] = []
        totals = {
            "duplicates": 0,
            "missing_sku": 0,
            "identical_prices": 0,
            "too_many": 0,
        }

        for product in products:
            for issue in self._check_product(product):
                totals_key = issue.context.get("kind")
                if totals_key:
                    totals[totals_key] = totals.get(totals_key, 0) + 1
                issues.append(issue)

        logger.info(
            "variant_organizer_complete",
            store_id=store_id,
            products=len(products),
            issues=len(issues),
            **totals,
        )

        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={
                "products_scanned": len(products),
                "duplicate_variants": totals["duplicates"],
                "missing_sku": totals["missing_sku"],
                "identical_prices": totals["identical_prices"],
                "too_many_variants": totals["too_many"],
            },
        )

    # ------------------------------------------------------------------
    # Per-product checks
    # ------------------------------------------------------------------

    def _check_product(self, product: dict) -> list[ScanIssue]:
        issues: list[ScanIssue] = []
        title = product.get("title", "")
        pid = product.get("id", "")

        variants = [
            edge["node"]
            for edge in product.get("variants", {}).get("edges", [])
        ]
        variant_count = product.get("totalVariants") or len(variants)

        if not variants:
            return issues

        # 1. Duplicate variant titles within the product.
        titles_seen: dict[str, int] = {}
        for v in variants:
            t = (v.get("title") or "").strip().lower()
            if t:
                titles_seen[t] = titles_seen.get(t, 0) + 1
        duplicates = [t for t, count in titles_seen.items() if count > 1]
        if duplicates:
            issues.append(
                ScanIssue(
                    module="listings",
                    scanner=self.name,
                    severity="minor",
                    title=f"Duplicate variant titles on '{title}'",
                    description=(
                        f"{len(duplicates)} variant title(s) repeated: "
                        f"{', '.join(duplicates[:5])}."
                    ),
                    fix_type="manual",
                    fix_description=(
                        "Give each variant a unique title based on its options."
                    ),
                    auto_fixable=False,
                    context={
                        "shopify_product_id": pid,
                        "kind": "duplicates",
                        "duplicate_titles": duplicates[:10],
                    },
                )
            )

        # 2. Variants without SKU.
        no_sku = [v for v in variants if not (v.get("sku") or "").strip()]
        if no_sku:
            issues.append(
                ScanIssue(
                    module="listings",
                    scanner=self.name,
                    severity="minor",
                    title=(
                        f"{len(no_sku)} variants without SKU on '{title}'"
                    ),
                    description=(
                        "Variants without SKUs make inventory reconciliation "
                        "and multi-channel sync unreliable."
                    ),
                    fix_type="manual",
                    fix_description=(
                        "Assign a unique SKU to every variant in Shopify."
                    ),
                    auto_fixable=False,
                    context={
                        "shopify_product_id": pid,
                        "kind": "missing_sku",
                        "variant_count": len(no_sku),
                    },
                )
            )

        # 3. Identical prices across all variants (when there are at least 2).
        if len(variants) >= 2:
            prices = {v.get("price") for v in variants}
            # Only flag if prices exist and are all identical.
            prices.discard(None)
            if len(prices) == 1:
                issues.append(
                    ScanIssue(
                        module="listings",
                        scanner=self.name,
                        severity="minor",
                        title=(
                            f"All variants of '{title}' have identical prices"
                        ),
                        description=(
                            "Multiple variants at the exact same price is "
                            "rarely intentional — either collapse into one "
                            "variant or price the differences."
                        ),
                        fix_type="manual",
                        fix_description=(
                            "Review the product options and decide if the "
                            "variants should be a single listing."
                        ),
                        auto_fixable=False,
                        context={
                            "shopify_product_id": pid,
                            "kind": "identical_prices",
                            "variant_count": len(variants),
                        },
                    )
                )

        # 4. Too many variants.
        if variant_count > _MAX_VARIANTS:
            issues.append(
                ScanIssue(
                    module="listings",
                    scanner=self.name,
                    severity="minor",
                    title=(
                        f"'{title}' has {variant_count} variants "
                        f"(>{_MAX_VARIANTS})"
                    ),
                    description=(
                        "Above ~100 variants, Shopify slows down the storefront "
                        "and admin. Split into multiple products if possible."
                    ),
                    fix_type="manual",
                    fix_description=(
                        "Group related variants into separate products, or "
                        "convert infrequent options into metafields."
                    ),
                    auto_fixable=False,
                    context={
                        "shopify_product_id": pid,
                        "kind": "too_many",
                        "variant_count": variant_count,
                    },
                )
            )

        return issues

    # ------------------------------------------------------------------
    # Fetch
    # ------------------------------------------------------------------

    async def _fetch_products(self, shopify: ShopifyClient) -> list[dict]:
        products: list[dict] = []
        cursor: str | None = None
        max_pages = 20
        for _ in range(max_pages):
            data = await shopify.graphql(
                VARIANT_QUERY, {"first": 50, "after": cursor}
            )
            edges = data.get("products", {}).get("edges", [])
            products.extend(edge["node"] for edge in edges)
            page = data.get("products", {}).get("pageInfo", {})
            if not page.get("hasNextPage"):
                break
            cursor = page.get("endCursor")
            if not cursor:
                break
        return products
