"""Feedback route — Ouroboros learning loop."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.agent.learner import OuroborosLearner
from app.agent.memory import get_store_memory
from app.dependencies import get_current_merchant, get_supabase_service

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1", tags=["feedback"])

VALID_REASON_CATEGORIES = {
    "not_relevant", "too_risky", "will_do_later",
    "disagree", "already_fixed", "other",
}


class FeedbackRequest(BaseModel):
    issue_id: str
    accepted: bool
    reason: str | None = Field(default=None, max_length=500)
    reason_category: str | None = None

    def model_post_init(self, __context: object) -> None:
        if self.reason_category and self.reason_category not in VALID_REASON_CATEGORIES:
            msg = f"Invalid reason_category. Valid: {', '.join(sorted(VALID_REASON_CATEGORIES))}"
            raise ValueError(msg)


@router.post("/feedback", status_code=201)
async def create_feedback(
    request: FeedbackRequest,
    merchant: dict = Depends(get_current_merchant),
) -> dict:
    """Record merchant feedback on a recommendation (Ouroboros)."""
    supabase = get_supabase_service()

    # Look up the issue to get store_id and scan_id
    issue = (
        supabase.table("scan_issues")
        .select("id, store_id, scan_id, scanner")
        .eq("id", request.issue_id)
        .eq("merchant_id", merchant["id"])
        .maybe_single()
        .execute()
    )

    store_id = issue.data["store_id"] if issue.data else None
    scan_id = issue.data.get("scan_id") if issue.data else None

    result = supabase.table("feedback").insert({
        "merchant_id": merchant["id"],
        "store_id": store_id,
        "scan_id": scan_id,
        "issue_id": request.issue_id,
        "accepted": request.accepted,
        "reason": request.reason,
        "reason_category": request.reason_category,
        "recommendation_type": issue.data.get("scanner") if issue.data else None,
    }).execute()

    feedback = result.data[0]

    logger.info(
        "feedback_recorded",
        merchant_id=merchant["id"],
        issue_id=request.issue_id,
        accepted=request.accepted,
        category=request.reason_category,
    )

    # Ouroboros — push the feedback into Mem0 so the next scan can adapt.
    # Failures here must NOT break the API response: feedback is already
    # persisted in DB, the LEARN layer is best-effort.
    try:
        learner = OuroborosLearner(get_store_memory())
        await learner.process_feedback(
            merchant_id=merchant["id"],
            issue_id=request.issue_id,
            accepted=request.accepted,
            reason=request.reason,
            reason_category=request.reason_category,
            supabase=supabase,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "ouroboros_process_failed",
            merchant_id=merchant["id"],
            issue_id=request.issue_id,
            error=str(exc),
        )

    return {
        "id": feedback["id"],
        "accepted": request.accepted,
        "reason_category": request.reason_category,
        "created_at": feedback["created_at"],
    }
