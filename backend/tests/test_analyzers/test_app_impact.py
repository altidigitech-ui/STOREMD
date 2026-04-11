"""Tests for AppImpactScanner."""

import pytest
from unittest.mock import AsyncMock

from app.agent.analyzers.app_impact import AppImpactScanner
from tests.mocks.shopify_responses import MOCK_APPS_DATA, MOCK_SCRIPT_TAGS


@pytest.fixture
def scanner():
    return AppImpactScanner()


@pytest.fixture
def mock_shopify():
    client = AsyncMock()
    client.shop_domain = "teststore.myshopify.com"
    return client


@pytest.mark.unit
@pytest.mark.asyncio
async def test_detects_app_impact(scanner, mock_shopify):
    """Detects apps with script tags and estimates impact."""
    mock_shopify.graphql.side_effect = [MOCK_APPS_DATA, MOCK_SCRIPT_TAGS]

    result = await scanner.scan("store-1", mock_shopify, [])

    assert result.metrics["apps_count"] == 2
    assert result.metrics["total_scripts"] == 2
    assert result.metrics["total_impact_ms"] > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_no_scripts(scanner, mock_shopify):
    """Store with apps but no script tags — no impact issues."""
    mock_shopify.graphql.side_effect = [
        MOCK_APPS_DATA,
        {"scriptTags": {"edges": []}},
    ]

    result = await scanner.scan("store-1", mock_shopify, [])

    assert result.metrics["total_scripts"] == 0
    # No heavy-app issues (only unattributed warning won't appear with 0 scripts)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shopify_error(scanner, mock_shopify):
    """Shopify API error propagates."""
    from app.core.exceptions import ErrorCode, ShopifyError

    mock_shopify.graphql.side_effect = ShopifyError(
        code=ErrorCode.SHOPIFY_RATE_LIMIT,
        message="Rate limited",
        status_code=429,
    )

    with pytest.raises(ShopifyError):
        await scanner.scan("store-1", mock_shopify, [])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_should_run_plan(scanner):
    """Verify should_run based on plan and module."""
    assert await scanner.should_run(["health"], "starter") is True
    assert await scanner.should_run(["health"], "pro") is True
    assert await scanner.should_run(["health"], "free") is False
    assert await scanner.should_run(["listings"], "starter") is False
