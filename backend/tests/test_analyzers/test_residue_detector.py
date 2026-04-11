"""Tests for ResidueDetector scanner."""

import pytest
from unittest.mock import AsyncMock

from app.agent.analyzers.residue_detector import ResidueDetector


@pytest.fixture
def scanner():
    return ResidueDetector()


@pytest.fixture
def mock_shopify():
    client = AsyncMock()
    client.shop_domain = "teststore.myshopify.com"
    return client


APPS_WITH_PRIVY = {
    "appInstallations": {
        "edges": [
            {"node": {"app": {"title": "Privy", "handle": "privy"}}},
        ]
    }
}

SCRIPTS_WITH_PRIVY_AND_OLD_APP = {
    "scriptTags": {
        "edges": [
            {"node": {"id": "st1", "src": "https://privy.com/widget.js", "displayScope": "ALL"}},
            {"node": {"id": "st2", "src": "https://old-app.com/legacy.js", "displayScope": "ALL"}},
        ]
    }
}

SCRIPTS_WITH_KLAVIYO_RESIDUE = {
    "scriptTags": {
        "edges": [
            {"node": {"id": "st1", "src": "https://static.klaviyo.com/onsite.js", "displayScope": "ALL"}},
        ]
    }
}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_detects_residual_scripts(scanner, mock_shopify):
    """Detects scripts from known uninstalled apps."""
    # Privy installed, Klaviyo NOT installed but script present
    mock_shopify.graphql.side_effect = [
        APPS_WITH_PRIVY,  # Only Privy installed
        SCRIPTS_WITH_KLAVIYO_RESIDUE,  # Klaviyo script still present
    ]

    result = await scanner.scan("store-1", mock_shopify, [])

    assert len(result.issues) == 1
    assert result.issues[0].scanner == "residue_detector"
    assert "Klaviyo" in result.issues[0].title
    assert result.issues[0].auto_fixable is True
    assert result.metrics["residual_scripts"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_no_residual_scripts(scanner, mock_shopify):
    """All scripts match installed apps — no residue."""
    mock_shopify.graphql.side_effect = [
        APPS_WITH_PRIVY,
        {"scriptTags": {"edges": [
            {"node": {"id": "st1", "src": "https://privy.com/widget.js", "displayScope": "ALL"}},
        ]}},
    ]

    result = await scanner.scan("store-1", mock_shopify, [])

    # Privy script is from an installed app — not residual
    assert len(result.issues) == 0
    assert result.metrics["residual_scripts"] == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_empty_scripts(scanner, mock_shopify):
    """No script tags at all — clean store."""
    mock_shopify.graphql.side_effect = [
        APPS_WITH_PRIVY,
        {"scriptTags": {"edges": []}},
    ]

    result = await scanner.scan("store-1", mock_shopify, [])

    assert len(result.issues) == 0
    assert result.metrics["total_scripts"] == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_should_run_plan(scanner):
    """Plan and module checks."""
    assert await scanner.should_run(["health"], "starter") is True
    assert await scanner.should_run(["health"], "free") is False
    assert await scanner.should_run(["browser"], "pro") is False
