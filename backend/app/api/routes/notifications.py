"""Notification routes — list and mark as read."""

from __future__ import annotations

import base64

import structlog
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.dependencies import get_current_merchant, get_supabase_service
from app.core.exceptions import AppError, ErrorCode

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1", tags=["notifications"])


@router.get("/notifications")
async def list_notifications(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    unread_only: bool = Query(default=False),
    merchant: dict = Depends(get_current_merchant),
) -> dict:
    """List notifications (paginated, most recent first)."""
    supabase = get_supabase_service()

    query = (
        supabase.table("notifications")
        .select("*", count="exact")
        .eq("merchant_id", merchant["id"])
        .order("sent_at", desc=True)
        .limit(limit + 1)
    )

    if unread_only:
        query = query.eq("read", False)

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

    # Unread count
    unread_result = (
        supabase.table("notifications")
        .select("id", count="exact")
        .eq("merchant_id", merchant["id"])
        .eq("read", False)
        .execute()
    )

    return {
        "data": [
            {
                "id": n["id"],
                "channel": n["channel"],
                "title": n["title"],
                "body": n["body"],
                "action_url": n.get("action_url"),
                "category": n.get("category"),
                "read": n.get("read", False),
                "sent_at": n.get("sent_at"),
            }
            for n in items
        ],
        "unread_count": unread_result.count or 0,
        "pagination": {
            "has_next": has_next,
            "next_cursor": next_cursor,
        },
    }


@router.patch("/notifications/{notification_id}/read", status_code=204)
async def mark_notification_read(
    notification_id: str,
    merchant: dict = Depends(get_current_merchant),
) -> JSONResponse:
    """Mark a notification as read."""
    supabase = get_supabase_service()
    from datetime import UTC, datetime

    result = (
        supabase.table("notifications")
        .update({"read": True, "read_at": datetime.now(UTC).isoformat()})
        .eq("id", notification_id)
        .eq("merchant_id", merchant["id"])
        .execute()
    )

    if not result.data:
        raise AppError(
            code=ErrorCode.NOTIFICATION_NOT_FOUND,
            message="Notification not found",
            status_code=404,
        )

    return JSONResponse(status_code=204, content=None)
