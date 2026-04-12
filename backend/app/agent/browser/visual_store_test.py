"""Visual Store Test — feature #42.

Captures full-page screenshots of the storefront on mobile + desktop,
uploads them to Supabase Storage, then diffs against the previous
screenshot to surface significant visual changes.

Reference: .claude/skills/browser-automation/SKILL.md
"""

from __future__ import annotations

import io
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

from app.agent.browser.base import BaseBrowserScanner
from app.models.scan import ScanIssue, ScannerResult

if TYPE_CHECKING:
    from app.services.shopify import ShopifyClient  # noqa: F401

logger = structlog.get_logger()


# Pixel diff thresholds.
_PIXEL_DIFF_THRESHOLD = 30  # sum of RGB deltas above this = "changed pixel"
_SIGNIFICANT_DIFF_PCT = 5.0  # >5% changed pixels = visual change worth flagging
_CRITICAL_DIFF_PCT = 15.0  # >15% = critical (probable layout break)
_REGION_THRESHOLD_PCT = 3.0  # below this we don't bother reporting the region


class VisualStoreTest(BaseBrowserScanner):
    """Screenshot + pixel diff for mobile + desktop storefront."""

    name = "visual_store_test"
    module = "browser"

    async def run_test(
        self,
        browser: Any,
        store_url: str,
        store_id: str,
        memory_context: list[dict],
    ) -> ScannerResult:
        issues: list[ScanIssue] = []
        screenshots_metadata: dict[str, dict] = {}

        for device in ("mobile", "desktop"):
            page = await self.create_page(browser, device)
            try:
                # 1. Navigate, wait for idle + post-load animations.
                try:
                    await page.goto(
                        store_url, wait_until="networkidle", timeout=30_000
                    )
                except Exception as exc:  # noqa: BLE001 — partial loads still useful
                    logger.warning(
                        "visual_navigation_failed",
                        store_id=store_id,
                        device=device,
                        error=str(exc),
                    )
                await page.wait_for_timeout(2_000)

                # 2. Full-page screenshot.
                screenshot_bytes: bytes = await page.screenshot(
                    full_page=True, type="png"
                )

                # 3. Upload to Supabase Storage.
                ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
                storage_path = f"{store_id}/{device}_{ts}.png"
                public_url = await self._upload_screenshot(
                    storage_path, screenshot_bytes
                )

                screenshots_metadata[device] = {
                    "path": storage_path,
                    "url": public_url,
                    "diff_pct": None,
                    "diff_regions": [],
                    "significant_change": False,
                }

                # 4. Diff against previous screenshot for this device.
                previous = await self._get_previous_screenshot(
                    store_id, device
                )
                if previous and previous.get("bytes"):
                    diff_pct, regions = self._compute_diff(
                        previous["bytes"], screenshot_bytes
                    )
                    significant = diff_pct > _SIGNIFICANT_DIFF_PCT
                    screenshots_metadata[device].update(
                        {
                            "diff_pct": round(diff_pct, 1),
                            "diff_regions": regions,
                            "significant_change": significant,
                        }
                    )

                    if significant:
                        cause = self._guess_cause(regions, memory_context)
                        severity = (
                            "critical"
                            if diff_pct > _CRITICAL_DIFF_PCT
                            else "major"
                        )
                        issues.append(
                            ScanIssue(
                                module="browser",
                                scanner=self.name,
                                severity=severity,
                                title=(
                                    f"Visual change detected on {device} "
                                    f"({diff_pct:.1f}% changed)"
                                ),
                                description=(
                                    f"Significant visual changes detected on "
                                    f"the {device} storefront. "
                                    f"Probable cause: {cause}."
                                ),
                                impact=f"{diff_pct:.1f}% of page changed",
                                impact_value=float(diff_pct),
                                impact_unit="percent",
                                fix_type="manual",
                                fix_description=f"Review the changes: {cause}",
                                auto_fixable=False,
                                context={
                                    "device": device,
                                    "diff_pct": round(diff_pct, 1),
                                    "diff_regions": regions,
                                    "probable_cause": cause,
                                },
                            )
                        )

                # 5. Persist a row in the screenshots table.
                await self._record_screenshot(
                    store_id=store_id,
                    device=device,
                    storage_path=storage_path,
                    diff_pct=screenshots_metadata[device]["diff_pct"],
                    diff_regions=screenshots_metadata[device]["diff_regions"],
                    significant_change=screenshots_metadata[device][
                        "significant_change"
                    ],
                )

            finally:
                try:
                    await page.close()
                except Exception:  # noqa: BLE001
                    pass

        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={"screenshots": screenshots_metadata},
        )

    # ------------------------------------------------------------------
    # Diff helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_diff(
        prev_bytes: bytes, curr_bytes: bytes
    ) -> tuple[float, list[dict]]:
        """Pixel-by-pixel diff. Returns (changed_pct, regions)."""
        from PIL import Image, ImageChops  # noqa: PLC0415 — heavy import

        prev = Image.open(io.BytesIO(prev_bytes)).convert("RGB")
        curr = Image.open(io.BytesIO(curr_bytes)).convert("RGB")
        if prev.size != curr.size:
            curr = curr.resize(prev.size)

        diff = ImageChops.difference(prev, curr)
        diff_pixels = sum(
            1 for px in diff.getdata() if sum(px[:3]) > _PIXEL_DIFF_THRESHOLD
        )
        total = max(1, prev.size[0] * prev.size[1])
        diff_pct = (diff_pixels / total) * 100

        regions = VisualStoreTest._identify_regions(diff, prev.size)
        return diff_pct, regions

    @staticmethod
    def _identify_regions(diff_img: Any, size: tuple[int, int]) -> list[dict]:
        """Bucket the diff into top / middle / bottom thirds."""
        w, h = size
        thirds = [
            ("top (header/hero)", 0, h // 3),
            ("middle (content)", h // 3, 2 * h // 3),
            ("bottom (footer)", 2 * h // 3, h),
        ]
        regions: list[dict] = []
        for name, y_start, y_end in thirds:
            crop = diff_img.crop((0, y_start, w, y_end))
            changed = sum(
                1 for px in crop.getdata() if sum(px[:3]) > _PIXEL_DIFF_THRESHOLD
            )
            total = max(1, w * (y_end - y_start))
            pct = (changed / total) * 100
            if pct > _REGION_THRESHOLD_PCT:
                regions.append({"area": name, "change_pct": round(pct, 1)})
        return regions

    @staticmethod
    def _guess_cause(
        regions: list[dict], memory_context: list[dict]
    ) -> str:
        """Best-effort cause inference from Mem0 + region heuristic."""
        for mem in memory_context:
            text = str(mem.get("memory") or mem.get("content") or "")
            lowered = text.lower()
            if "updated" in lowered or "changed" in lowered:
                return text[:200]
        if not regions:
            return "Visual changes detected"
        areas = ", ".join(r["area"] for r in regions)
        return (
            f"Visual changes in {areas} — check recent app updates "
            "or theme changes"
        )

    # ------------------------------------------------------------------
    # Storage / DB helpers (best-effort, never block the scan)
    # ------------------------------------------------------------------

    async def _upload_screenshot(
        self, path: str, data: bytes
    ) -> str | None:
        try:
            from app.dependencies import get_supabase_service

            supabase = get_supabase_service()
            supabase.storage.from_("screenshots").upload(
                path, data, {"content-type": "image/png"}
            )
            return supabase.storage.from_("screenshots").get_public_url(path)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "visual_screenshot_upload_failed",
                path=path,
                error=str(exc),
            )
            return None

    async def _get_previous_screenshot(
        self, store_id: str, device: str
    ) -> dict | None:
        try:
            from app.dependencies import get_supabase_service

            supabase = get_supabase_service()
            result = (
                supabase.table("screenshots")
                .select("*")
                .eq("store_id", store_id)
                .eq("device", device)
                .order("created_at", desc=True)
                .limit(1)
                .maybe_single()
                .execute()
            )
            row = result.data if result and result.data else None
            if not row or not row.get("storage_path"):
                return None
            file_bytes = supabase.storage.from_("screenshots").download(
                row["storage_path"]
            )
            return {"bytes": file_bytes, **row}
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "visual_previous_screenshot_failed",
                store_id=store_id,
                device=device,
                error=str(exc),
            )
            return None

    async def _record_screenshot(
        self,
        *,
        store_id: str,
        device: str,
        storage_path: str,
        diff_pct: float | None,
        diff_regions: list[dict],
        significant_change: bool,
    ) -> None:
        try:
            from app.dependencies import get_supabase_service

            supabase = get_supabase_service()
            supabase.table("screenshots").insert(
                {
                    "store_id": store_id,
                    "device": device,
                    "storage_path": storage_path,
                    "diff_pct": diff_pct,
                    "diff_regions": diff_regions,
                    "significant_change": significant_change,
                    "created_at": datetime.now(UTC).isoformat(),
                }
            ).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "visual_screenshot_record_failed",
                store_id=store_id,
                device=device,
                error=str(exc),
            )
