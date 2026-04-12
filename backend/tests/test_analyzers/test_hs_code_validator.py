"""Unit tests for HSCodeValidator."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from app.agent.analyzers.hs_code_validator import HSCodeValidator


def _product(pid: str, hs_code: str | None, product_type: str = "") -> dict:
    return {
        "id": pid,
        "title": f"Product {pid}",
        "productType": product_type,
        "variants": {
            "edges": [
                {"node": {"harmonizedSystemCode": hs_code}},
            ]
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
def scanner() -> HSCodeValidator:
    return HSCodeValidator()


@pytest.fixture
def mock_shopify():
    return AsyncMock()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_detects_missing_hs(
    scanner: HSCodeValidator, mock_shopify: AsyncMock
) -> None:
    mock_shopify.graphql.return_value = _response(
        [_product("p1", None), _product("p2", "6105100000", "shirt")]
    )

    result = await scanner.scan("store-1", mock_shopify, [])

    assert result.metrics["missing_hs"] == 1
    titles = [i.title for i in result.issues]
    assert any("missing HS code" in t for t in titles)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_detects_suspicious_hs(
    scanner: HSCodeValidator, mock_shopify: AsyncMock
) -> None:
    # bag should start with 4202; using 7113 (jewelry) is suspicious.
    mock_shopify.graphql.return_value = _response(
        [_product("p1", "7113000000", "bag")]
    )

    result = await scanner.scan("store-1", mock_shopify, [])

    assert result.metrics["suspicious_hs"] == 1
    titles = [i.title for i in result.issues]
    assert any("Suspicious HS code" in t for t in titles)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_valid_hs_codes(
    scanner: HSCodeValidator, mock_shopify: AsyncMock
) -> None:
    mock_shopify.graphql.return_value = _response(
        [
            _product("p1", "6105100000", "shirt"),
            _product("p2", "4202120000", "bag"),
        ]
    )

    result = await scanner.scan("store-1", mock_shopify, [])

    assert result.metrics["valid_hs"] == 2
    assert result.metrics["missing_hs"] == 0
    assert result.metrics["suspicious_hs"] == 0
    assert result.issues == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_should_run_plan(scanner: HSCodeValidator) -> None:
    assert await scanner.should_run(["agentic"], "pro") is True
    assert await scanner.should_run(["agentic"], "agency") is True
    assert await scanner.should_run(["agentic"], "starter") is False
    assert await scanner.should_run(["agentic"], "free") is False
