"""BaseScanner ABC — contract for all StoreMD scanners."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from app.models.scan import ScanIssue, ScannerResult  # noqa: F401 — re-export

if TYPE_CHECKING:
    from app.services.shopify import ShopifyClient

PLAN_HIERARCHY: dict[str, int] = {
    "free": 0,
    "starter": 1,
    "pro": 2,
    "agency": 3,
}


class BaseScanner(ABC):
    """Base class for all StoreMD scanners.

    Attributes:
        name: Scanner identifier (e.g. "ghost_billing")
        module: Module this scanner belongs to ("health", "listings", etc.)
        group: Execution group ("shopify_api", "external", "browser")
        requires_plan: Minimum plan required to run this scanner
    """

    name: str
    module: str
    group: str
    requires_plan: str

    @abstractmethod
    async def scan(
        self,
        store_id: str,
        shopify: ShopifyClient,
        memory_context: list[dict],
    ) -> ScannerResult:
        """Execute the scan. Return issues and metrics.

        Rules:
        - NEVER raise an exception that blocks other scanners
        - NEVER call Claude API (that's the analyze node's job)
        - NEVER write to DB (that's the save_results node's job)
        - NEVER send notifications (that's the notify node's job)
        - ALWAYS return a ScannerResult, even if empty
        """
        ...

    async def should_run(self, modules: list[str], plan: str) -> bool:
        """Check if this scanner should execute given the modules and plan."""
        if self.module not in modules:
            return False
        return PLAN_HIERARCHY.get(plan, 0) >= PLAN_HIERARCHY.get(self.requires_plan, 0)
