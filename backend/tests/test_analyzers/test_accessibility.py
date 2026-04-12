"""Unit tests for AccessibilityScanner."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agent.analyzers.accessibility import (
    AccessibilityScanner,
    parse_accessibility,
)


@pytest.fixture
def scanner() -> AccessibilityScanner:
    return AccessibilityScanner()


@pytest.fixture
def mock_shopify():
    sh = AsyncMock()
    sh.graphql.return_value = {
        "shop": {"primaryDomain": {"url": "https://teststore.com"}}
    }
    return sh


def _patched_html(html: str):
    """Patch httpx.AsyncClient so the scanner sees the supplied HTML."""

    response = MagicMock()
    response.text = html
    response.raise_for_status = MagicMock()

    fake_client = AsyncMock()
    fake_client.get = AsyncMock(return_value=response)

    fake_ctx = MagicMock()
    fake_ctx.__aenter__ = AsyncMock(return_value=fake_client)
    fake_ctx.__aexit__ = AsyncMock(return_value=None)

    return patch(
        "app.agent.analyzers.accessibility.httpx.AsyncClient",
        return_value=fake_ctx,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_detects_missing_alt(
    scanner: AccessibilityScanner, mock_shopify: AsyncMock
) -> None:
    html = """
    <html><body>
      <img src="/a.png">
      <img src="/b.png" alt="ok">
      <img src="/c.png">
    </body></html>
    """
    with _patched_html(html):
        result = await scanner.scan("store-1", mock_shopify, [])

    titles = [i.title for i in result.issues]
    assert any("missing alt text" in t for t in titles)
    # 2 imgs missing alt out of 3
    img_issue = next(i for i in result.issues if "missing alt text" in i.title)
    assert img_issue.context["count"] == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_all_accessible(
    scanner: AccessibilityScanner, mock_shopify: AsyncMock
) -> None:
    html = """
    <html><body>
      <h1>Title</h1>
      <h2>Subtitle</h2>
      <img src="/a.png" alt="A">
      <a href="/about">About</a>
      <button aria-label="Close">x</button>
      <label for="email">Email</label>
      <input type="text" id="email">
    </body></html>
    """
    with _patched_html(html):
        result = await scanner.scan("store-1", mock_shopify, [])

    assert result.metrics["score"] == 100
    assert result.issues == []


@pytest.mark.unit
def test_parse_accessibility_pure_function() -> None:
    """The parser is also exposed as a pure helper for tests/CI."""
    html = "<a href='/x'></a><a href='/y'>label</a>"
    violations = parse_accessibility(html)
    rules = {v["rule"] for v in violations}
    assert "link-name" in rules


@pytest.mark.unit
@pytest.mark.asyncio
async def test_should_run_plan(scanner: AccessibilityScanner) -> None:
    assert await scanner.should_run(["compliance"], "starter") is True
    assert await scanner.should_run(["compliance"], "free") is False
    assert await scanner.should_run(["health"], "starter") is False
