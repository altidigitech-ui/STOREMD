"""OuroborosLearner — couche LEARN du loop agent.

Pipeline:
1. process_feedback(): each accept/reject persists a merchant memory
2. Every PATTERN_INTERVAL feedbacks, analyze_patterns() reviews
   the merchant's history and writes an aggregated insight to the
   agent (cross-merchant) memory layer.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

import structlog

from app.agent.memory import StoreMemory

logger = structlog.get_logger()

# Trigger pattern analysis every N feedbacks for a merchant.
PATTERN_INTERVAL = 10


class OuroborosLearner:
    """Couche LEARN — feedback loop between merchant and agent."""

    def __init__(self, memory: StoreMemory) -> None:
        self.memory = memory

    async def process_feedback(
        self,
        merchant_id: str,
        issue_id: str,
        accepted: bool,
        reason: str | None,
        reason_category: str | None,
        supabase: Any,
    ) -> None:
        """Persist one feedback into Mem0 + log it.

        - Loads the issue from `scan_issues` to know its scanner/severity/title.
        - Calls memory.learn_from_feedback().
        - Triggers pattern analysis when the feedback count hits PATTERN_INTERVAL.
        """
        # Load the issue context (best-effort).
        issue_row: dict[str, Any] | None = None
        try:
            result = (
                supabase.table("scan_issues")
                .select("title, scanner, severity")
                .eq("id", issue_id)
                .maybe_single()
                .execute()
            )
            issue_row = result.data if result and result.data else None
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "feedback_issue_lookup_failed",
                issue_id=issue_id,
                error=str(exc),
            )

        title = issue_row.get("title") if issue_row else "unknown issue"
        scanner = issue_row.get("scanner") if issue_row else "unknown"
        severity = issue_row.get("severity") if issue_row else "minor"

        await self.memory.learn_from_feedback(
            merchant_id=merchant_id,
            issue_title=title,
            scanner=scanner,
            severity=severity,
            accepted=accepted,
            reason=reason,
        )

        logger.info(
            "feedback_processed",
            merchant_id=merchant_id,
            issue_id=issue_id,
            accepted=accepted,
            scanner=scanner,
            reason_category=reason_category,
        )

        # Pattern analysis trigger (every N feedbacks for this merchant).
        try:
            count_res = (
                supabase.table("feedback")
                .select("id", count="exact")
                .eq("merchant_id", merchant_id)
                .execute()
            )
            count = count_res.count or 0
            if count > 0 and count % PATTERN_INTERVAL == 0:
                await self.analyze_patterns(merchant_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "feedback_count_failed",
                merchant_id=merchant_id,
                error=str(exc),
            )

    async def analyze_patterns(self, merchant_id: str) -> dict[str, float]:
        """Review the merchant's feedback history and store an aggregated
        insight in agent memory.

        Returns the per-recommendation acceptance rate (mostly useful for tests).
        """
        memories = await self.memory.recall_merchant(
            merchant_id,
            "recommendation feedback ACCEPTED REJECTED",
            limit=50,
        )

        # Aggregate accepts vs rejects per scanner.
        per_scanner: dict[str, dict[str, int]] = defaultdict(
            lambda: {"accepted": 0, "rejected": 0}
        )

        for mem in memories:
            text = str(
                mem.get("memory")
                or mem.get("content")
                or mem.get("text")
                or ""
            )
            scanner_match = re.search(r"scanner:\s*([\w_-]+)", text)
            if not scanner_match:
                continue
            scanner = scanner_match.group(1)
            if "ACCEPTED" in text:
                per_scanner[scanner]["accepted"] += 1
            elif "REJECTED" in text:
                per_scanner[scanner]["rejected"] += 1

        rates: dict[str, float] = {}
        for scanner, counts in per_scanner.items():
            total = counts["accepted"] + counts["rejected"]
            if total == 0:
                continue
            rate = counts["accepted"] / total
            rates[scanner] = round(rate, 2)

            # Store a textual insight for future scans of this merchant.
            verdict = (
                "frequently rejects"
                if rate < 0.3
                else "usually accepts"
                if rate > 0.7
                else "is mixed on"
            )
            insight = (
                f"Merchant {merchant_id} {verdict} '{scanner}' recommendations "
                f"({counts['accepted']} accepted / {counts['rejected']} rejected, "
                f"rate {rate:.0%})."
            )
            await self.memory.remember_agent(insight)

        logger.info(
            "ouroboros_pattern_analysis",
            merchant_id=merchant_id,
            scanners=len(rates),
            rates=rates,
        )
        return rates
