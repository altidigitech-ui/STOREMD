"""Listings API routes — catalogue scan results, priorities, rewrite, bulk."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.core.exceptions import AuthError, ErrorCode, ListingError
from app.dependencies import (
    get_current_merchant,
    get_current_store,
    get_supabase_service,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/stores/{store_id}/listings", tags=["listings"])


PLAN_HIERARCHY = {"free": 0, "starter": 1, "pro": 2, "agency": 3}


def _require_plan(merchant: dict, required: str, feature: str) -> None:
    plan = merchant.get("plan", "free")
    if PLAN_HIERARCHY.get(plan, 0) < PLAN_HIERARCHY.get(required, 0):
        raise AuthError(
            code=ErrorCode.PLAN_REQUIRED,
            message=f"Feature '{feature}' requires {required} plan or above",
            status_code=403,
            context={"feature": feature, "required_plan": required},
        )


# ---------------------------------------------------------------------------
# GET /listings/scan — catalogue scan results (paginated)
# ---------------------------------------------------------------------------


@router.get("/scan")
async def get_listings_scan(
    store_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    sort: str = Query(default="score_asc"),
    min_score: int | None = Query(default=None, ge=0, le=100),
    max_score: int | None = Query(default=None, ge=0, le=100),
    merchant: dict = Depends(get_current_merchant),
    store: dict = Depends(get_current_store),
) -> dict:
    """Return paginated product analyses with score/breakdown."""
    supabase = get_supabase_service()

    sort_column = "score"
    descending = sort in {"score_desc", "revenue_desc", "priority"}
    if sort == "revenue_desc":
        sort_column = "revenue_30d"
    elif sort == "priority":
        sort_column = "priority_rank"

    query = (
        supabase.table("product_analyses")
        .select("*", count="exact")
        .eq("store_id", store_id)
        .eq("merchant_id", merchant["id"])
        .order(sort_column, desc=descending)
        .limit(limit + 1)
    )

    if min_score is not None:
        query = query.gte("score", min_score)
    if max_score is not None:
        query = query.lte("score", max_score)

    try:
        result = query.execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("listings_scan_query_failed", error=str(exc))
        return {
            "products_scanned": 0,
            "avg_score": 0,
            "data": [],
            "pagination": {"has_next": False, "next_cursor": None},
        }

    rows = result.data or []
    has_next = len(rows) > limit
    items = rows[:limit]

    avg_score = (
        sum((r.get("score") or 0) for r in rows) / len(rows) if rows else 0
    )

    data = [
        {
            "shopify_product_id": r.get("shopify_product_id"),
            "title": r.get("title"),
            "handle": r.get("handle"),
            "score": r.get("score"),
            "title_score": r.get("title_score"),
            "description_score": r.get("description_score"),
            "images_score": r.get("images_score"),
            "seo_score": r.get("seo_score"),
            "revenue_30d": r.get("revenue_30d"),
            "orders_30d": r.get("orders_30d"),
            "priority_rank": r.get("priority_rank"),
            "issues": r.get("issues") or [],
        }
        for r in items
    ]

    return {
        "products_scanned": result.count or len(rows),
        "avg_score": round(avg_score),
        "data": data,
        "pagination": {
            "has_next": has_next,
            "next_cursor": None,  # cursor support TBD with stable sort
            "total_count": result.count,
        },
    }


# ---------------------------------------------------------------------------
# GET /listings/priorities — top products to improve (low score + high revenue)
# ---------------------------------------------------------------------------


@router.get("/priorities")
async def get_listings_priorities(
    store_id: str,
    merchant: dict = Depends(get_current_merchant),
    store: dict = Depends(get_current_store),
) -> dict:
    """Return the top products to improve (revenue-weighted)."""
    _require_plan(merchant, "starter", "listing_priority")

    supabase = get_supabase_service()
    try:
        result = (
            supabase.table("product_analyses")
            .select("*")
            .eq("store_id", store_id)
            .eq("merchant_id", merchant["id"])
            .order("priority_rank")
            .limit(20)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("priorities_query_failed", error=str(exc))
        return {"data": []}

    items = result.data or []
    data = [
        {
            "shopify_product_id": r.get("shopify_product_id"),
            "title": r.get("title"),
            "score": r.get("score"),
            "revenue_30d": r.get("revenue_30d"),
            "potential_uplift_pct": r.get("potential_uplift_pct"),
            "priority_rank": r.get("priority_rank"),
            "top_issue": (r.get("issues") or [{}])[0].get("suggestion"),
        }
        for r in items
    ]
    return {"data": data}


# ---------------------------------------------------------------------------
# POST /listings/{product_id}/rewrite
# ---------------------------------------------------------------------------


class RewriteRequest(BaseModel):
    elements: list[str] = Field(default_factory=list, max_length=10)
    tone: str = "professional"
    keep_strong: bool = True


@router.post("/{product_id}/rewrite")
async def rewrite_listing(
    store_id: str,
    product_id: str,
    request: RewriteRequest,
    merchant: dict = Depends(get_current_merchant),
    store: dict = Depends(get_current_store),
) -> dict:
    """Generate a rewrite for the requested product elements."""
    _require_plan(merchant, "starter", "listing_rewrite")

    if not request.elements:
        raise ListingError(
            code=ErrorCode.INVALID_INPUT,
            message="elements list cannot be empty",
            status_code=422,
        )

    # Claude API call wired through the agent's claude.py service.
    # We return a preview here — the merchant must POST /fixes/{id}/apply.
    try:
        from app.services.claude import claude_generate_fix

        rewrites = []
        for element in request.elements:
            prompt = (
                "Rewrite the following Shopify product field for clarity, "
                f"SEO, and AI-shopping compatibility. Field: {element}. "
                f"Tone: {request.tone}. "
                f"Keep strong sections: {request.keep_strong}.\n"
                f"Product GID: {product_id}.\n"
                "Respond as JSON: "
                '{"element": "<field>", "before": "<existing>", '
                '"after": "<rewritten>"}.'
            )
            text = await claude_generate_fix(prompt)
            rewrites.append(
                {
                    "element": element,
                    "before": "",
                    "after": text,
                    "applied": False,
                }
            )
    except Exception as exc:  # noqa: BLE001
        raise ListingError(
            code=ErrorCode.LISTING_REWRITE_FAILED,
            message=f"Rewrite failed: {exc}",
            status_code=502,
        ) from exc

    return {
        "product_id": product_id,
        "rewrites": rewrites,
    }


# ---------------------------------------------------------------------------
# POST /listings/bulk — bulk operation (background task)
# ---------------------------------------------------------------------------


VALID_BULK_OPS = {
    "generate_alt_text",
    "rewrite_descriptions",
    "optimize_seo",
    "fill_metafields",
}


class BulkRequest(BaseModel):
    operation: str
    product_ids: list[str] = Field(min_length=1, max_length=500)
    options: dict = Field(default_factory=dict)


@router.post("/bulk", status_code=202)
async def bulk_operation(
    store_id: str,
    request: BulkRequest,
    merchant: dict = Depends(get_current_merchant),
    store: dict = Depends(get_current_store),
) -> dict:
    """Queue a bulk operation for background processing (Pro+)."""
    _require_plan(merchant, "pro", "bulk_operations")

    if request.operation not in VALID_BULK_OPS:
        raise ListingError(
            code=ErrorCode.INVALID_INPUT,
            message=(
                f"Invalid operation. Valid: {', '.join(sorted(VALID_BULK_OPS))}"
            ),
            status_code=422,
        )

    supabase = get_supabase_service()
    try:
        result = (
            supabase.table("bulk_operations")
            .insert(
                {
                    "merchant_id": merchant["id"],
                    "store_id": store_id,
                    "operation": request.operation,
                    "product_count": len(request.product_ids),
                    "product_ids": request.product_ids,
                    "options": request.options,
                    "status": "pending",
                }
            )
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        raise ListingError(
            code=ErrorCode.BULK_IMPORT_FAILED,
            message=f"Could not enqueue bulk operation: {exc}",
            status_code=502,
        ) from exc

    record = result.data[0]

    return {
        "bulk_operation_id": record["id"],
        "status": record.get("status", "pending"),
        "product_count": len(request.product_ids),
        "operation": request.operation,
    }
