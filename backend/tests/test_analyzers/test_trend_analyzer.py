"""Unit tests for TrendAnalyzer."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from app.agent.analyzers.trend_analyzer import TrendAnalyzer


@pytest.fixture
def scanner() -> TrendAnalyzer:
    return TrendAnalyzer()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_detects_declining_trend(
    scanner: TrendAnalyzer, monkeypatch
) -> None:
    """3+ consecutive declining scans → major issue."""
    # newest first
    fake_scores = [50, 55, 60, 67]

    async def fake_fetch(store_id):
        return fake_scores

    monkeypatch.setattr(scanner, "_fetch_recent_scores", fake_fetch)

    result = await scanner.scan("store-1", AsyncMock(), [])

    assert result.metrics["trend"] == "down"
    assert result.metrics["streak"] >= 3
    assert any("declining" in i.title.lower() for i in result.issues)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stable_trend_no_issues(
    scanner: TrendAnalyzer, monkeypatch
) -> None:
    fake_scores = [70, 70, 70]

    async def fake_fetch(store_id):
        return fake_scores

    monkeypatch.setattr(scanner, "_fetch_recent_scores", fake_fetch)

    result = await scanner.scan("store-1", AsyncMock(), [])

    assert result.metrics["trend"] == "stable"
    assert result.metrics["delta"] == 0
    assert result.issues == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_insufficient_history_returns_no_trend(
    scanner: TrendAnalyzer, monkeypatch
) -> None:
    async def fake_fetch(store_id):
        return [67]  # only one scan

    monkeypatch.setattr(scanner, "_fetch_recent_scores", fake_fetch)
    result = await scanner.scan("store-1", AsyncMock(), [])

    assert result.metrics["trend"] == "stable"
    assert result.issues == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_should_run_plan(scanner: TrendAnalyzer) -> None:
    assert await scanner.should_run(["health"], "free") is True
    assert await scanner.should_run(["health"], "starter") is True
    assert await scanner.should_run(["listings"], "free") is False
