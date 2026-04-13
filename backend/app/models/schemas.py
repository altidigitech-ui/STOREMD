"""Pydantic request/response schemas for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

VALID_MODULES = {"health", "listings", "agentic", "compliance", "browser"}


class ScanCreateRequest(BaseModel):
    modules: list[str] = Field(
        default=["health"],
        min_length=1,
        max_length=5,
    )

    def model_post_init(self, __context: object) -> None:
        invalid = set(self.modules) - VALID_MODULES
        if invalid:
            msg = f"Invalid modules: {invalid}. Valid: {', '.join(sorted(VALID_MODULES))}"
            raise ValueError(msg)


class ScanResponse(BaseModel):
    id: str
    status: str
    modules: list[str]
    trigger: str
    created_at: str


class ScanListItem(BaseModel):
    id: str
    status: str
    trigger: str
    modules: list[str]
    score: int | None = None
    mobile_score: int | None = None
    desktop_score: int | None = None
    issues_count: int = 0
    critical_count: int = 0
    partial_scan: bool = False
    duration_ms: int | None = None
    started_at: str | None = None
    completed_at: str | None = None
    created_at: str


class ScanIssueResponse(BaseModel):
    id: str
    module: str
    scanner: str
    severity: str
    title: str
    description: str
    impact: str | None = None
    impact_value: float | None = None
    impact_unit: str | None = None
    fix_type: str | None = None
    fix_description: str | None = None
    auto_fixable: bool = False
    fix_applied: bool = False
    dismissed: bool = False


class ScanDetailResponse(BaseModel):
    id: str
    status: str
    score: int | None = None
    mobile_score: int | None = None
    desktop_score: int | None = None
    modules: list[str]
    trigger: str
    partial_scan: bool = False
    duration_ms: int | None = None
    progress: int = 0
    current_step: str | None = None
    issues: list[ScanIssueResponse] = []
    errors: list[str] = []
    started_at: str | None = None
    completed_at: str | None = None


class HealthScoreHistory(BaseModel):
    date: str
    score: int


class HealthResponse(BaseModel):
    score: int | None = None
    mobile_score: int | None = None
    desktop_score: int | None = None
    trend: str = "stable"  # "up", "down", "stable"
    trend_delta: int = 0
    last_scan_at: str | None = None
    issues_count: int = 0
    critical_count: int = 0
    previous_score: int | None = None
    history: list[HealthScoreHistory] = []


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

class PaginationMeta(BaseModel):
    has_next: bool = False
    next_cursor: str | None = None
    total_count: int | None = None


class PaginatedResponse(BaseModel):
    data: list = []
    pagination: PaginationMeta = PaginationMeta()
