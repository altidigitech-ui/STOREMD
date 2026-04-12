"""Unit tests for VisualStoreTest — diff threshold + plan check."""

from __future__ import annotations

import io

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agent.browser.visual_store_test import VisualStoreTest


def _solid_png(color: tuple[int, int, int], size: tuple[int, int] = (40, 90)) -> bytes:
    """Generate a tiny PNG of a solid colour."""
    from PIL import Image

    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def scanner() -> VisualStoreTest:
    return VisualStoreTest()


@pytest.mark.unit
def test_compute_diff_detects_visual_change(scanner: VisualStoreTest) -> None:
    """A black vs white image should produce ~100% diff and 3 regions."""
    prev = _solid_png((0, 0, 0))
    curr = _solid_png((255, 255, 255))

    diff_pct, regions = scanner._compute_diff(prev, curr)

    assert diff_pct > 90.0
    # Each third changes significantly.
    assert any("top" in r["area"] for r in regions)


@pytest.mark.unit
def test_compute_diff_no_change_below_threshold(
    scanner: VisualStoreTest,
) -> None:
    """Two identical images yield 0% diff and no regions."""
    img = _solid_png((128, 128, 128))
    diff_pct, regions = scanner._compute_diff(img, img)

    assert diff_pct < 1.0
    assert regions == []


@pytest.mark.unit
def test_guess_cause_uses_memory_context(scanner: VisualStoreTest) -> None:
    memory = [
        {"memory": "App Reviews+ updated 2h ago — sections rebuilt"},
    ]
    cause = scanner._guess_cause(
        regions=[{"area": "top (header/hero)", "change_pct": 18.2}],
        memory_context=memory,
    )
    assert "Reviews+" in cause


@pytest.mark.unit
def test_guess_cause_falls_back_to_region_summary(
    scanner: VisualStoreTest,
) -> None:
    cause = scanner._guess_cause(
        regions=[{"area": "middle (content)", "change_pct": 12.3}],
        memory_context=[],
    )
    assert "middle (content)" in cause


@pytest.mark.unit
@pytest.mark.asyncio
async def test_should_run_plan(scanner: VisualStoreTest) -> None:
    assert await scanner.should_run(["browser"], "pro") is True
    assert await scanner.should_run(["browser"], "agency") is True
    assert await scanner.should_run(["browser"], "starter") is False
    assert await scanner.should_run(["browser"], "free") is False
    assert await scanner.should_run(["health"], "pro") is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_test_records_screenshot_metrics(
    scanner: VisualStoreTest, monkeypatch
) -> None:
    """run_test() should produce screenshot metadata for both devices."""
    # Mock create_page → page that returns a screenshot.
    page = MagicMock()
    page.goto = AsyncMock()
    page.wait_for_timeout = AsyncMock()
    page.screenshot = AsyncMock(return_value=_solid_png((200, 200, 200)))
    page.close = AsyncMock()

    async def fake_create_page(browser, device="desktop"):
        return page

    monkeypatch.setattr(scanner, "create_page", fake_create_page)

    # No previous screenshot, no upload, no DB write.
    monkeypatch.setattr(
        scanner, "_get_previous_screenshot", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        scanner,
        "_upload_screenshot",
        AsyncMock(return_value="https://storage/x.png"),
    )
    monkeypatch.setattr(
        scanner, "_record_screenshot", AsyncMock(return_value=None)
    )

    browser = MagicMock()

    result = await scanner.run_test(
        browser=browser,
        store_url="https://teststore.com",
        store_id="store-1",
        memory_context=[],
    )

    assert "mobile" in result.metrics["screenshots"]
    assert "desktop" in result.metrics["screenshots"]
    # No previous screenshot ⇒ no diff_pct, no issues.
    assert result.issues == []
