"""Tests for ListingAnalyzer scanner."""

import pytest
from unittest.mock import AsyncMock

from app.agent.analyzers.listing_analyzer import ListingAnalyzer

MOCK_PRODUCTS_LOW_SCORE = {
    "products": {
        "edges": [
            {
                "cursor": "c1",
                "node": {
                    "id": "gid://shopify/Product/1",
                    "title": "X",
                    "handle": "x",
                    "status": "ACTIVE",
                    "productType": "",
                    "descriptionHtml": "",
                    "seo": {"title": None, "description": None},
                    "images": {"edges": []},
                    "variants": {"edges": [
                        {"node": {"id": "v1", "title": "Default", "sku": "", "barcode": None, "price": "10.00"}},
                    ]},
                },
            },
        ],
        "pageInfo": {"hasNextPage": False, "endCursor": "c1"},
    }
}

MOCK_PRODUCTS_GOOD = {
    "products": {
        "edges": [
            {
                "cursor": "c1",
                "node": {
                    "id": "gid://shopify/Product/2",
                    "title": "Premium Organic Face Cream - Anti-Aging Moisturizer",
                    "handle": "premium-organic-face-cream",
                    "status": "ACTIVE",
                    "productType": "skincare",
                    "descriptionHtml": (
                        "<p>Our premium organic face cream is crafted with natural ingredients "
                        "including vitamin E, hyaluronic acid, and jojoba oil. Perfect for daily "
                        "use, this lightweight moisturizer absorbs quickly without leaving a "
                        "greasy residue. Suitable for all skin types including sensitive skin.</p>"
                        "<ul><li>100% organic ingredients</li>"
                        "<li>Cruelty-free and vegan</li></ul>"
                    ),
                    "seo": {
                        "title": "Premium Organic Face Cream | Anti-Aging Moisturizer",
                        "description": "Discover our premium organic face cream with vitamin E and hyaluronic acid. Lightweight, cruelty-free moisturizer for all skin types.",
                    },
                    "images": {"edges": [
                        {"node": {"id": "img1", "altText": "Organic face cream jar", "url": "https://img1.jpg", "width": 800, "height": 800}},
                        {"node": {"id": "img2", "altText": "Face cream texture closeup", "url": "https://img2.jpg", "width": 800, "height": 800}},
                        {"node": {"id": "img3", "altText": "Face cream ingredients", "url": "https://img3.jpg", "width": 800, "height": 800}},
                    ]},
                    "variants": {"edges": [
                        {"node": {"id": "v1", "title": "50ml", "sku": "FC50", "barcode": "1234567890", "price": "29.99"}},
                    ]},
                },
            },
        ],
        "pageInfo": {"hasNextPage": False, "endCursor": "c1"},
    }
}

MOCK_PRODUCTS_EMPTY = {
    "products": {
        "edges": [],
        "pageInfo": {"hasNextPage": False, "endCursor": None},
    }
}


@pytest.fixture
def scanner():
    return ListingAnalyzer()


@pytest.fixture
def mock_shopify():
    client = AsyncMock()
    client.shop_domain = "teststore.myshopify.com"
    return client


@pytest.mark.unit
@pytest.mark.asyncio
async def test_detects_low_score_products(scanner, mock_shopify):
    """Detects products with low listing quality."""
    mock_shopify.graphql.return_value = MOCK_PRODUCTS_LOW_SCORE

    result = await scanner.scan("store-1", mock_shopify, [])

    assert len(result.issues) >= 1
    assert result.issues[0].scanner == "listing_analyzer"
    assert result.issues[0].module == "listings"
    assert result.metrics["products_scanned"] == 1
    assert result.metrics["products_below_50"] >= 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_all_products_good(scanner, mock_shopify):
    """Well-optimized products don't generate issues."""
    mock_shopify.graphql.return_value = MOCK_PRODUCTS_GOOD

    result = await scanner.scan("store-1", mock_shopify, [])

    # Good product should score above 50
    assert result.metrics["products_scanned"] == 1
    assert result.metrics["avg_score"] >= 50


@pytest.mark.unit
@pytest.mark.asyncio
async def test_empty_catalog(scanner, mock_shopify):
    """Store with no products returns empty results."""
    mock_shopify.graphql.return_value = MOCK_PRODUCTS_EMPTY

    result = await scanner.scan("store-1", mock_shopify, [])

    assert len(result.issues) == 0
    assert result.metrics["products_scanned"] == 0
    assert result.metrics["avg_score"] == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_should_run_plan(scanner):
    """Listing analyzer is available on all plans (free)."""
    assert await scanner.should_run(["listings"], "free") is True
    assert await scanner.should_run(["listings"], "starter") is True
    assert await scanner.should_run(["listings"], "pro") is True
    assert await scanner.should_run(["health"], "pro") is False  # wrong module
