"""Unit tests for AgenticReadinessScanner."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from app.agent.analyzers.agentic_readiness import AgenticReadinessScanner


def _product(
    pid: str,
    *,
    barcode: str | None = None,
    metafields: dict[tuple[str, str], str] | None = None,
    description: str = "",
    product_type: str = "",
) -> dict:
    metafields = metafields or {}
    return {
        "id": pid,
        "title": pid,
        "descriptionHtml": description,
        "productType": product_type,
        "status": "ACTIVE",
        "variants": {
            "edges": [
                {"node": {"barcode": barcode, "sku": "X"}},
            ]
        },
        "metafields": {
            "edges": [
                {
                    "node": {
                        "namespace": ns,
                        "key": key,
                        "value": value,
                        "type": "single_line_text_field",
                    }
                }
                for (ns, key), value in metafields.items()
            ]
        },
    }


def _products_response(products: list[dict]) -> dict:
    return {
        "products": {
            "edges": [{"cursor": "c", "node": p} for p in products],
            "pageInfo": {"hasNextPage": False, "endCursor": "c"},
        }
    }


def _theme_no_schema() -> dict:
    return {
        "themes": {
            "edges": [
                {
                    "node": {
                        "id": "t1",
                        "files": {
                            "edges": [
                                {
                                    "node": {
                                        "filename": "templates/product.json",
                                        "body": {"content": "{}"},
                                    }
                                }
                            ]
                        },
                    }
                }
            ]
        }
    }


def _theme_with_schema() -> dict:
    return {
        "themes": {
            "edges": [
                {
                    "node": {
                        "id": "t1",
                        "files": {
                            "edges": [
                                {
                                    "node": {
                                        "filename": "templates/product.json",
                                        "body": {
                                            "content": (
                                                '<script type="application/ld+json">'
                                                '{"@context":"schema.org",'
                                                '"@type":"Product"}</script>'
                                            )
                                        },
                                    }
                                }
                            ]
                        },
                    }
                }
            ]
        }
    }


@pytest.fixture
def scanner() -> AgenticReadinessScanner:
    return AgenticReadinessScanner()


@pytest.fixture
def mock_shopify():
    return AsyncMock()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_detects_missing_gtin(
    scanner: AgenticReadinessScanner, mock_shopify: AsyncMock
) -> None:
    mock_shopify.graphql.side_effect = [
        _products_response([_product("p1")]),
        _theme_no_schema(),
    ]

    result = await scanner.scan("store-1", mock_shopify, [])

    metrics = result.metrics["checks"]
    assert metrics["gtin_present"]["status"] == "fail"
    assert metrics["gtin_present"]["affected_products"] == 1
    titles = [i.title for i in result.issues]
    assert any("missing GTIN" in t for t in titles)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_all_checks_pass(
    scanner: AgenticReadinessScanner, mock_shopify: AsyncMock
) -> None:
    long_description = (
        "<p>This handcrafted t-shirt is designed for everyday comfort and "
        "ethical sourcing. Cut from breathable organic cotton, it pairs a "
        "relaxed silhouette with a soft hand feel that holds up wash after "
        "wash without losing shape, color, or structure. Each piece is "
        "produced in a Fair Trade certified facility using low impact dyes "
        "and recycled water systems.</p>"
        "<ul>"
        "<li>Material: 100% organic cotton, 180gsm</li>"
        "<li>Dimensions: chest 51cm, length 70cm (size M)</li>"
        "<li>Weight: 200g</li>"
        "<li>Care: machine wash cold, tumble dry low</li>"
        "</ul>"
    )
    well_filled = _product(
        "p1",
        barcode="012345678905",
        description=long_description,
        metafields={
            ("custom", "material"): "cotton",
            ("custom", "dimensions"): "30x40",
            ("custom", "weight"): "200g",
            ("google", "category"): "Apparel & Accessories",
        },
    )
    mock_shopify.graphql.side_effect = [
        _products_response([well_filled]),
        _theme_with_schema(),
    ]

    result = await scanner.scan("store-1", mock_shopify, [])

    assert result.metrics["score"] == 100
    assert result.issues == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_score_calculation_partial(
    scanner: AgenticReadinessScanner, mock_shopify: AsyncMock
) -> None:
    p1 = _product("p1", barcode="012345678905")  # passes only GTIN
    p2 = _product("p2")  # fails everything
    mock_shopify.graphql.side_effect = [
        _products_response([p1, p2]),
        _theme_no_schema(),
    ]

    result = await scanner.scan("store-1", mock_shopify, [])

    # GTIN: 1/2 pass -> 0.5 * 0.20 * 100 = 10
    # Catalog: 2/2 pass -> 1.0 * 0.10 * 100 = 10
    # Other 4 checks all fail (0 contribution).
    assert result.metrics["score"] == 20


@pytest.mark.unit
@pytest.mark.asyncio
async def test_should_run_plan(scanner: AgenticReadinessScanner) -> None:
    assert await scanner.should_run(["agentic"], "starter") is True
    assert await scanner.should_run(["agentic"], "pro") is True
    assert await scanner.should_run(["agentic"], "free") is False
    assert await scanner.should_run(["health"], "starter") is False
