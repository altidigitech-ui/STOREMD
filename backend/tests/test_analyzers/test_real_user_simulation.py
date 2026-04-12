"""Unit tests for RealUserSimulation."""

from __future__ import annotations

import time

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agent.browser.real_user_simulation import RealUserSimulation


@pytest.fixture
def scanner() -> RealUserSimulation:
    return RealUserSimulation()


def _make_page() -> MagicMock:
    page = MagicMock()
    page.goto = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.wait_for_timeout = AsyncMock()
    page.locator = MagicMock(return_value=MagicMock(all=AsyncMock(return_value=[])))
    page.close = AsyncMock()
    page.url = "https://teststore.com"
    return page


@pytest.mark.unit
@pytest.mark.asyncio
async def test_detects_slow_journey(
    scanner: RealUserSimulation, monkeypatch
) -> None:
    """Steps that take >10s total should produce a major issue."""
    page = _make_page()

    async def fake_create_page(browser, device="desktop"):
        return page

    async def fake_time_navigation(page_arg, url, name):
        return {
            "name": name,
            "url": url,
            "time_ms": 5_000,  # 5s each — total > 10s
            "bottleneck": False,
            "cause": None,
        }

    async def fake_atc(page_arg):
        return {
            "name": "Add to Cart",
            "url": None,
            "time_ms": 4_000,
            "bottleneck": False,
            "cause": None,
        }

    async def fake_find_collection(page_arg, base_url):
        return f"{base_url}/collections/all"

    async def fake_find_product(page_arg, base_url):
        return f"{base_url}/products/x"

    async def fake_record(**kwargs):
        return None

    monkeypatch.setattr(scanner, "create_page", fake_create_page)
    monkeypatch.setattr(scanner, "_time_navigation", staticmethod(fake_time_navigation))
    monkeypatch.setattr(scanner, "_time_add_to_cart", staticmethod(fake_atc))
    monkeypatch.setattr(scanner, "_find_collection_link", staticmethod(fake_find_collection))
    monkeypatch.setattr(scanner, "_find_product_link", staticmethod(fake_find_product))
    monkeypatch.setattr(scanner, "_record_simulation", fake_record)

    result = await scanner.run_test(
        browser=MagicMock(),
        store_url="https://teststore.com",
        store_id="store-1",
        memory_context=[],
    )

    assert result.metrics["total_time_ms"] >= 10_000
    assert any(i.severity in ("major", "critical") for i in result.issues)
    assert result.metrics["bottleneck_step"] is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fast_journey_no_issues(
    scanner: RealUserSimulation, monkeypatch
) -> None:
    """Fast journey produces no issue."""
    page = _make_page()

    async def fake_create_page(browser, device="desktop"):
        return page

    async def fake_time_navigation(page_arg, url, name):
        return {
            "name": name,
            "url": url,
            "time_ms": 800,
            "bottleneck": False,
            "cause": None,
        }

    async def fake_atc(page_arg):
        return {
            "name": "Add to Cart",
            "url": None,
            "time_ms": 500,
            "bottleneck": False,
            "cause": None,
        }

    async def fake_find_collection(page_arg, base_url):
        return f"{base_url}/collections/all"

    async def fake_find_product(page_arg, base_url):
        return f"{base_url}/products/x"

    async def fake_record(**kwargs):
        return None

    monkeypatch.setattr(scanner, "create_page", fake_create_page)
    monkeypatch.setattr(scanner, "_time_navigation", staticmethod(fake_time_navigation))
    monkeypatch.setattr(scanner, "_time_add_to_cart", staticmethod(fake_atc))
    monkeypatch.setattr(scanner, "_find_collection_link", staticmethod(fake_find_collection))
    monkeypatch.setattr(scanner, "_find_product_link", staticmethod(fake_find_product))
    monkeypatch.setattr(scanner, "_record_simulation", fake_record)

    result = await scanner.run_test(
        browser=MagicMock(),
        store_url="https://teststore.com",
        store_id="store-1",
        memory_context=[],
    )

    assert result.issues == []
    assert result.metrics["total_time_ms"] < 10_000


@pytest.mark.unit
@pytest.mark.asyncio
async def test_should_run_plan(scanner: RealUserSimulation) -> None:
    assert await scanner.should_run(["browser"], "pro") is True
    assert await scanner.should_run(["browser"], "starter") is False
    assert await scanner.should_run(["health"], "pro") is False
