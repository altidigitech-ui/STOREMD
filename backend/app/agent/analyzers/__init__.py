"""Scanner registry — registers all scanners, provides lookup by module/plan."""

from __future__ import annotations

from app.agent.analyzers.base import BaseScanner


class ScannerRegistry:
    """Central registry for all scanners.

    Usage:
        registry = ScannerRegistry()
        scanners = registry.get_for_modules(["health", "listings"])
    """

    def __init__(self) -> None:
        self._scanners: list[BaseScanner] = []
        self._register_all()

    def _register_all(self) -> None:
        """Register all known scanners."""
        # Lazy imports to avoid circular dependencies
        from app.agent.analyzers.health_scorer import HealthScorer
        from app.agent.analyzers.app_impact import AppImpactScanner
        from app.agent.analyzers.residue_detector import ResidueDetector
        from app.agent.analyzers.ghost_billing import GhostBillingDetector
        from app.agent.analyzers.code_weight import CodeWeightScanner
        from app.agent.analyzers.security_monitor import SecurityMonitor
        from app.agent.analyzers.listing_analyzer import ListingAnalyzer
        from app.agent.analyzers.pixel_health import PixelHealthScanner
        from app.agent.analyzers.agentic_readiness import AgenticReadinessScanner
        from app.agent.analyzers.hs_code_validator import HSCodeValidator
        from app.agent.analyzers.broken_links import BrokenLinksScanner
        from app.agent.analyzers.accessibility import AccessibilityScanner
        from app.agent.analyzers.bot_traffic import BotTrafficScanner
        from app.agent.analyzers.benchmark import BenchmarkScanner
        from app.agent.analyzers.trend_analyzer import TrendAnalyzer
        from app.agent.analyzers.content_theft import ContentTheftScanner
        from app.agent.browser.visual_store_test import VisualStoreTest
        from app.agent.browser.real_user_simulation import RealUserSimulation
        from app.agent.browser.accessibility_live import AccessibilityLiveTest

        self._scanners = [
            # Module: health (11)
            HealthScorer(),
            AppImpactScanner(),
            ResidueDetector(),
            GhostBillingDetector(),
            CodeWeightScanner(),
            SecurityMonitor(),
            PixelHealthScanner(),
            BotTrafficScanner(),
            BenchmarkScanner(),
            TrendAnalyzer(),
            ContentTheftScanner(),
            # Module: listings (1)
            ListingAnalyzer(),
            # Module: agentic (2)
            AgenticReadinessScanner(),
            HSCodeValidator(),
            # Module: compliance (2)
            BrokenLinksScanner(),
            AccessibilityScanner(),
            # Module: browser (3, Pro plan, sequential)
            VisualStoreTest(),
            RealUserSimulation(),
            AccessibilityLiveTest(),
        ]

    def register(self, scanner: BaseScanner) -> None:
        """Register a scanner dynamically."""
        self._scanners.append(scanner)

    def get_for_modules(self, modules: list[str]) -> list[BaseScanner]:
        """Return all scanners that belong to the requested modules."""
        return [s for s in self._scanners if s.module in modules]

    async def get_eligible(
        self, modules: list[str], plan: str
    ) -> list[BaseScanner]:
        """Return scanners eligible for the given modules and plan."""
        result = []
        for scanner in self._scanners:
            if await scanner.should_run(modules, plan):
                result.append(scanner)
        return result

    @property
    def all_scanners(self) -> list[BaseScanner]:
        return list(self._scanners)
