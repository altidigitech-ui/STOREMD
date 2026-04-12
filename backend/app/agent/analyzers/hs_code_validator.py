"""HS Code Validator — feature #38.

Verifies that products have valid harmonized system codes:
- present (not null/empty)
- correct format (6-10 digits)
- consistent with the product type (heuristic prefix mapping)

Reference: .claude/skills/agentic-readiness/SKILL.md
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import structlog

from app.agent.analyzers.base import BaseScanner, ScannerResult
from app.models.scan import ScanIssue

if TYPE_CHECKING:
    from app.services.shopify import ShopifyClient

logger = structlog.get_logger()


PRODUCTS_HS_QUERY = """
query FetchProductsHS($first: Int!, $after: String) {
  products(first: $first, after: $after, query: "status:active") {
    edges {
      cursor
      node {
        id
        title
        productType
        variants(first: 5) {
          edges {
            node {
              harmonizedSystemCode
            }
          }
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""


class HSCodeValidator(BaseScanner):
    """Validates HS codes on products (presence, format, type coherence)."""

    name = "hs_code_validator"
    module = "agentic"
    group = "shopify_api"
    requires_plan = "pro"

    HS_CODE_REGEX = re.compile(r"^\d{6,10}$")

    # Heuristic mapping: product_type → expected HS prefix.
    TYPE_TO_HS_PREFIX: dict[str, str] = {
        "shirt": "6105",
        "t-shirt": "6109",
        "tshirt": "6109",
        "dress": "6104",
        "pants": "6103",
        "shoes": "6403",
        "sneakers": "6404",
        "bag": "4202",
        "handbag": "4202",
        "jewelry": "7113",
        "necklace": "7113",
        "watch": "9101",
        "cosmetics": "3304",
        "skincare": "3304",
        "candle": "3406",
        "supplement": "2106",
        "toy": "9503",
        "electronics": "8471",
        "phone case": "4202",
    }

    async def scan(
        self,
        store_id: str,
        shopify: ShopifyClient,
        memory_context: list[dict],
    ) -> ScannerResult:
        products = await self._fetch_products(shopify)

        missing = 0
        invalid = 0
        suspicious = 0
        issues: list[ScanIssue] = []

        for product in products:
            hs_code = self._extract_hs_code(product)
            product_type = (product.get("productType") or "").lower().strip()

            if not hs_code:
                missing += 1
                continue

            if not self.HS_CODE_REGEX.match(hs_code):
                invalid += 1
                issues.append(
                    ScanIssue(
                        module="agentic",
                        scanner=self.name,
                        severity="minor",
                        title=(
                            f"Invalid HS code format on '{product.get('title', '')}'"
                        ),
                        description=(
                            f"HS codes must be 6-10 digits. Found: '{hs_code}'."
                        ),
                        fix_type="manual",
                        fix_description="Correct the HS code in Shopify admin",
                        context={
                            "product_id": product["id"],
                            "hs_code": hs_code,
                        },
                    )
                )
                continue

            expected = self.TYPE_TO_HS_PREFIX.get(product_type)
            if expected and not hs_code.startswith(expected):
                suspicious += 1
                issues.append(
                    ScanIssue(
                        module="agentic",
                        scanner=self.name,
                        severity="minor",
                        title=(
                            f"Suspicious HS code on '{product.get('title', '')}'"
                        ),
                        description=(
                            f"Product type '{product_type}' usually has HS code "
                            f"starting with '{expected}', but found '{hs_code}'. "
                            "This may cause incorrect tariffs or customs delays."
                        ),
                        fix_type="manual",
                        fix_description=(
                            f"Verify HS code. Expected prefix: {expected}"
                        ),
                        context={
                            "product_id": product["id"],
                            "hs_code": hs_code,
                            "expected_prefix": expected,
                            "product_type": product_type,
                        },
                    )
                )

        if missing > 0:
            severity = "major" if missing > len(products) * 0.3 else "minor"
            issues.insert(
                0,
                ScanIssue(
                    module="agentic",
                    scanner=self.name,
                    severity=severity,
                    title=f"{missing} products missing HS code",
                    description=(
                        f"{missing} out of {len(products)} products have no HS code. "
                        "Missing HS codes cause incorrect tariffs, customs delays "
                        "and potential chargebacks for international orders."
                    ),
                    impact=f"{missing} products at risk for international shipping",
                    impact_value=float(missing),
                    impact_unit="products",
                    fix_type="manual",
                    fix_description=(
                        "Add HS codes in Shopify admin → Products → Edit → Shipping"
                    ),
                    context={
                        "missing_count": missing,
                        "total_products": len(products),
                    },
                ),
            )

        valid = len(products) - missing - invalid - suspicious

        logger.info(
            "hs_code_validator_complete",
            store_id=store_id,
            total=len(products),
            missing=missing,
            invalid=invalid,
            suspicious=suspicious,
        )

        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={
                "total_products": len(products),
                "missing_hs": missing,
                "invalid_hs": invalid,
                "suspicious_hs": suspicious,
                "valid_hs": max(0, valid),
            },
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_hs_code(product: dict) -> str | None:
        for edge in product.get("variants", {}).get("edges", []):
            hs = edge["node"].get("harmonizedSystemCode")
            if hs and hs.strip():
                return hs.strip()
        return None

    async def _fetch_products(self, shopify: ShopifyClient) -> list[dict]:
        products: list[dict] = []
        cursor: str | None = None
        max_pages = 20
        for _ in range(max_pages):
            data = await shopify.graphql(
                PRODUCTS_HS_QUERY,
                {"first": 50, "after": cursor},
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
