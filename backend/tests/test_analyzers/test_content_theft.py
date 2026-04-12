"""Unit tests for the ContentTheftScanner placeholder."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from app.agent.analyzers.content_theft import ContentTheftScanner


@pytest.fixture
def scanner() -> ContentTheftScanner:
    return ContentTheftScanner()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_placeholder_returns_empty(
    scanner: ContentTheftScanner,
) -> None:
    result = await scanner.scan("store-1", AsyncMock(), [])
    assert result.issues == []
    assert result.metrics["status"] == "coming_soon"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_should_run_plan(scanner: ContentTheftScanner) -> None:
    assert await scanner.should_run(["health"], "pro") is True
    assert await scanner.should_run(["health"], "agency") is True
    assert await scanner.should_run(["health"], "starter") is False
    assert await scanner.should_run(["health"], "free") is False
