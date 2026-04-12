"""Unit tests for VariantOrganizer."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from app.agent.analyzers.variant_organizer import VariantOrganizer


def _product(
    pid: str,
    *,
    variants: list[dict],
    title: str = "Test product",
    total_variants: int | None = None,
) -> dict:
    return {
        "id": pid,
        "title": title,
        "handle": pid.lower(),
        "totalVariants": total_variants or len(variants),
        "variants": {
            "edges": [{"node": v} for v in variants],
        },
    }


def _response(products: list[dict]) -> dict:
    return {
        "products": {
            "edges": [{"cursor": "c", "node": p} for p in products],
            "pageInfo": {"hasNextPage": False, "endCursor": "c"},
        }
    }


@pytest.fixture
def scanner() -> VariantOrganizer:
    return VariantOrganizer()


@pytest.fixture
def mock_shopify():
    return AsyncMock()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_detects_duplicate_variants(
    scanner: VariantOrganizer, mock_shopify: AsyncMock
) -> None:
    """Duplicate variant titles + missing SKU + identical prices → 3 issues."""
    product = _product(
        "p1",
        variants=[
            {"id": "v1", "title": "Red", "sku": "", "price": "29.99"},
            {"id": "v2", "title": "Red", "sku": "", "price": "29.99"},
        ],
    )
    mock_shopify.graphql.return_value = _response([product])

    result = await scanner.scan("store-1", mock_shopify, [])

    titles = [i.title for i in result.issues]
    assert any("Duplicate variant titles" in t for t in titles)
    assert any("without SKU" in t for t in titles)
    assert any("identical prices" in t for t in titles)

    # Metrics match.
    assert result.metrics["duplicate_variants"] == 1
    assert result.metrics["missing_sku"] == 1
    assert result.metrics["identical_prices"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clean_variants_no_issues(
    scanner: VariantOrganizer, mock_shopify: AsyncMock
) -> None:
    product = _product(
        "p1",
        variants=[
            {"id": "v1", "title": "Red / S", "sku": "SKU-R-S", "price": "29.99"},
            {"id": "v2", "title": "Red / M", "sku": "SKU-R-M", "price": "34.99"},
            {"id": "v3", "title": "Blue / S", "sku": "SKU-B-S", "price": "29.99"},
        ],
    )
    mock_shopify.graphql.return_value = _response([product])

    result = await scanner.scan("store-1", mock_shopify, [])

    assert result.issues == []
    assert result.metrics["products_scanned"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_detects_too_many_variants(
    scanner: VariantOrganizer, mock_shopify: AsyncMock
) -> None:
    product = _product(
        "p1",
        variants=[
            {"id": f"v{i}", "title": f"V{i}", "sku": f"S{i}", "price": str(i)}
            for i in range(10)
        ],
        total_variants=150,  # hypothetical — GraphQL only returns first 100
    )
    mock_shopify.graphql.return_value = _response([product])

    result = await scanner.scan("store-1", mock_shopify, [])
    titles = [i.title for i in result.issues]
    assert any("150 variants" in t for t in titles)
    assert result.metrics["too_many_variants"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_should_run_plan(scanner: VariantOrganizer) -> None:
    assert await scanner.should_run(["listings"], "pro") is True
    assert await scanner.should_run(["listings"], "agency") is True
    assert await scanner.should_run(["listings"], "starter") is False
    assert await scanner.should_run(["listings"], "free") is False
    assert await scanner.should_run(["health"], "pro") is False
