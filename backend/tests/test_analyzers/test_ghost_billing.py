"""Tests for GhostBillingDetector scanner."""

import pytest
from unittest.mock import AsyncMock

from app.agent.analyzers.ghost_billing import GhostBillingDetector
from tests.mocks.shopify_responses import MOCK_APPS_DATA, MOCK_APPS_WITH_BILLING


@pytest.fixture
def scanner():
    return GhostBillingDetector()


@pytest.fixture
def mock_shopify():
    client = AsyncMock()
    client.shop_domain = "teststore.myshopify.com"
    return client


@pytest.mark.unit
@pytest.mark.asyncio
async def test_detects_ghost_billing(scanner, mock_shopify):
    """Happy path: an app billing but not installed is surfaced as a ghost charge."""
    # First graphql call → billing data (includes ghost app App/99)
    # Second graphql call → installed apps (App/99 absent)
    mock_shopify.graphql.side_effect = [MOCK_APPS_WITH_BILLING, MOCK_APPS_DATA]

    result = await scanner.scan("store-1", mock_shopify, [])

    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.scanner == "ghost_billing"
    assert issue.severity == "major"
    assert "Old SEO App" in issue.title
    assert "9.99" in issue.title
    assert "teststore.myshopify.com" in issue.fix_description
    assert result.metrics["ghost_charges"] == 1
    assert result.metrics["total_ghost_monthly"] == pytest.approx(9.99)
    # Context fields required by the frontend cancel guide
    assert issue.context["cancel_url"] == (
        "https://teststore.myshopify.com/admin/settings/billing/subscriptions"
    )
    assert issue.context["shop_domain"] == "teststore.myshopify.com"
    assert issue.context["charge_name"] == "Old SEO App"
    assert issue.context["charge_since"] == "2025-11-01T00:00:00Z"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_no_ghosts_when_all_billing_apps_installed(scanner, mock_shopify):
    """No ghost charges when every billing app is in the installed list."""
    billing_only_privy = {
        "appInstallations": {
            "edges": [
                {
                    "node": {
                        "app": {
                            "id": "gid://shopify/App/1",
                            "title": "Privy",
                            "handle": "privy",
                        },
                        "activeSubscriptions": [
                            {
                                "id": "gid://shopify/AppSubscription/10",
                                "name": "Growth Plan",
                                "status": "ACTIVE",
                                "lineItems": [
                                    {
                                        "plan": {
                                            "pricingDetails": {
                                                "price": {
                                                    "amount": "29.99",
                                                    "currencyCode": "USD",
                                                },
                                                "interval": "EVERY_30_DAYS",
                                            }
                                        }
                                    }
                                ],
                            }
                        ],
                    }
                }
            ]
        }
    }
    # Privy (App/1) is billing AND is in MOCK_APPS_DATA → no ghost
    mock_shopify.graphql.side_effect = [billing_only_privy, MOCK_APPS_DATA]

    result = await scanner.scan("store-1", mock_shopify, [])

    assert len(result.issues) == 0
    assert result.metrics["ghost_charges"] == 0
    assert result.metrics["apps_with_billing"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_no_issues_when_no_active_subscriptions(scanner, mock_shopify):
    """Scan produces no issues when no apps have active subscriptions."""
    no_billing = {
        "appInstallations": {
            "edges": [
                {
                    "node": {
                        "app": {
                            "id": "gid://shopify/App/1",
                            "title": "Privy",
                            "handle": "privy",
                        },
                        "activeSubscriptions": [],
                    }
                }
            ]
        }
    }
    mock_shopify.graphql.side_effect = [no_billing, MOCK_APPS_DATA]

    result = await scanner.scan("store-1", mock_shopify, [])

    assert len(result.issues) == 0
    assert result.metrics["ghost_charges"] == 0
    assert result.metrics["apps_with_billing"] == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_critical_severity_for_high_charge(scanner, mock_shopify):
    """A ghost charge >= $50/month is marked critical."""
    billing_data = {
        "appInstallations": {
            "edges": [
                {
                    "node": {
                        "app": {
                            "id": "gid://shopify/App/99",
                            "title": "Expensive Ghost App",
                            "handle": "expensive-ghost",
                        },
                        "activeSubscriptions": [
                            {
                                "id": "gid://shopify/AppSubscription/30",
                                "name": "Enterprise",
                                "status": "ACTIVE",
                                "lineItems": [
                                    {
                                        "plan": {
                                            "pricingDetails": {
                                                "price": {
                                                    "amount": "99.00",
                                                    "currencyCode": "USD",
                                                },
                                                "interval": "EVERY_30_DAYS",
                                            }
                                        }
                                    }
                                ],
                            }
                        ],
                    }
                }
            ]
        }
    }
    # App/99 is NOT in MOCK_APPS_DATA → ghost
    mock_shopify.graphql.side_effect = [billing_data, MOCK_APPS_DATA]

    result = await scanner.scan("store-1", mock_shopify, [])

    assert len(result.issues) == 1
    assert result.issues[0].severity == "critical"
    assert result.metrics["total_ghost_monthly"] == pytest.approx(99.0)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_billing_query_failure_returns_empty_result(scanner, mock_shopify):
    """A Shopify API error on the billing query degrades gracefully — no exception raised."""
    from app.core.exceptions import ErrorCode, ShopifyError

    mock_shopify.graphql.side_effect = ShopifyError(
        code=ErrorCode.SHOPIFY_API_UNAVAILABLE,
        message="Shopify down",
        status_code=503,
    )

    result = await scanner.scan("store-1", mock_shopify, [])

    assert result.scanner_name == "ghost_billing"
    assert result.issues == []
    assert result.metrics["skipped"] == "graphql_error"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_installed_query_failure_returns_empty_result(scanner, mock_shopify):
    """Failure on the second (installed apps) query degrades gracefully."""
    from app.core.exceptions import ErrorCode, ShopifyError

    mock_shopify.graphql.side_effect = [
        MOCK_APPS_WITH_BILLING,
        ShopifyError(
            code=ErrorCode.SHOPIFY_API_UNAVAILABLE,
            message="Shopify down",
            status_code=503,
        ),
    ]

    result = await scanner.scan("store-1", mock_shopify, [])

    assert result.issues == []
    assert result.metrics["skipped"] == "installed_query_error"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_should_run_plan(scanner):
    """Verify should_run gates on plan and module."""
    assert await scanner.should_run(["health"], "starter") is True
    assert await scanner.should_run(["health"], "pro") is True
    assert await scanner.should_run(["health"], "agency") is True
    assert await scanner.should_run(["health"], "free") is False
    assert await scanner.should_run(["listings"], "pro") is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_uninstalled_app_excluded_from_installed_set(scanner, mock_shopify):
    """An app with uninstalledAt set must not appear in installed_app_ids.

    Shopify's appInstallations returns historical records for uninstalled apps
    too. The fix adds `uninstalledAt` to FETCH_INSTALLED_QUERY and filters it
    in Python so ghost charges are correctly detected.
    """
    billing_data = {
        "appInstallations": {
            "edges": [
                {
                    "node": {
                        "app": {
                            "id": "gid://shopify/App/77",
                            "title": "Formerly Installed App",
                            "handle": "formerly-installed",
                        },
                        "activeSubscriptions": [
                            {
                                "id": "gid://shopify/AppSubscription/77",
                                "name": "Basic",
                                "status": "ACTIVE",
                                "createdAt": "2026-01-01T00:00:00Z",
                                "lineItems": [
                                    {
                                        "plan": {
                                            "pricingDetails": {
                                                "price": {
                                                    "amount": "19.99",
                                                    "currencyCode": "USD",
                                                },
                                                "interval": "EVERY_30_DAYS",
                                            }
                                        }
                                    }
                                ],
                            }
                        ],
                    }
                }
            ]
        }
    }
    # The installed query returns App/77 but with uninstalledAt set — it was
    # uninstalled and must be excluded from the reference set.
    installed_data = {
        "appInstallations": {
            "edges": [
                {
                    "node": {
                        "app": {
                            "id": "gid://shopify/App/77",
                            "title": "Formerly Installed App",
                            "handle": "formerly-installed",
                        },
                        "uninstalledAt": "2026-01-01T00:00:00Z",
                    }
                }
            ]
        }
    }
    mock_shopify.graphql.side_effect = [billing_data, installed_data]

    result = await scanner.scan("store-1", mock_shopify, [])

    # App/77 has uninstalledAt set → excluded from installed_app_ids → ghost charge
    assert len(result.issues) == 1
    assert result.issues[0].context["app_id"] == "gid://shopify/App/77"
    assert result.metrics["ghost_charges"] == 1
    assert result.metrics["total_ghost_monthly"] == pytest.approx(19.99)
