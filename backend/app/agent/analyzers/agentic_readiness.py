"""Agentic Readiness Scanner — features #35 + #36.

Scores how prepared a Shopify store is for agentic shopping
(ChatGPT, Copilot, Gemini). 6 weighted checks, computed across all
active products plus a theme-level schema markup check.

Reference: .claude/skills/agentic-readiness/SKILL.md
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from app.agent.analyzers.base import BaseScanner, ScannerResult
from app.models.scan import ScanIssue

if TYPE_CHECKING:
    from app.services.shopify import ShopifyClient

logger = structlog.get_logger()


PRODUCTS_QUERY = """
query FetchAgenticProducts($first: Int!, $after: String) {
  products(first: $first, after: $after, query: "status:active") {
    edges {
      cursor
      node {
        id
        title
        descriptionHtml
        productType
        status
        variants(first: 10) {
          edges {
            node {
              barcode
              sku
            }
          }
        }
        metafields(first: 20) {
          edges {
            node {
              namespace
              key
              value
              type
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


THEME_QUERY = """
query {
  themes(first: 1, roles: MAIN) {
    edges {
      node {
        id
        files(filenames: ["templates/product.json", "sections/main-product.liquid"], first: 2) {
          edges {
            node {
              filename
              body { ... on OnlineStoreThemeFileBodyText { content } }
            }
          }
        }
      }
    }
  }
}
"""


# Words that suggest a description is structured (not just marketing copy).
_SPEC_KEYWORDS = (
    "material",
    "dimensions",
    "weight",
    "size",
    "ingredients",
    "made from",
    "composed of",
    "specifications",
)


class AgenticReadinessScanner(BaseScanner):
    """6 weighted checks measuring AI-shopping compatibility."""

    name = "agentic_readiness"
    module = "agentic"
    group = "shopify_api"
    requires_plan = "starter"

    # Metafields that AI agents look for to recommend a product.
    IMPORTANT_METAFIELDS: list[tuple[str, str]] = [
        ("custom", "material"),
        ("custom", "dimensions"),
        ("custom", "weight"),
        ("custom", "care_instructions"),
        ("custom", "country_of_origin"),
    ]

    WEIGHTS: dict[str, float] = {
        "gtin_present": 0.20,
        "metafields_filled": 0.25,
        "structured_description": 0.20,
        "schema_markup": 0.15,
        "google_category": 0.10,
        "shopify_catalog": 0.10,
    }

    async def scan(
        self,
        store_id: str,
        shopify: ShopifyClient,
        memory_context: list[dict],
    ) -> ScannerResult:
        products = await self._fetch_products(shopify)
        total = len(products)

        checks: dict[str, dict] = {
            name: {"pass": 0, "fail": 0, "affected": []}
            for name in self.WEIGHTS
        }

        for product in products:
            self.check_gtin(product, checks)
            self.check_metafields(product, checks)
            self.check_description(product, checks)
            self.check_google_category(product, checks)
            # shopify_catalog: optimistic default — Shopify Catalog channel
            # status isn't in the basic Products API; treat as pass for now.
            checks["shopify_catalog"]["pass"] += 1

        # schema_markup is a theme-level binary check.
        schema_ok = await self._check_schema_markup(shopify)
        if schema_ok:
            checks["schema_markup"]["pass"] = total
        else:
            checks["schema_markup"]["fail"] = total

        score = self.calculate_score(checks, total)
        issues = self.build_issues(checks, total)

        logger.info(
            "agentic_readiness_complete",
            store_id=store_id,
            score=score,
            products=total,
            issues=len(issues),
        )

        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={
                "score": score,
                "products_scanned": total,
                "checks": {
                    name: {
                        "status": self._status_for(c, total),
                        "pass_rate": (c["pass"] / total) if total else 0.0,
                        "affected_products": c["fail"],
                    }
                    for name, c in checks.items()
                },
            },
        )

    # ------------------------------------------------------------------
    # Per-product checks
    # ------------------------------------------------------------------

    def check_gtin(self, product: dict, checks: dict) -> None:
        variants = product.get("variants", {}).get("edges", [])
        has_gtin = any(
            (v["node"].get("barcode") or "").strip() for v in variants
        )
        bucket = checks["gtin_present"]
        if has_gtin:
            bucket["pass"] += 1
        else:
            bucket["fail"] += 1
            bucket["affected"].append(product["id"])

    def check_metafields(self, product: dict, checks: dict) -> None:
        metafields = self._metafield_index(product)
        filled = sum(
            1
            for ns, key in self.IMPORTANT_METAFIELDS
            if (metafields.get((ns, key)) or "").strip()
        )
        bucket = checks["metafields_filled"]
        # At least 3/5 important metafields filled = pass.
        if filled >= 3:
            bucket["pass"] += 1
        else:
            bucket["fail"] += 1
            bucket["affected"].append(product["id"])

    def check_description(self, product: dict, checks: dict) -> None:
        desc = (product.get("descriptionHtml") or "").lower()
        word_count = len(desc.split())
        has_list = any(tag in desc for tag in ("<ul>", "<ol>", "<li>"))
        has_specs = any(kw in desc for kw in _SPEC_KEYWORDS)

        bucket = checks["structured_description"]
        if word_count >= 50 and (has_list or has_specs):
            bucket["pass"] += 1
        else:
            bucket["fail"] += 1
            bucket["affected"].append(product["id"])

    def check_google_category(self, product: dict, checks: dict) -> None:
        metafields = self._metafield_index(product)
        bucket = checks["google_category"]
        if (metafields.get(("google", "category")) or "").strip():
            bucket["pass"] += 1
        else:
            bucket["fail"] += 1
            bucket["affected"].append(product["id"])

    async def _check_schema_markup(self, shopify: ShopifyClient) -> bool:
        """Look for JSON-LD Product schema in the main theme template."""
        try:
            data = await shopify.graphql(THEME_QUERY)
        except Exception as exc:  # noqa: BLE001
            logger.warning("agentic_schema_check_failed", error=str(exc))
            return False

        for theme_edge in data.get("themes", {}).get("edges", []):
            files = (
                theme_edge.get("node", {}).get("files", {}).get("edges", [])
            )
            for file_edge in files:
                body = file_edge.get("node", {}).get("body") or {}
                content = (body.get("content") or "").lower()
                if "schema.org" in content or "application/ld+json" in content:
                    return True
        return False

    # ------------------------------------------------------------------
    # Score / issues
    # ------------------------------------------------------------------

    def calculate_score(self, checks: dict, total: int) -> int:
        if total == 0:
            return 0
        score = 0.0
        for name, weight in self.WEIGHTS.items():
            bucket = checks[name]
            considered = bucket["pass"] + bucket["fail"]
            rate = (bucket["pass"] / considered) if considered else 0.0
            score += rate * weight * 100
        return round(score)

    def build_issues(self, checks: dict, total: int) -> list[ScanIssue]:
        descriptions: dict[str, dict[str, str]] = {
            "gtin_present": {
                "title": "Products missing GTIN/barcode",
                "fix": "Add GTIN/barcode on each product variant",
                "fix_type": "manual",
            },
            "metafields_filled": {
                "title": "Products with incomplete metafields",
                "fix": (
                    "Fill key metafields (material, dimensions, weight) "
                    "to make products discoverable by AI agents"
                ),
                "fix_type": "one_click",
            },
            "structured_description": {
                "title": "Products with unstructured descriptions",
                "fix": "Rewrite descriptions with specs, bullet lists, dimensions",
                "fix_type": "one_click",
            },
            "schema_markup": {
                "title": "Theme missing Product schema markup",
                "fix": "Add JSON-LD Product schema to the product template",
                "fix_type": "developer",
            },
            "google_category": {
                "title": "Products without Google Product Category",
                "fix": "Assign Google categories via Shopify admin or metafields",
                "fix_type": "manual",
            },
            "shopify_catalog": {
                "title": "Products not published to Shopify Catalog",
                "fix": "Publish products to the Catalog sales channel",
                "fix_type": "manual",
            },
        }

        issues: list[ScanIssue] = []
        for name, bucket in checks.items():
            failed = bucket["fail"]
            if failed <= 0:
                continue
            desc = descriptions[name]
            severity = "critical" if failed > total * 0.5 else "major"
            issues.append(
                ScanIssue(
                    module="agentic",
                    scanner=self.name,
                    severity=severity,
                    title=f"{desc['title']} ({failed}/{total})",
                    description=(
                        f"{failed} out of {total} products fail this check. "
                        "AI shopping agents (ChatGPT, Copilot, Gemini) "
                        "need this data to recommend your products."
                    ),
                    impact=f"{failed} products invisible to AI agents",
                    impact_value=float(failed),
                    impact_unit="products",
                    fix_type=desc["fix_type"],
                    fix_description=desc["fix"],
                    auto_fixable=desc["fix_type"] == "one_click",
                    context={
                        "check": name,
                        "affected_count": failed,
                        "affected_product_ids": bucket["affected"][:50],
                    },
                )
            )
        return issues

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _metafield_index(product: dict) -> dict[tuple[str, str], str]:
        return {
            (m["node"]["namespace"], m["node"]["key"]): m["node"].get("value")
            for m in product.get("metafields", {}).get("edges", [])
        }

    @staticmethod
    def _status_for(bucket: dict, total: int) -> str:
        if bucket["fail"] == 0:
            return "pass"
        if bucket["pass"] > 0:
            return "partial"
        return "fail"

    async def _fetch_products(self, shopify: ShopifyClient) -> list[dict]:
        products: list[dict] = []
        cursor: str | None = None
        page_size = 50
        # Hard cap to avoid runaway iterations for very large catalogs.
        max_pages = 20

        for _ in range(max_pages):
            data = await shopify.graphql(
                PRODUCTS_QUERY,
                {"first": page_size, "after": cursor},
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
