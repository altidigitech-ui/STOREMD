"""Tests for GhostBillingDetector scanner."""

import pytest
from unittest.mock import AsyncMock

from app.agent.analyzers.ghost_billing import GhostBillingDetector
from tests.mocks.shopify_responses import MOCK_APPS_DATA, MOCK_RECURRING_CHARGES


@pytest.fixture
def scanner():
    return GhostBillingDetector()


@pytest.fixture
def mock_shopify():
    client = AsyncMock()
    client.shop_domain = "teststore.myshopify.com"
    return client


@pytest.mark.unit
@pytest.mark.asyncio
async def test_detects_ghost_billing(scanner, mock_shopify):
    """Happy path: detects an app billing without being installed."""
    mock_shopify.graphql.return_value = MOCK_APPS_DATA
    mock_shopify.rest_get.return_value = MOCK_RECURRING_CHARGES

    result = await scanner.scan("store-1", mock_shopify, [])

    assert len(result.issues) == 1
    assert result.issues[0].scanner == "ghost_billing"
    assert result.issues[0].severity == "major"
    assert "Old SEO App" in result.issues[0].title
    assert result.metrics["ghost_charges"] == 1
    assert result.metrics["total_ghost_monthly"] == 9.99


@pytest.mark.unit
@pytest.mark.asyncio
async def test_no_ghosts(scanner, mock_shopify):
    """No ghost billing — all charges match installed apps."""
    mock_shopify.graphql.return_value = MOCK_APPS_DATA
    mock_shopify.rest_get.return_value = {
        "recurring_application_charges": [
            {
                "id": 1,
                "name": "Privy",
                "status": "active",
                "price": "29.99",
                "created_at": "2026-01-01T00:00:00Z",
            },
        ]
    }

    result = await scanner.scan("store-1", mock_shopify, [])

    assert len(result.issues) == 0
    assert result.metrics["ghost_charges"] == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shopify_api_error(scanner, mock_shopify):
    """Shopify API failure propagates as ShopifyError."""
    from app.core.exceptions import ErrorCode, ShopifyError

    mock_shopify.rest_get.side_effect = ShopifyError(
        code=ErrorCode.SHOPIFY_API_UNAVAILABLE,
        message="Shopify down",
        status_code=503,
    )

    with pytest.raises(ShopifyError):
        await scanner.scan("store-1", mock_shopify, [])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_should_run_plan(scanner):
    """Verify should_run based on plan and module."""
    assert await scanner.should_run(["health"], "starter") is True
    assert await scanner.should_run(["health"], "pro") is True
    assert await scanner.should_run(["health"], "agency") is True
    assert await scanner.should_run(["health"], "free") is False  # requires starter
    assert await scanner.should_run(["listings"], "pro") is False  # wrong module
