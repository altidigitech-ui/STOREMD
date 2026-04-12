"""Broken Links Scanner — feature #40.

Crawls a sample of the storefront's pages and product URLs via the
Shopify API, then issues HEAD requests to detect 404/5xx/timeouts.

Capped at MAX_LINKS to keep scan time reasonable.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import httpx
import structlog

from app.agent.analyzers.base import BaseScanner, ScannerResult
from app.models.scan import ScanIssue

if TYPE_CHECKING:
    from app.services.shopify import ShopifyClient

logger = structlog.get_logger()

MAX_LINKS = 100
HEAD_TIMEOUT_S = 10.0
HEAD_CONCURRENCY = 8


# We use the Shopify GraphQL API to enumerate stable URLs (pages,
# products, collections). External link crawling would require
# rendering the storefront — out of scope for the static scanner
# (handled by the browser group later).
LINKS_QUERY = """
query FetchLinks {
  shop {
    primaryDomain { url }
  }
  pages(first: 50) {
    edges {
      node {
        handle
      }
    }
  }
  products(first: 50, query: "status:active") {
    edges {
      node {
        handle
      }
    }
  }
  collections(first: 30) {
    edges {
      node {
        handle
      }
    }
  }
}
"""


class BrokenLinksScanner(BaseScanner):
    """Detect broken internal links on the storefront."""

    name = "broken_links"
    module = "compliance"
    group = "external"
    requires_plan = "starter"

    async def scan(
        self,
        store_id: str,
        shopify: ShopifyClient,
        memory_context: list[dict],
    ) -> ScannerResult:
        data = await shopify.graphql(LINKS_QUERY)
        base_url = (
            data.get("shop", {})
            .get("primaryDomain", {})
            .get("url", "")
            .rstrip("/")
        )

        if not base_url:
            return ScannerResult(
                scanner_name=self.name,
                issues=[],
                metrics={"checked": 0, "broken": 0, "skipped": "no_domain"},
            )

        urls: list[tuple[str, str]] = []  # (url, kind)

        for edge in data.get("pages", {}).get("edges", []):
            handle = edge["node"].get("handle")
            if handle:
                urls.append((f"{base_url}/pages/{handle}", "page"))

        for edge in data.get("products", {}).get("edges", []):
            handle = edge["node"].get("handle")
            if handle:
                urls.append((f"{base_url}/products/{handle}", "product"))

        for edge in data.get("collections", {}).get("edges", []):
            handle = edge["node"].get("handle")
            if handle:
                urls.append((f"{base_url}/collections/{handle}", "collection"))

        urls = urls[:MAX_LINKS]

        broken: list[dict] = []
        sem = asyncio.Semaphore(HEAD_CONCURRENCY)

        async with httpx.AsyncClient(
            timeout=HEAD_TIMEOUT_S, follow_redirects=True
        ) as http:

            async def check(url: str, kind: str) -> None:
                async with sem:
                    try:
                        response = await http.head(url)
                        status = response.status_code
                        # Some Shopify pages reject HEAD with 405; retry with GET.
                        if status == 405:
                            response = await http.get(url)
                            status = response.status_code
                        if status >= 400:
                            broken.append(
                                {
                                    "url": url,
                                    "kind": kind,
                                    "status_code": status,
                                    "type": "internal",
                                }
                            )
                    except httpx.TimeoutException:
                        broken.append(
                            {
                                "url": url,
                                "kind": kind,
                                "status_code": 0,
                                "type": "internal",
                                "error": "timeout",
                            }
                        )
                    except httpx.HTTPError as exc:
                        broken.append(
                            {
                                "url": url,
                                "kind": kind,
                                "status_code": 0,
                                "type": "internal",
                                "error": str(exc)[:120],
                            }
                        )

            await asyncio.gather(*(check(u, k) for u, k in urls))

        issues: list[ScanIssue] = []
        for link in broken:
            severity = "major" if link.get("kind") == "product" else "minor"
            issues.append(
                ScanIssue(
                    module="compliance",
                    scanner=self.name,
                    severity=severity,
                    title=f"Broken {link['kind']} link: {link['url']}",
                    description=(
                        f"HEAD request returned status {link['status_code']}."
                        + (
                            f" Error: {link['error']}."
                            if link.get("error")
                            else ""
                        )
                    ),
                    impact="Visitors hitting 404 lose conversion + SEO penalty",
                    impact_value=1.0,
                    impact_unit="links",
                    fix_type="one_click",
                    fix_description=(
                        "Create a redirect from the broken URL to a relevant "
                        "live page or product."
                    ),
                    auto_fixable=True,
                    context=link,
                )
            )

        logger.info(
            "broken_links_complete",
            store_id=store_id,
            checked=len(urls),
            broken=len(broken),
        )

        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={
                "pages_crawled": len(urls),
                "broken_count": len(broken),
            },
        )
