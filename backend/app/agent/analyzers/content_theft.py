"""Content Theft Scanner — feature #8.

Phase 2 — will use Google Search API to detect copied product
descriptions. For now this is a placeholder so the registry has a
stable scanner name and the orchestrator can already include it in
the scan pipeline (it just emits no issues).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from app.agent.analyzers.base import BaseScanner, ScannerResult

if TYPE_CHECKING:
    from app.services.shopify import ShopifyClient

logger = structlog.get_logger()


class ContentTheftScanner(BaseScanner):
    """Placeholder — see docs/FEATURES.md #8."""

    name = "content_theft"
    module = "health"
    group = "external"
    requires_plan = "pro"

    async def scan(
        self,
        store_id: str,
        shopify: ShopifyClient,
        memory_context: list[dict],
    ) -> ScannerResult:
        logger.info("content_theft_skipped", store_id=store_id)
        return ScannerResult(
            scanner_name=self.name,
            issues=[],
            metrics={
                "status": "coming_soon",
                "phase": "Phase 2 — Google Search API integration",
            },
        )
