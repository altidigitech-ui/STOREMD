from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PreviewIssue:
    severity: str  # "critical", "major", "minor", "info"
    title: str
    description: str
    category: str  # "seo", "accessibility", "security", "performance", "links", "robots"
    fix_available_after_install: bool = True


@dataclass
class PreviewCheckerResult:
    checker_name: str
    issues: list[PreviewIssue] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


@dataclass
class LockedModule:
    name: str
    description: str
    requires: str = "install"


@dataclass
class PreviewScanResult:
    shop_domain: str
    store_url: str
    preview_score: int
    scan_duration_ms: int
    checks_run: int
    checks_available_after_install: int
    issues: list[PreviewIssue] = field(default_factory=list)
    summary: dict = field(default_factory=dict)  # {"critical": N, "major": N, ...}
    locked_modules: list[LockedModule] = field(default_factory=list)
    error: str | None = None
