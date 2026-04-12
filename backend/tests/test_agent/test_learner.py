"""Unit tests for the OuroborosLearner."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agent.learner import OuroborosLearner


def _supabase_with_issue(issue: dict) -> MagicMock:
    """Return a Supabase mock that yields `issue` for the issue lookup
    and 1 for the feedback count (so pattern analysis is NOT triggered)."""
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.maybe_single.return_value = table

    issue_response = MagicMock(data=issue)
    count_response = MagicMock(count=1)

    # Two .execute() calls happen: one for the issue lookup, one for the count.
    table.execute.side_effect = [issue_response, count_response]

    supabase = MagicMock()
    supabase.table.return_value = table
    return supabase


@pytest.mark.unit
@pytest.mark.asyncio
async def test_feedback_stored_in_memory() -> None:
    memory = AsyncMock()
    learner = OuroborosLearner(memory)

    supabase = _supabase_with_issue(
        {
            "title": "Remove residual Privy code",
            "scanner": "residue_detector",
            "severity": "major",
        }
    )

    await learner.process_feedback(
        merchant_id="merchant-1",
        issue_id="issue-1",
        accepted=True,
        reason=None,
        reason_category=None,
        supabase=supabase,
    )

    memory.learn_from_feedback.assert_awaited_once()
    kwargs = memory.learn_from_feedback.await_args.kwargs
    assert kwargs["merchant_id"] == "merchant-1"
    assert kwargs["accepted"] is True
    assert kwargs["scanner"] == "residue_detector"
    assert kwargs["issue_title"] == "Remove residual Privy code"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rejected_feedback_includes_reason() -> None:
    memory = AsyncMock()
    learner = OuroborosLearner(memory)

    supabase = _supabase_with_issue(
        {
            "title": "Uninstall Privy",
            "scanner": "app_impact",
            "severity": "critical",
        }
    )

    await learner.process_feedback(
        merchant_id="merchant-1",
        issue_id="issue-2",
        accepted=False,
        reason="need it for popups",
        reason_category="disagree",
        supabase=supabase,
    )

    kwargs = memory.learn_from_feedback.await_args.kwargs
    assert kwargs["accepted"] is False
    assert kwargs["reason"] == "need it for popups"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_analyze_patterns_writes_agent_memory() -> None:
    memory = AsyncMock()
    memory.recall_merchant.return_value = [
        {
            "memory": (
                "Recommendation 'Uninstall Privy' (scanner: app_impact, "
                "severity: critical): REJECTED. Reason: need it."
            )
        },
        {
            "memory": (
                "Recommendation 'Uninstall Klaviyo' (scanner: app_impact, "
                "severity: critical): REJECTED."
            )
        },
        {
            "memory": (
                "Recommendation 'Add alt text' (scanner: image_optimizer, "
                "severity: minor): ACCEPTED."
            )
        },
    ]

    learner = OuroborosLearner(memory)
    rates = await learner.analyze_patterns("merchant-1")

    assert rates["app_impact"] == 0.0
    assert rates["image_optimizer"] == 1.0
    assert memory.remember_agent.await_count == 2
