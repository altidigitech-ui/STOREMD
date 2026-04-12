"""Unit tests for BrokenLinksScanner."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agent.analyzers.broken_links import BrokenLinksScanner


def _shop_response() -> dict:
    return {
        "shop": {"primaryDomain": {"url": "https://teststore.com"}},
        "pages": {"edges": [{"node": {"handle": "about"}}]},
        "products": {
            "edges": [
                {"node": {"handle": "alive"}},
                {"node": {"handle": "broken"}},
            ]
        },
        "collections": {"edges": []},
    }


class _MockResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


@pytest.fixture
def scanner() -> BrokenLinksScanner:
    return BrokenLinksScanner()


@pytest.fixture
def mock_shopify():
    sh = AsyncMock()
    sh.graphql.return_value = _shop_response()
    return sh


@pytest.mark.unit
@pytest.mark.asyncio
async def test_detects_broken_link(
    scanner: BrokenLinksScanner, mock_shopify: AsyncMock
) -> None:
    async def fake_head(url: str):
        return _MockResponse(404 if "broken" in url else 200)

    fake_client = AsyncMock()
    fake_client.head = fake_head

    fake_ctx = MagicMock()
    fake_ctx.__aenter__ = AsyncMock(return_value=fake_client)
    fake_ctx.__aexit__ = AsyncMock(return_value=None)

    with patch("app.agent.analyzers.broken_links.httpx.AsyncClient", return_value=fake_ctx):
        result = await scanner.scan("store-1", mock_shopify, [])

    assert result.metrics["broken_count"] == 1
    assert any("broken" in i.title for i in result.issues)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_all_links_ok(
    scanner: BrokenLinksScanner, mock_shopify: AsyncMock
) -> None:
    async def fake_head(url: str):
        return _MockResponse(200)

    fake_client = AsyncMock()
    fake_client.head = fake_head

    fake_ctx = MagicMock()
    fake_ctx.__aenter__ = AsyncMock(return_value=fake_client)
    fake_ctx.__aexit__ = AsyncMock(return_value=None)

    with patch("app.agent.analyzers.broken_links.httpx.AsyncClient", return_value=fake_ctx):
        result = await scanner.scan("store-1", mock_shopify, [])

    assert result.metrics["broken_count"] == 0
    assert result.issues == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_should_run_plan(scanner: BrokenLinksScanner) -> None:
    assert await scanner.should_run(["compliance"], "starter") is True
    assert await scanner.should_run(["compliance"], "free") is False
    assert await scanner.should_run(["health"], "starter") is False
