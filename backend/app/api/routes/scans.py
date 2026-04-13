"""Scan API routes — create, list, detail, health score."""

from __future__ import annotations

import base64
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends, Query

from app.core.exceptions import AuthError, ErrorCode, ScanError
from app.dependencies import get_current_merchant, get_current_store, get_supabase_service
from app.models.schemas import (
    HealthResponse,
    HealthScoreHistory,
    PaginatedResponse,
    PaginationMeta,
    ScanCreateRequest,
    ScanDetailResponse,
    ScanIssueResponse,
    ScanListItem,
    ScanResponse,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/stores/{store_id}", tags=["scans"])

# Module -> minimum plan mapping
MODULE_PLAN_REQUIREMENTS: dict[str, str] = {
    "health": "free",
    "listings": "free",
    "agentic": "starter",
    "compliance": "starter",
    "browser": "pro",
}

PLAN_HIERARCHY: dict[str, int] = {
    "free": 0,
    "starter": 1,
    "pro": 2,
    "agency": 3,
}


@router.post("/scans", status_code=201)
async def create_scan(
    store_id: str,
    request: ScanCreateRequest,
    merchant: dict = Depends(get_current_merchant),
    store: dict = Depends(get_current_store),
) -> ScanResponse:
    """Trigger a new scan for a store."""
    supabase = get_supabase_service()
    plan = merchant.get("plan", "free")
    plan_level = PLAN_HIERARCHY.get(plan, 0)

    # Check plan requirements for requested modules
    for module in request.modules:
        required_plan = MODULE_PLAN_REQUIREMENTS.get(module, "free")
        if PLAN_HIERARCHY.get(required_plan, 0) > plan_level:
            raise AuthError(
                code=ErrorCode.PLAN_REQUIRED,
                message=f"Module '{module}' requires {required_plan} plan or above",
                status_code=403,
                context={"module": module, "required_plan": required_plan},
            )

    # Check for already running scan
    running = (
        supabase.table("scans")
        .select("id")
        .eq("store_id", store_id)
        .in_("status", ["pending", "running"])
        .execute()
    )
    if running.data:
        raise ScanError(
            code=ErrorCode.SCAN_ALREADY_RUNNING,
            message="A scan is already running for this store",
            status_code=409,
            context={"existing_scan_id": running.data[0]["id"]},
        )

    # Create scan record
    now = datetime.now(UTC).isoformat()
    scan_data = {
        "store_id": store_id,
        "merchant_id": merchant["id"],
        "status": "pending",
        "trigger": "manual",
        "modules": request.modules,
        "created_at": now,
    }

    result = supabase.table("scans").insert(scan_data).execute()
    scan = result.data[0]

    # Dispatch Celery task
    from tasks.scan_tasks import run_scan
    run_scan.delay(
        scan["id"],
        store_id,
        merchant["id"],
        request.modules,
        "manual",
    )

    logger.info("scan_created", scan_id=scan["id"], store_id=store_id, modules=request.modules)

    return ScanResponse(
        id=scan["id"],
        status=scan["status"],
        modules=request.modules,
        trigger="manual",
        created_at=now,
    )


@router.get("/scans")
async def list_scans(
    store_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    status: str | None = Query(default=None),
    merchant: dict = Depends(get_current_merchant),
    store: dict = Depends(get_current_store),
) -> PaginatedResponse:
    """List scans for a store (paginated, most recent first)."""
    supabase = get_supabase_service()

    query = (
        supabase.table("scans")
        .select("*", count="exact")
        .eq("store_id", store_id)
        .eq("merchant_id", merchant["id"])
        .order("created_at", desc=True)
        .limit(limit + 1)  # Fetch one extra to detect has_next
    )

    if status:
        query = query.eq("status", status)

    if cursor:
        try:
            cursor_id = base64.b64decode(cursor).decode()
            query = query.lt("id", cursor_id)
        except Exception:
            pass

    result = query.execute()
    rows = result.data or []
    has_next = len(rows) > limit
    items = rows[:limit]

    next_cursor = None
    if has_next and items:
        next_cursor = base64.b64encode(items[-1]["id"].encode()).decode()

    data = [
        ScanListItem(
            id=s["id"],
            status=s["status"],
            trigger=s.get("trigger", "manual"),
            modules=s.get("modules", ["health"]),
            score=s.get("score"),
            mobile_score=s.get("mobile_score"),
            desktop_score=s.get("desktop_score"),
            issues_count=s.get("issues_count", 0),
            critical_count=s.get("critical_count", 0),
            partial_scan=s.get("partial_scan", False),
            duration_ms=s.get("duration_ms"),
            started_at=s.get("started_at"),
            completed_at=s.get("completed_at"),
            created_at=s["created_at"],
        )
        for s in items
    ]

    return PaginatedResponse(
        data=[d.model_dump() for d in data],
        pagination=PaginationMeta(
            has_next=has_next,
            next_cursor=next_cursor,
            total_count=result.count,
        ),
    )


@router.get("/scans/{scan_id}")
async def get_scan_detail(
    store_id: str,
    scan_id: str,
    merchant: dict = Depends(get_current_merchant),
    store: dict = Depends(get_current_store),
) -> ScanDetailResponse:
    """Get detailed scan results with issues."""
    supabase = get_supabase_service()

    # Fetch scan
    scan_result = (
        supabase.table("scans")
        .select("*")
        .eq("id", scan_id)
        .eq("store_id", store_id)
        .eq("merchant_id", merchant["id"])
        .maybe_single()
        .execute()
    )

    if not scan_result.data:
        raise ScanError(
            code=ErrorCode.SCAN_NOT_FOUND,
            message="Scan not found",
            status_code=404,
        )

    scan = scan_result.data

    # Fetch issues
    issues_result = (
        supabase.table("scan_issues")
        .select("*")
        .eq("scan_id", scan_id)
        .order("severity")
        .execute()
    )

    issues = [
        ScanIssueResponse(
            id=i["id"],
            module=i["module"],
            scanner=i["scanner"],
            severity=i["severity"],
            title=i["title"],
            description=i["description"],
            impact=i.get("impact"),
            impact_value=i.get("impact_value"),
            impact_unit=i.get("impact_unit"),
            fix_type=i.get("fix_type"),
            fix_description=i.get("fix_description"),
            auto_fixable=i.get("auto_fixable", False),
            fix_applied=i.get("fix_applied", False),
            dismissed=i.get("dismissed", False),
        )
        for i in (issues_result.data or [])
    ]

    return ScanDetailResponse(
        id=scan["id"],
        status=scan["status"],
        score=scan.get("score"),
        mobile_score=scan.get("mobile_score"),
        desktop_score=scan.get("desktop_score"),
        modules=scan.get("modules", ["health"]),
        trigger=scan.get("trigger", "manual"),
        partial_scan=scan.get("partial_scan", False),
        duration_ms=scan.get("duration_ms"),
        progress=scan.get("progress") or 0,
        current_step=scan.get("current_step"),
        issues=issues,
        errors=[],
        started_at=scan.get("started_at"),
        completed_at=scan.get("completed_at"),
    )


@router.get("/health")
async def get_health_score(
    store_id: str,
    merchant: dict = Depends(get_current_merchant),
    store: dict = Depends(get_current_store),
) -> HealthResponse:
    """Get current health score + trend + history."""
    supabase = get_supabase_service()

    # Fetch recent completed scans
    scans_result = (
        supabase.table("scans")
        .select("score, mobile_score, desktop_score, issues_count, critical_count, completed_at")
        .eq("store_id", store_id)
        .eq("merchant_id", merchant["id"])
        .eq("status", "completed")
        .order("completed_at", desc=True)
        .limit(10)
        .execute()
    )

    scans = scans_result.data or []

    if not scans:
        return HealthResponse()

    latest = scans[0]
    previous = scans[1] if len(scans) > 1 else None

    # Calculate trend
    trend = "stable"
    trend_delta = 0
    if previous and latest.get("score") is not None and previous.get("score") is not None:
        trend_delta = latest["score"] - previous["score"]
        if trend_delta >= 3:
            trend = "up"
        elif trend_delta <= -3:
            trend = "down"

    # Build history
    history = [
        HealthScoreHistory(
            date=s["completed_at"][:10] if s.get("completed_at") else "",
            score=s["score"],
        )
        for s in scans
        if s.get("score") is not None
    ]

    return HealthResponse(
        score=latest.get("score"),
        mobile_score=latest.get("mobile_score"),
        desktop_score=latest.get("desktop_score"),
        trend=trend,
        trend_delta=trend_delta,
        last_scan_at=latest.get("completed_at"),
        issues_count=latest.get("issues_count", 0),
        critical_count=latest.get("critical_count", 0),
        previous_score=previous.get("score") if previous else None,
        history=history,
    )
