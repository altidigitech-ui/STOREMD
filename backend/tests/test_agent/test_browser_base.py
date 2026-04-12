"""Unit tests for BaseBrowserScanner — viewport / launch args / URL resolve."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agent.browser.base import (
    CHROMIUM_ARGS,
    DEFAULT_TIMEOUT_MS,
    DESKTOP_UA,
    MOBILE_UA,
    BaseBrowserScanner,
)
from app.models.scan import ScannerResult


class _DummyScanner(BaseBrowserScanner):
    name = "dummy_browser"
    module = "browser"

    async def run_test(self, browser, store_url, store_id, memory_context):
        return ScannerResult(
            scanner_name=self.name, issues=[], metrics={"ok": True}
        )


@pytest.fixture
def scanner() -> _DummyScanner:
    return _DummyScanner()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_page_mobile_viewport(
    scanner: _DummyScanner,
) -> None:
    page = MagicMock()
    page.set_default_timeout = MagicMock()
    context = MagicMock()
    context.new_page = AsyncMock(return_value=page)
    browser = MagicMock()
    browser.new_context = AsyncMock(return_value=context)

    result = await scanner.create_page(browser, "mobile")

    assert result is page
    browser.new_context.assert_awaited_once()
    kwargs = browser.new_context.await_args.kwargs
    assert kwargs["viewport"] == {"width": 375, "height": 812}
    assert kwargs["user_agent"] == MOBILE_UA
    page.set_default_timeout.assert_called_once_with(DEFAULT_TIMEOUT_MS)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_page_desktop_viewport(
    scanner: _DummyScanner,
) -> None:
    page = MagicMock()
    page.set_default_timeout = MagicMock()
    context = MagicMock()
    context.new_page = AsyncMock(return_value=page)
    browser = MagicMock()
    browser.new_context = AsyncMock(return_value=context)

    await scanner.create_page(browser, "desktop")

    kwargs = browser.new_context.await_args.kwargs
    assert kwargs["viewport"] == {"width": 1440, "height": 900}
    assert kwargs["user_agent"] == DESKTOP_UA


@pytest.mark.unit
def test_browser_launch_args_include_container_safety() -> None:
    """All container-friendly Chromium flags must be present."""
    expected = {
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--single-process",
    }
    assert expected.issubset(set(CHROMIUM_ARGS))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_store_url_resolves_primary_domain(
    scanner: _DummyScanner,
) -> None:
    shopify = AsyncMock()
    shopify.graphql.return_value = {
        "shop": {"primaryDomain": {"url": "https://teststore.com/"}}
    }

    url = await scanner.get_store_url("store-1", shopify)
    assert url == "https://teststore.com"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_store_url_returns_none_on_failure(
    scanner: _DummyScanner,
) -> None:
    shopify = AsyncMock()
    shopify.graphql.side_effect = RuntimeError("boom")
    url = await scanner.get_store_url("store-1", shopify)
    assert url is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_skips_when_playwright_missing(
    scanner: _DummyScanner, monkeypatch
) -> None:
    """If playwright isn't installed (API container), return a clean skip."""
    shopify = AsyncMock()
    shopify.graphql.return_value = {
        "shop": {"primaryDomain": {"url": "https://teststore.com"}}
    }

    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "playwright.async_api":
            raise ImportError("simulated missing playwright")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    result = await scanner.scan("store-1", shopify, [])
    assert result.metrics.get("skipped") == "playwright_unavailable"
