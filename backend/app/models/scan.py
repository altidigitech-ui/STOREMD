"""Scan domain models — ScanIssue, ScannerResult, AgentState."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ScanIssue:
    """A single issue detected by a scanner."""

    module: str  # "health", "listings", "agentic", "compliance", "browser"
    scanner: str  # "ghost_billing", "app_impact", etc.
    severity: str  # "critical", "major", "minor", "info"
    title: str
    description: str
    impact: str | None = None  # "+1.8s load time", "$9.99/month lost"
    impact_value: float | None = None  # 1.8, 9.99 (for sorting)
    impact_unit: str | None = None  # "seconds", "dollars", "score_points", "percent"
    fix_type: str | None = None  # "one_click", "manual", "developer"
    fix_description: str | None = None
    auto_fixable: bool = False
    context: dict = field(default_factory=dict)


@dataclass
class ScannerResult:
    """Result from a single scanner execution."""

    scanner_name: str
    issues: list[ScanIssue] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)  # raw data (scores, counts, etc.)
    metadata: dict = field(default_factory=dict)  # debug info


@dataclass
class AgentState:
    """State object flowing through the LangGraph scan pipeline."""

    # Identifiers
    scan_id: str
    store_id: str
    merchant_id: str

    # Scan config
    modules: list[str] = field(default_factory=lambda: ["health"])
    trigger: str = "manual"  # "manual", "cron", "webhook"

    # Results (populated during the pipeline)
    score: int | None = None
    mobile_score: int | None = None
    desktop_score: int | None = None
    issues: list[ScanIssue] = field(default_factory=list)
    scanner_results: dict[str, ScannerResult] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    # Context from Mem0 (populated in load_memory node)
    historical_context: list[dict] = field(default_factory=list)
    merchant_preferences: dict = field(default_factory=dict)
    cross_store_signals: list[dict] = field(default_factory=list)

    # Metadata
    metadata: dict = field(default_factory=dict)
