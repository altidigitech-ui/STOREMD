"""Benchmark Scanner — feature #11.

Compares the current store score against the cross-store fleet average
(stored in Mem0 cross-store memory).

Until we have ≥ MIN_SAMPLES baselines, we surface an info message rather
than misleading numbers.
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


MIN_SAMPLES = 50  # Require at least this many baselines before benchmarking.

# Pattern: "Scan {scan_id} completed. Score: 67 (mobile: 52, desktop: 81)..."
_SCORE_RE = re.compile(r"Score:\s*(\d+)")


class BenchmarkScanner(BaseScanner):
    """Compare the store's current score with the cross-store fleet average.

    The cross-store memory layer is consumed via the orchestrator's
    `memory_context` argument — same pattern as the other scanners.
    """

    name = "benchmark"
    module = "health"
    group = "shopify_api"
    requires_plan = "pro"

    async def scan(
        self,
        store_id: str,
        shopify: ShopifyClient,
        memory_context: list[dict],
    ) -> ScannerResult:
        # Pull the current score from the store's own memory context.
        store_score = self._extract_latest_score(memory_context)

        # Cross-store data is mixed into memory_context by the
        # orchestrator. We extract only entries that carry a score.
        all_scores = self._extract_all_scores(memory_context)

        if len(all_scores) < MIN_SAMPLES:
            return ScannerResult(
                scanner_name=self.name,
                issues=[
                    ScanIssue(
                        module="health",
                        scanner=self.name,
                        severity="info",
                        title="Benchmark unlocks at 50 stores scanned",
                        description=(
                            f"Need at least {MIN_SAMPLES} stores in the "
                            f"benchmark pool. Currently {len(all_scores)}."
                        ),
                        fix_type="manual",
                        fix_description=(
                            "Benchmark will appear automatically once the "
                            "fleet has enough samples."
                        ),
                        auto_fixable=False,
                    )
                ],
                metrics={
                    "samples": len(all_scores),
                    "min_samples": MIN_SAMPLES,
                    "store_score": store_score,
                    "average_score": None,
                    "percentile": None,
                },
            )

        average = sum(all_scores) / len(all_scores)
        percentile = self._percentile(store_score, all_scores) if store_score else None

        issues: list[ScanIssue] = []
        if store_score is not None and store_score < average - 10:
            issues.append(
                ScanIssue(
                    module="health",
                    scanner=self.name,
                    severity="major",
                    title="Below the fleet average",
                    description=(
                        f"Your score ({store_score}) is more than 10 points "
                        f"below the average ({average:.0f}) across "
                        f"{len(all_scores)} stores."
                    ),
                    impact=f"-{average - store_score:.0f} points vs average",
                    impact_value=float(average - store_score),
                    impact_unit="score_points",
                    fix_type="manual",
                    fix_description="Review the issues list to close the gap.",
                    auto_fixable=False,
                )
            )

        logger.info(
            "benchmark_scan_complete",
            store_id=store_id,
            store_score=store_score,
            average=average,
            samples=len(all_scores),
        )

        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={
                "samples": len(all_scores),
                "min_samples": MIN_SAMPLES,
                "store_score": store_score,
                "average_score": round(average, 1),
                "percentile": percentile,
            },
        )

    @staticmethod
    def _extract_latest_score(memory_context: list[dict]) -> int | None:
        for mem in memory_context:
            text = str(mem.get("memory") or mem.get("content") or "")
            match = _SCORE_RE.search(text)
            if match:
                return int(match.group(1))
        return None

    @staticmethod
    def _extract_all_scores(memory_context: list[dict]) -> list[int]:
        scores: list[int] = []
        for mem in memory_context:
            text = str(mem.get("memory") or mem.get("content") or "")
            for match in _SCORE_RE.finditer(text):
                try:
                    scores.append(int(match.group(1)))
                except ValueError:
                    continue
        return scores

    @staticmethod
    def _percentile(value: int, samples: list[int]) -> int:
        if not samples:
            return 0
        below = sum(1 for s in samples if s < value)
        return round(100 * below / len(samples))
