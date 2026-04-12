"""Accessibility Live Test — extension of feature #39.

Renders the storefront with Playwright, injects axe-core, and runs
both the axe rules and a couple of manual heuristics (touch target
size, keyboard focus).

Reference: .claude/skills/browser-automation/SKILL.md
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from app.agent.browser.base import BaseBrowserScanner
from app.models.scan import ScanIssue, ScannerResult

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()


_AXE_VERSION = "4.9.1"
_AXE_CDN = (
    f"https://cdnjs.cloudflare.com/ajax/libs/axe-core/{_AXE_VERSION}/axe.min.js"
)

# axe impact → StoreMD severity.
_SEVERITY_MAP: dict[str, str] = {
    "critical": "critical",
    "serious": "major",
    "moderate": "minor",
    "minor": "info",
}

_MIN_TOUCH_TARGET_PX = 44


class AccessibilityLiveTest(BaseBrowserScanner):
    """Live WCAG checks via axe-core + Playwright manual heuristics."""

    name = "accessibility_live"
    module = "browser"

    async def run_test(
        self,
        browser: Any,
        store_url: str,
        store_id: str,
        memory_context: list[dict],
    ) -> ScannerResult:
        page = await self.create_page(browser, "mobile")
        issues: list[ScanIssue] = []

        try:
            try:
                await page.goto(
                    store_url, wait_until="networkidle", timeout=30_000
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "axe_navigation_failed",
                    store_id=store_id,
                    error=str(exc),
                )

            # 1. Inject axe-core.
            try:
                await page.add_script_tag(url=_AXE_CDN)
                axe_results = await page.evaluate("() => axe.run()")
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "axe_run_failed",
                    store_id=store_id,
                    error=str(exc),
                )
                axe_results = {"violations": []}

            for violation in axe_results.get("violations", []):
                impact = violation.get("impact", "minor")
                nodes = violation.get("nodes", [])
                issues.append(
                    ScanIssue(
                        module="browser",
                        scanner=self.name,
                        severity=_SEVERITY_MAP.get(impact, "minor"),
                        title=f"Accessibility: {violation.get('help', '')}",
                        description=violation.get("description", "") or "",
                        impact=f"{len(nodes)} elements affected",
                        impact_value=float(len(nodes)),
                        impact_unit="elements",
                        fix_type="developer",
                        fix_description=violation.get("helpUrl", "") or "",
                        auto_fixable=False,
                        context={
                            "rule_id": violation.get("id"),
                            "wcag_tags": violation.get("tags", []),
                            "nodes_count": len(nodes),
                        },
                    )
                )

            # 2. Manual heuristic — touch target size on mobile.
            small_buttons = await self._count_small_buttons(page)
            if small_buttons > 0:
                issues.append(
                    ScanIssue(
                        module="browser",
                        scanner=self.name,
                        severity="major",
                        title=(
                            f"{small_buttons} buttons too small for mobile "
                            f"(< {_MIN_TOUCH_TARGET_PX}px)"
                        ),
                        description=(
                            f"Touch targets should be at least "
                            f"{_MIN_TOUCH_TARGET_PX}x{_MIN_TOUCH_TARGET_PX}px "
                            "for accessibility."
                        ),
                        fix_type="developer",
                        fix_description=(
                            f"Increase button size to minimum "
                            f"{_MIN_TOUCH_TARGET_PX}x{_MIN_TOUCH_TARGET_PX}px"
                        ),
                        auto_fixable=False,
                        context={"small_buttons_count": small_buttons},
                    )
                )

            # 3. Manual heuristic — keyboard navigation reachable.
            try:
                await page.keyboard.press("Tab")
                focused = await page.evaluate(
                    "() => document.activeElement && document.activeElement.tagName"
                )
            except Exception:  # noqa: BLE001
                focused = None
            if not focused or focused == "BODY":
                issues.append(
                    ScanIssue(
                        module="browser",
                        scanner=self.name,
                        severity="major",
                        title=(
                            "Keyboard navigation broken — "
                            "no focusable elements"
                        ),
                        description=(
                            "Pressing Tab does not move focus to any "
                            "interactive element."
                        ),
                        fix_type="developer",
                        fix_description=(
                            "Ensure interactive elements have proper tabindex "
                            "and aren't trapped behind decorative wrappers."
                        ),
                        auto_fixable=False,
                    )
                )

        finally:
            try:
                await page.close()
            except Exception:  # noqa: BLE001
                pass

        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={
                "violations_count": len(issues),
                "axe_version": _AXE_VERSION,
            },
        )

    @staticmethod
    async def _count_small_buttons(page: Any) -> int:
        """Sample up to 20 buttons/role=button elements and count those <44px."""
        try:
            buttons = await page.locator(
                "button, a.btn, [role='button']"
            ).all()
        except Exception:  # noqa: BLE001
            return 0
        small = 0
        for btn in buttons[:20]:
            try:
                box = await btn.bounding_box()
            except Exception:  # noqa: BLE001
                continue
            if not box:
                continue
            if (
                box.get("width", 0) < _MIN_TOUCH_TARGET_PX
                or box.get("height", 0) < _MIN_TOUCH_TARGET_PX
            ):
                small += 1
        return small
