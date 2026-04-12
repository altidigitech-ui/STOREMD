"""Accessibility Scanner — feature #39 (static).

Fetches the storefront homepage HTML over HTTPS and runs lightweight
WCAG 2.1 heuristics:
- <img> without alt
- <input> without label
- <a> without text content
- <button> without accessible name
- heading hierarchy

Live (Playwright) scan is feature #39 extension and ships with the
browser group later. This static scanner gives the merchant useful
signal on Starter plan without needing a worker.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import TYPE_CHECKING

import httpx
import structlog

from app.agent.analyzers.base import BaseScanner, ScannerResult
from app.models.scan import ScanIssue

if TYPE_CHECKING:
    from app.services.shopify import ShopifyClient

logger = structlog.get_logger()

GET_TIMEOUT_S = 15.0


class _AccessibilityParser(HTMLParser):
    """Walk the DOM and accumulate accessibility violations.

    Counts (not lists) — we only need totals for the issue summary.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.imgs_total = 0
        self.imgs_missing_alt = 0
        self.inputs_total = 0
        self.inputs_with_id: set[str] = set()
        self.labels_for: set[str] = set()
        self.inputs_no_id = 0
        self.links_total = 0
        self._link_buf: list[str] = []
        self._link_open = False
        self.links_empty = 0
        self.buttons_total = 0
        self._btn_buf: list[str] = []
        self._btn_open = False
        self._btn_has_arialabel = False
        self.buttons_no_name = 0
        self.headings: list[int] = []  # h-level sequence
        self._h_open: int | None = None
        self._h_buf: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attrs_dict = {k: (v or "") for k, v in attrs}

        if tag == "img":
            self.imgs_total += 1
            if not (attrs_dict.get("alt") or "").strip():
                # role=presentation/none counts as intentionally decorative
                role = (attrs_dict.get("role") or "").lower()
                if role not in {"presentation", "none"}:
                    self.imgs_missing_alt += 1
            return

        if tag == "input":
            input_type = (attrs_dict.get("type") or "").lower()
            if input_type in {"hidden", "submit", "button"}:
                return
            self.inputs_total += 1
            input_id = attrs_dict.get("id")
            aria_label = (attrs_dict.get("aria-label") or "").strip()
            if input_id:
                self.inputs_with_id.add(input_id)
            elif not aria_label:
                self.inputs_no_id += 1
            return

        if tag == "label":
            for_id = attrs_dict.get("for")
            if for_id:
                self.labels_for.add(for_id)
            return

        if tag == "a":
            self.links_total += 1
            self._link_open = True
            self._link_buf = []
            aria_label = (attrs_dict.get("aria-label") or "").strip()
            if aria_label:
                self._link_buf.append(aria_label)
            return

        if tag == "button":
            self.buttons_total += 1
            self._btn_open = True
            self._btn_buf = []
            self._btn_has_arialabel = bool(
                (attrs_dict.get("aria-label") or "").strip()
            )
            return

        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(tag[1])
            self._h_open = level
            self._h_buf = []
            return

    def handle_data(self, data: str) -> None:
        if self._link_open:
            self._link_buf.append(data)
        if self._btn_open:
            self._btn_buf.append(data)
        if self._h_open is not None:
            self._h_buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._link_open:
            text = "".join(self._link_buf).strip()
            if not text:
                self.links_empty += 1
            self._link_open = False
            self._link_buf = []
            return

        if tag == "button" and self._btn_open:
            text = "".join(self._btn_buf).strip()
            if not text and not self._btn_has_arialabel:
                self.buttons_no_name += 1
            self._btn_open = False
            self._btn_buf = []
            self._btn_has_arialabel = False
            return

        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"} and self._h_open:
            text = "".join(self._h_buf).strip()
            if text:
                self.headings.append(self._h_open)
            self._h_open = None
            self._h_buf = []
            return

    # Inputs may appear before their <label for=...> — final reconciliation
    # is done in the scanner after parsing completes.
    def inputs_missing_label(self) -> int:
        unlabeled_with_id = sum(
            1 for input_id in self.inputs_with_id if input_id not in self.labels_for
        )
        return unlabeled_with_id + self.inputs_no_id

    def heading_skips(self) -> int:
        # Count "skip" jumps (e.g. h1 → h3) which break screen-reader navigation.
        skips = 0
        prev: int | None = None
        for level in self.headings:
            if prev is not None and level > prev + 1:
                skips += 1
            prev = level
        return skips


SHOP_QUERY = """
query { shop { primaryDomain { url } } }
"""


class AccessibilityScanner(BaseScanner):
    """Static WCAG 2.1 heuristic scan over the storefront homepage."""

    name = "accessibility"
    module = "compliance"
    group = "external"
    requires_plan = "starter"

    async def scan(
        self,
        store_id: str,
        shopify: ShopifyClient,
        memory_context: list[dict],
    ) -> ScannerResult:
        data = await shopify.graphql(SHOP_QUERY)
        url = (
            data.get("shop", {})
            .get("primaryDomain", {})
            .get("url", "")
            .rstrip("/")
        )

        if not url:
            return ScannerResult(
                scanner_name=self.name,
                issues=[],
                metrics={"score": 0, "skipped": "no_domain"},
            )

        try:
            async with httpx.AsyncClient(
                timeout=GET_TIMEOUT_S, follow_redirects=True
            ) as http:
                response = await http.get(url)
                response.raise_for_status()
                html = response.text
        except httpx.HTTPError as exc:
            logger.warning(
                "accessibility_fetch_failed", url=url, error=str(exc)
            )
            return ScannerResult(
                scanner_name=self.name,
                issues=[],
                metrics={"score": 0, "skipped": "fetch_error"},
            )

        parser = _AccessibilityParser()
        try:
            parser.feed(html)
        except Exception as exc:  # noqa: BLE001 — html parser is fragile
            logger.warning("accessibility_parse_failed", error=str(exc))

        violations = self._build_violations(parser)
        violations_count = sum(v["count"] for v in violations)
        # Score: 100 minus penalty per violation, floor 0.
        score = max(0, 100 - violations_count * 4)
        eaa_compliant = score >= 80 and not any(
            v["severity"] == "critical" for v in violations
        )

        issues: list[ScanIssue] = []
        for v in violations:
            issues.append(
                ScanIssue(
                    module="compliance",
                    scanner=self.name,
                    severity=v["severity"],
                    title=v["title"],
                    description=v["description"],
                    impact=f"{v['count']} elements affected",
                    impact_value=float(v["count"]),
                    impact_unit="elements",
                    fix_type=v["fix_type"],
                    fix_description=v["fix"],
                    auto_fixable=v["auto_fixable"],
                    context={"rule": v["rule"], "count": v["count"]},
                )
            )

        logger.info(
            "accessibility_scan_complete",
            store_id=store_id,
            score=score,
            violations=len(issues),
        )

        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={
                "score": score,
                "violations_count": len(issues),
                "eaa_compliant": eaa_compliant,
                "live_test_available": True,
            },
        )

    @staticmethod
    def _build_violations(parser: _AccessibilityParser) -> list[dict]:
        out: list[dict] = []

        if parser.imgs_missing_alt > 0:
            out.append(
                {
                    "rule": "img-alt",
                    "title": (
                        f"{parser.imgs_missing_alt} images missing alt text"
                    ),
                    "description": (
                        "Screen readers cannot describe images without an "
                        "alt attribute. WCAG 2.1 — 1.1.1."
                    ),
                    "severity": "critical",
                    "count": parser.imgs_missing_alt,
                    "fix": "Generate alt text via Claude API and apply",
                    "fix_type": "one_click",
                    "auto_fixable": True,
                }
            )

        unlabeled_inputs = parser.inputs_missing_label()
        if unlabeled_inputs > 0:
            out.append(
                {
                    "rule": "label",
                    "title": (
                        f"{unlabeled_inputs} form inputs without label"
                    ),
                    "description": (
                        "Inputs need an associated <label> or aria-label "
                        "for accessibility. WCAG 2.1 — 3.3.2."
                    ),
                    "severity": "major",
                    "count": unlabeled_inputs,
                    "fix": "Add <label for='...'> or aria-label",
                    "fix_type": "developer",
                    "auto_fixable": False,
                }
            )

        if parser.links_empty > 0:
            out.append(
                {
                    "rule": "link-name",
                    "title": f"{parser.links_empty} links without text",
                    "description": (
                        "Empty links are unusable for assistive tech. "
                        "WCAG 2.1 — 2.4.4."
                    ),
                    "severity": "major",
                    "count": parser.links_empty,
                    "fix": "Add text content or aria-label to every link",
                    "fix_type": "developer",
                    "auto_fixable": False,
                }
            )

        if parser.buttons_no_name > 0:
            out.append(
                {
                    "rule": "button-name",
                    "title": (
                        f"{parser.buttons_no_name} buttons without accessible name"
                    ),
                    "description": (
                        "Icon-only buttons must expose an aria-label. "
                        "WCAG 2.1 — 4.1.2."
                    ),
                    "severity": "major",
                    "count": parser.buttons_no_name,
                    "fix": "Add aria-label to icon-only buttons",
                    "fix_type": "developer",
                    "auto_fixable": False,
                }
            )

        skips = parser.heading_skips()
        if skips > 0:
            out.append(
                {
                    "rule": "heading-order",
                    "title": f"{skips} heading hierarchy skip(s)",
                    "description": (
                        "Headings should not skip levels (h1 → h3) — it "
                        "breaks screen-reader navigation. WCAG 2.1 — 1.3.1."
                    ),
                    "severity": "minor",
                    "count": skips,
                    "fix": "Use sequential heading levels in templates",
                    "fix_type": "developer",
                    "auto_fixable": False,
                }
            )

        return out


# Re-exported for tests that want to feed raw HTML bypassing httpx.
def parse_accessibility(html: str) -> list[dict]:
    parser = _AccessibilityParser()
    parser.feed(html)
    return AccessibilityScanner._build_violations(parser)
