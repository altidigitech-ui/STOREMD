"""Real User Simulation — feature #43.

Walks through the buyer journey on mobile (Homepage → Collection →
Product → Add to Cart → Cart) and times each step. Identifies the
slowest step (>3s) as the bottleneck and persists results.

CRITICAL RULE: never submit a real payment. We stop at /cart.

Reference: .claude/skills/browser-automation/SKILL.md
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

from app.agent.browser.base import BaseBrowserScanner
from app.models.scan import ScanIssue, ScannerResult

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()


_BOTTLENECK_THRESHOLD_MS = 3_000  # >3s on a single step is a bottleneck
_TOTAL_MAJOR_MS = 10_000
_TOTAL_CRITICAL_MS = 20_000

# Selectors we try in order to find the Add-to-Cart button.
_ATC_SELECTORS: list[str] = [
    "button[name='add']",
    "button.product-form__submit",
    "[data-action='add-to-cart']",
    "button:has-text('Add to cart')",
    "button:has-text('Add to Cart')",
]


class RealUserSimulation(BaseBrowserScanner):
    """5-step purchase path simulation, mobile-first."""

    name = "real_user_simulation"
    module = "browser"

    async def run_test(
        self,
        browser: Any,
        store_url: str,
        store_id: str,
        memory_context: list[dict],
    ) -> ScannerResult:
        page = await self.create_page(browser, "mobile")
        steps: list[dict] = []
        bottleneck_step: str | None = None
        bottleneck_cause: str | None = None

        try:
            # Step 1 — Homepage
            steps.append(await self._time_navigation(page, store_url, "Homepage"))

            # Step 2 — Collection
            collection_url = await self._find_collection_link(page, store_url)
            if collection_url:
                steps.append(
                    await self._time_navigation(
                        page, collection_url, "Collection"
                    )
                )

            # Step 3 — Product
            product_url = await self._find_product_link(page, store_url)
            if product_url:
                steps.append(
                    await self._time_navigation(page, product_url, "Product")
                )

                # Step 4 — Add to Cart (only if we made it to a product page)
                steps.append(await self._time_add_to_cart(page))

            # Step 5 — Cart / Checkout (NEVER submit payment)
            steps.append(
                await self._time_navigation(
                    page, f"{store_url}/cart", "Cart/Checkout"
                )
            )
        except Exception as exc:  # noqa: BLE001 — record + keep going
            logger.warning(
                "simulation_step_failed",
                store_id=store_id,
                error=str(exc),
            )
            steps.append(
                {
                    "name": "Error",
                    "url": page.url if page else None,
                    "time_ms": 0,
                    "bottleneck": False,
                    "cause": str(exc)[:120],
                }
            )
        finally:
            try:
                await page.close()
            except Exception:  # noqa: BLE001
                pass

        total_ms = sum(int(s.get("time_ms") or 0) for s in steps)

        # Identify the bottleneck.
        if steps:
            slowest = max(steps, key=lambda s: int(s.get("time_ms") or 0))
            if int(slowest.get("time_ms") or 0) > _BOTTLENECK_THRESHOLD_MS:
                slowest["bottleneck"] = True
                bottleneck_step = slowest["name"]
                bottleneck_cause = self._diagnose_bottleneck(
                    slowest, memory_context
                )
                slowest["cause"] = bottleneck_cause

        issues: list[ScanIssue] = []
        if total_ms > _TOTAL_MAJOR_MS:
            severity = (
                "critical" if total_ms > _TOTAL_CRITICAL_MS else "major"
            )
            issues.append(
                ScanIssue(
                    module="browser",
                    scanner=self.name,
                    severity=severity,
                    title=(
                        f"Slow user journey: {total_ms / 1000:.1f}s total"
                    ),
                    description=(
                        f"Full purchase path takes {total_ms / 1000:.1f}s. "
                        f"Bottleneck: {bottleneck_step or 'none'} "
                        f"({bottleneck_cause or 'unknown cause'})."
                    ),
                    impact=f"{total_ms / 1000:.1f}s total journey time",
                    impact_value=round(total_ms / 1000, 2),
                    impact_unit="seconds",
                    fix_type="manual",
                    fix_description=(
                        f"Optimize {bottleneck_step or 'the slowest step'}: "
                        f"{bottleneck_cause or 'investigate apps + theme'}"
                    ),
                    auto_fixable=False,
                    context={
                        "total_time_ms": total_ms,
                        "steps": steps,
                        "bottleneck_step": bottleneck_step,
                        "bottleneck_cause": bottleneck_cause,
                    },
                )
            )

        await self._record_simulation(
            store_id=store_id,
            total_time_ms=total_ms,
            steps=steps,
            bottleneck_step=bottleneck_step,
            bottleneck_cause=bottleneck_cause,
        )

        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={
                "total_time_ms": total_ms,
                "steps": steps,
                "bottleneck_step": bottleneck_step,
                "bottleneck_cause": bottleneck_cause,
            },
        )

    # ------------------------------------------------------------------
    # Step helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _time_navigation(page: Any, url: str, name: str) -> dict:
        """Navigate to url and return the elapsed time as a step dict."""
        start = time.monotonic()
        try:
            await page.goto(
                url, wait_until="domcontentloaded", timeout=30_000
            )
            await page.wait_for_load_state("networkidle", timeout=15_000)
        except Exception:  # noqa: BLE001 — partial loads still count
            pass
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return {
            "name": name,
            "url": url,
            "time_ms": elapsed_ms,
            "bottleneck": False,
            "cause": None,
        }

    @staticmethod
    async def _time_add_to_cart(page: Any) -> dict:
        """Try common ATC selectors and time the click + cart update."""
        start = time.monotonic()
        try:
            for selector in _ATC_SELECTORS:
                try:
                    btn = page.locator(selector).first
                    if await btn.is_visible():
                        await btn.click()
                        await page.wait_for_timeout(2_000)
                        break
                except Exception:  # noqa: BLE001 — try next selector
                    continue
        except Exception:  # noqa: BLE001
            pass
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return {
            "name": "Add to Cart",
            "url": None,
            "time_ms": elapsed_ms,
            "bottleneck": False,
            "cause": None,
        }

    @staticmethod
    async def _find_collection_link(page: Any, base_url: str) -> str | None:
        try:
            links = await page.locator("a[href*='/collections/']").all()
        except Exception:  # noqa: BLE001
            return f"{base_url}/collections/all"
        for link in links[:5]:
            try:
                href = await link.get_attribute("href")
            except Exception:  # noqa: BLE001
                continue
            if href and "/collections/" in href and href != "/collections/all":
                return href if href.startswith("http") else f"{base_url}{href}"
        return f"{base_url}/collections/all"

    @staticmethod
    async def _find_product_link(page: Any, base_url: str) -> str | None:
        try:
            links = await page.locator("a[href*='/products/']").all()
        except Exception:  # noqa: BLE001
            return None
        for link in links[:5]:
            try:
                href = await link.get_attribute("href")
            except Exception:  # noqa: BLE001
                continue
            if href and "/products/" in href:
                return href if href.startswith("http") else f"{base_url}{href}"
        return None

    @staticmethod
    def _diagnose_bottleneck(
        step: dict, memory_context: list[dict]
    ) -> str:
        """Use Mem0 context (recent app updates) to suggest a likely cause."""
        for mem in memory_context:
            text = str(mem.get("memory") or mem.get("content") or "")
            if "app" in text.lower() and "ms" in text.lower():
                return text[:200]
        return f"{step.get('name', 'Step')} took >{_BOTTLENECK_THRESHOLD_MS / 1000:.0f}s"

    # ------------------------------------------------------------------
    # DB persistence (best-effort)
    # ------------------------------------------------------------------

    async def _record_simulation(
        self,
        *,
        store_id: str,
        total_time_ms: int,
        steps: list[dict],
        bottleneck_step: str | None,
        bottleneck_cause: str | None,
    ) -> None:
        try:
            from app.dependencies import get_supabase_service

            supabase = get_supabase_service()
            supabase.table("user_simulations").insert(
                {
                    "store_id": store_id,
                    "total_time_ms": total_time_ms,
                    "steps": steps,
                    "bottleneck_step": bottleneck_step,
                    "bottleneck_cause": bottleneck_cause,
                    "created_at": datetime.now(UTC).isoformat(),
                }
            ).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "simulation_record_failed",
                store_id=store_id,
                error=str(exc),
            )
