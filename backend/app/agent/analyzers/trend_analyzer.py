"""Trend Analyzer — feature companion to #1 Health Score 24/7.

Reads the last N completed scans for the store from Supabase and
computes:
- direction (up / down / stable)
- delta vs. previous scan
- streak (consecutive scans moving in the same direction)
- 7-day score history

Issues a `major` ScanIssue if the score has been declining for 3+
consecutive scans.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from app.agent.analyzers.base import BaseScanner, ScannerResult
from app.models.scan import ScanIssue

if TYPE_CHECKING:
    from app.services.shopify import ShopifyClient

logger = structlog.get_logger()


_MAX_HISTORY = 7
_DECLINING_STREAK_THRESHOLD = 3


class TrendAnalyzer(BaseScanner):
    """Detects multi-scan trends in the store's health score."""

    name = "trend_analyzer"
    module = "health"
    group = "shopify_api"  # No external network call, but plays nice with the API group
    requires_plan = "free"

    async def scan(
        self,
        store_id: str,
        shopify: ShopifyClient,
        memory_context: list[dict],
    ) -> ScannerResult:
        scores = await self._fetch_recent_scores(store_id)

        if len(scores) < 2:
            # Not enough data yet — return a clean info result.
            return ScannerResult(
                scanner_name=self.name,
                issues=[],
                metrics={
                    "trend": "stable",
                    "delta": 0,
                    "streak": 0,
                    "scores_7d": scores,
                    "samples": len(scores),
                },
            )

        # `scores` is most-recent first.
        latest = scores[0]
        previous = scores[1]
        delta = latest - previous
        if delta > 0:
            trend = "up"
        elif delta < 0:
            trend = "down"
        else:
            trend = "stable"

        streak = self._compute_streak(scores)
        issues: list[ScanIssue] = []
        if trend == "down" and streak >= _DECLINING_STREAK_THRESHOLD:
            issues.append(
                ScanIssue(
                    module="health",
                    scanner=self.name,
                    severity="major",
                    title=(
                        f"Score declining for {streak} consecutive scans"
                    ),
                    description=(
                        f"Your health score has dropped on {streak} "
                        f"consecutive scans (from {scores[streak - 1]} "
                        f"to {latest})."
                    ),
                    impact=f"-{scores[streak - 1] - latest} score points",
                    impact_value=float(scores[streak - 1] - latest),
                    impact_unit="score_points",
                    fix_type="manual",
                    fix_description=(
                        "Review what changed recently — recent app updates, "
                        "theme edits, new product launches."
                    ),
                    auto_fixable=False,
                    context={
                        "streak": streak,
                        "scores_7d": scores,
                        "trend": trend,
                    },
                )
            )

        logger.info(
            "trend_analyzer_complete",
            store_id=store_id,
            trend=trend,
            delta=delta,
            streak=streak,
            samples=len(scores),
        )

        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={
                "trend": trend,
                "delta": delta,
                "streak": streak,
                "scores_7d": scores,
                "samples": len(scores),
            },
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _fetch_recent_scores(self, store_id: str) -> list[int]:
        """Return up to _MAX_HISTORY most recent completed scan scores."""
        try:
            from app.dependencies import get_supabase_service

            supabase = get_supabase_service()
            result = (
                supabase.table("scans")
                .select("score, completed_at")
                .eq("store_id", store_id)
                .eq("status", "completed")
                .order("completed_at", desc=True)
                .limit(_MAX_HISTORY)
                .execute()
            )
            rows = result.data or []
            return [int(r["score"]) for r in rows if r.get("score") is not None]
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "trend_analyzer_query_failed",
                store_id=store_id,
                error=str(exc),
            )
            return []

    @staticmethod
    def _compute_streak(scores: list[int]) -> int:
        """Count consecutive scans where each newer scan is below the
        immediately older one. `scores` is newest-first."""
        if len(scores) < 2:
            return 0
        streak = 1
        for i in range(len(scores) - 1):
            if scores[i] < scores[i + 1]:
                streak += 1
            else:
                break
        return streak
