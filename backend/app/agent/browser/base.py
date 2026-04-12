"""BaseBrowserScanner — Playwright lifecycle for the 3 browser scanners.

Reference: .claude/skills/browser-automation/SKILL.md

The scan() method handles the heavy lifting:
- Launches headless Chromium with container-friendly args
- Resolves the store's public URL via Shopify GraphQL
- Delegates to run_test() implemented by each subclass
- Always closes the browser, even on error

Subclasses focus on the actual test logic in run_test().
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

import structlog

from app.agent.analyzers.base import BaseScanner, ScannerResult

if TYPE_CHECKING:
    from app.services.shopify import ShopifyClient

logger = structlog.get_logger()


# Realistic mobile + desktop user agents.
MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
    "Mobile/15E148 Safari/604.1"
)

DESKTOP_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Container-friendly Chromium launch args.
CHROMIUM_ARGS: list[str] = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--single-process",
]

# Viewport presets.
VIEWPORTS: dict[str, dict[str, Any]] = {
    "mobile": {"width": 375, "height": 812, "user_agent": MOBILE_UA},
    "desktop": {"width": 1440, "height": 900, "user_agent": DESKTOP_UA},
}

# Default page action timeout in milliseconds.
DEFAULT_TIMEOUT_MS = 30_000


_STORE_URL_QUERY = """
query {
  shop {
    primaryDomain { url }
  }
}
"""


class BaseBrowserScanner(BaseScanner):
    """Base class for all Playwright-backed scanners.

    Subclass contract: implement `run_test()` — it receives the launched
    browser, the resolved store URL, the store id, and the memory context.
    """

    group = "browser"
    requires_plan = "pro"

    async def scan(
        self,
        store_id: str,
        shopify: ShopifyClient,
        memory_context: list[dict],
    ) -> ScannerResult:
        store_url = await self.get_store_url(store_id, shopify)
        if not store_url:
            logger.warning(
                "browser_scan_no_store_url",
                store_id=store_id,
                scanner=self.name,
            )
            return ScannerResult(
                scanner_name=self.name,
                issues=[],
                metrics={"skipped": "no_store_url"},
            )

        # Lazy import — Playwright is only installed in the worker image.
        try:
            from playwright.async_api import async_playwright
        except Exception as exc:  # noqa: BLE001 — package missing in API container
            logger.warning(
                "playwright_unavailable",
                scanner=self.name,
                error=str(exc),
            )
            return ScannerResult(
                scanner_name=self.name,
                issues=[],
                metrics={"skipped": "playwright_unavailable"},
            )

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=CHROMIUM_ARGS,
            )
            try:
                return await self.run_test(
                    browser, store_url, store_id, memory_context
                )
            finally:
                try:
                    await browser.close()
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "browser_close_failed",
                        scanner=self.name,
                        error=str(exc),
                    )

    async def get_store_url(
        self, store_id: str, shopify: ShopifyClient
    ) -> str | None:
        """Return the store's public URL via Shopify GraphQL."""
        try:
            data = await shopify.graphql(_STORE_URL_QUERY)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "browser_get_store_url_failed",
                store_id=store_id,
                error=str(exc),
            )
            return None
        url = (
            (data or {})
            .get("shop", {})
            .get("primaryDomain", {})
            .get("url")
        )
        return url.rstrip("/") if url else None

    async def create_page(self, browser: Any, device: str = "desktop") -> Any:
        """Create a Playwright Page sized for `device` ('mobile' or 'desktop')."""
        vp = VIEWPORTS.get(device, VIEWPORTS["desktop"])
        context = await browser.new_context(
            viewport={"width": vp["width"], "height": vp["height"]},
            user_agent=vp["user_agent"],
        )
        page = await context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT_MS)
        return page

    @abstractmethod
    async def run_test(
        self,
        browser: Any,
        store_url: str,
        store_id: str,
        memory_context: list[dict],
    ) -> ScannerResult:
        """Subclass implements the actual Playwright test."""
        raise NotImplementedError
