"""Tests for PixelHealthScanner."""

import pytest
from unittest.mock import AsyncMock

from app.agent.analyzers.pixel_health import PixelHealthScanner

MOCK_THEME = {
    "themes": {
        "edges": [{"node": {"id": "gid://shopify/Theme/1", "name": "Dawn"}}]
    }
}

MOCK_FILES_WITH_PIXELS = {
    "theme": {
        "files": {
            "edges": [
                {
                    "node": {
                        "filename": "layout/theme.liquid",
                        "contentType": "text/html",
                        "body": {
                            "content": (
                                '<!-- GA4 -->\n'
                                '<script async src="https://www.googletagmanager.com/gtag/js?id=G-ABC123"></script>\n'
                                '<script>gtag("config", "G-ABC123");</script>\n'
                                '<!-- Meta Pixel -->\n'
                                '<script>fbq("init", "123456");</script>\n'
                            )
                        },
                    }
                },
            ]
        }
    }
}

MOCK_FILES_NO_PIXELS = {
    "theme": {
        "files": {
            "edges": [
                {
                    "node": {
                        "filename": "layout/theme.liquid",
                        "contentType": "text/html",
                        "body": {"content": "<html><body>Hello</body></html>"},
                    }
                },
            ]
        }
    }
}

MOCK_FILES_DUPLICATE_PIXEL = {
    "theme": {
        "files": {
            "edges": [
                {
                    "node": {
                        "filename": "layout/theme.liquid",
                        "contentType": "text/html",
                        "body": {
                            "content": (
                                'gtag("config", "G-AAA"); gtag("config", "G-BBB"); '
                                'gtag("config", "G-CCC"); gtag("send", "pageview");'
                            )
                        },
                    }
                },
            ]
        }
    }
}


@pytest.fixture
def scanner():
    return PixelHealthScanner()


@pytest.fixture
def mock_shopify():
    client = AsyncMock()
    client.shop_domain = "teststore.myshopify.com"
    return client


@pytest.mark.unit
@pytest.mark.asyncio
async def test_detects_missing_pixel(scanner, mock_shopify):
    """Detects missing TikTok pixel (GA4 and Meta present)."""
    mock_shopify.graphql.side_effect = [MOCK_THEME, MOCK_FILES_WITH_PIXELS]

    result = await scanner.scan("store-1", mock_shopify, [])

    missing_names = [i.title for i in result.issues if "not detected" in i.title]
    assert any("TikTok" in name for name in missing_names)
    assert "tiktok_pixel" in result.metrics["missing_pixels"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_all_pixels_missing(scanner, mock_shopify):
    """All pixels missing generates 3 issues."""
    mock_shopify.graphql.side_effect = [MOCK_THEME, MOCK_FILES_NO_PIXELS]

    result = await scanner.scan("store-1", mock_shopify, [])

    missing_issues = [i for i in result.issues if "not detected" in i.title]
    assert len(missing_issues) == 3  # GA4, Meta, TikTok


@pytest.mark.unit
@pytest.mark.asyncio
async def test_detects_duplicate_pixel(scanner, mock_shopify):
    """Detects duplicate GA4 pixel instances."""
    mock_shopify.graphql.side_effect = [MOCK_THEME, MOCK_FILES_DUPLICATE_PIXEL]

    result = await scanner.scan("store-1", mock_shopify, [])

    duplicate_issues = [i for i in result.issues if "Duplicate" in i.title]
    assert len(duplicate_issues) >= 1
    assert "Google Analytics" in duplicate_issues[0].title


@pytest.mark.unit
@pytest.mark.asyncio
async def test_should_run_plan(scanner):
    """Pixel health requires starter plan."""
    assert await scanner.should_run(["health"], "starter") is True
    assert await scanner.should_run(["health"], "pro") is True
    assert await scanner.should_run(["health"], "free") is False
    assert await scanner.should_run(["listings"], "pro") is False
