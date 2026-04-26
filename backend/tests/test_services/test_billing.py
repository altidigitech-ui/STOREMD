"""Tests for StripeBillingService and ShopifyBillingService."""

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.exceptions import BillingError, ErrorCode
from app.services.stripe_billing import StripeBillingService, PLAN_HIERARCHY, USAGE_LIMITS
from app.services.shopify_billing import ShopifyBillingService


@pytest.fixture
def mock_supabase():
    supabase = MagicMock()
    return supabase


def _mock_merchant(supabase, plan="free", stripe_customer_id=None):
    """Configure the mock to return a merchant with the given plan."""
    t = MagicMock()
    t.select.return_value = t
    t.eq.return_value = t
    t.single.return_value = t
    t.maybe_single.return_value = t
    t.execute.return_value = MagicMock(data={
        "id": "merchant-1",
        "email": "test@test.com",
        "plan": plan,
        "stripe_customer_id": stripe_customer_id,
        "stripe_subscription_id": None,
    })
    supabase.table.return_value = t


@pytest.mark.unit
def test_check_plan_access_pro_granted(mock_supabase):
    """Pro feature accessible with Pro plan."""
    _mock_merchant(mock_supabase, plan="pro")
    billing = StripeBillingService(mock_supabase)
    assert billing.check_plan_access("merchant-1", "visual_store_test") is True


@pytest.mark.unit
def test_check_plan_access_free_denied(mock_supabase):
    """Pro feature denied on Free plan."""
    _mock_merchant(mock_supabase, plan="free")
    billing = StripeBillingService(mock_supabase)
    assert billing.check_plan_access("merchant-1", "visual_store_test") is False


@pytest.mark.unit
def test_check_plan_access_starter_for_starter_feature(mock_supabase):
    """Starter feature accessible with Starter plan."""
    _mock_merchant(mock_supabase, plan="starter")
    billing = StripeBillingService(mock_supabase)
    assert billing.check_plan_access("merchant-1", "app_impact_scanner") is True


@pytest.mark.unit
def test_check_plan_access_agency_has_all(mock_supabase):
    """Agency plan has access to all features."""
    _mock_merchant(mock_supabase, plan="agency")
    billing = StripeBillingService(mock_supabase)
    assert billing.check_plan_access("merchant-1", "visual_store_test") is True
    assert billing.check_plan_access("merchant-1", "app_impact_scanner") is True
    assert billing.check_plan_access("merchant-1", "health_score") is True


@pytest.mark.unit
def test_usage_limit_by_plan(mock_supabase):
    """Usage limits correspond to plan tiers."""
    _mock_merchant(mock_supabase, plan="free")
    billing = StripeBillingService(mock_supabase)
    assert billing.get_usage_limit("merchant-1", "scan") == 3
    assert billing.get_usage_limit("merchant-1", "browser_test") == 0

    _mock_merchant(mock_supabase, plan="starter")
    assert billing.get_usage_limit("merchant-1", "scan") == 5
    assert billing.get_usage_limit("merchant-1", "listing_analysis") == 100

    _mock_merchant(mock_supabase, plan="pro")
    assert billing.get_usage_limit("merchant-1", "scan") == 31
    assert billing.get_usage_limit("merchant-1", "browser_test") == 31


@pytest.mark.unit
def test_plan_hierarchy():
    """Plan hierarchy order is correct."""
    assert PLAN_HIERARCHY["free"] < PLAN_HIERARCHY["starter"]
    assert PLAN_HIERARCHY["starter"] < PLAN_HIERARCHY["pro"]
    assert PLAN_HIERARCHY["pro"] < PLAN_HIERARCHY["agency"]


# ─── ShopifyBillingService error-code tests ───────────────────────────────────

def _shopify_service() -> ShopifyBillingService:
    return ShopifyBillingService(
        shop_domain="test.myshopify.com",
        access_token="shpat_test",
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shopify_billing_http_error_uses_shopify_code():
    """_graphql raises BillingError with SHOPIFY_BILLING_FAILED on HTTP error."""
    svc = _shopify_service()
    mock_response = MagicMock()
    mock_response.status_code = 503
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        with pytest.raises(BillingError) as exc_info:
            await svc._graphql("query { shop { name } }", {})

    assert exc_info.value.code == ErrorCode.SHOPIFY_BILLING_FAILED


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shopify_billing_graphql_error_uses_shopify_code():
    """_graphql raises BillingError with SHOPIFY_BILLING_FAILED on GraphQL errors."""
    svc = _shopify_service()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"errors": [{"message": "Access denied"}]}
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        with pytest.raises(BillingError) as exc_info:
            await svc._graphql("query { shop { name } }", {})

    assert exc_info.value.code == ErrorCode.SHOPIFY_BILLING_FAILED


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shopify_billing_invalid_plan_uses_shopify_code():
    """create_subscription raises BillingError with SHOPIFY_BILLING_FAILED for unknown plan."""
    svc = _shopify_service()
    with pytest.raises(BillingError) as exc_info:
        await svc.create_subscription(plan="enterprise", return_url="https://example.com")

    assert exc_info.value.code == ErrorCode.SHOPIFY_BILLING_FAILED
    assert exc_info.value.status_code == 400


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shopify_billing_user_errors_uses_shopify_code():
    """create_subscription raises BillingError with SHOPIFY_BILLING_FAILED on userErrors."""
    svc = _shopify_service()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": {
            "appSubscriptionCreate": {
                "appSubscription": None,
                "confirmationUrl": None,
                "userErrors": [{"field": "name", "message": "Name too long"}],
            }
        }
    }
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        with pytest.raises(BillingError) as exc_info:
            await svc.create_subscription(plan="pro", return_url="https://example.com")

    assert exc_info.value.code == ErrorCode.SHOPIFY_BILLING_FAILED


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shopify_cancel_user_errors_uses_shopify_code():
    """cancel_subscription raises BillingError with SHOPIFY_BILLING_FAILED on userErrors."""
    svc = _shopify_service()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": {
            "appSubscriptionCancel": {
                "appSubscription": None,
                "userErrors": [{"field": "id", "message": "Not found"}],
            }
        }
    }
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        with pytest.raises(BillingError) as exc_info:
            await svc.cancel_subscription("gid://shopify/AppSubscription/123")

    assert exc_info.value.code == ErrorCode.SHOPIFY_BILLING_FAILED


# ─── Stripe still uses STRIPE_CHECKOUT_FAILED ────────────────────────────────

@pytest.mark.unit
def test_stripe_checkout_error_code_unchanged(mock_supabase):
    """StripeBillingService errors still use STRIPE_CHECKOUT_FAILED, not SHOPIFY_BILLING_FAILED."""
    _mock_merchant(mock_supabase, plan="free", stripe_customer_id=None)
    billing = StripeBillingService(mock_supabase)
    # Verify the code value is the Stripe-specific one
    assert ErrorCode.STRIPE_CHECKOUT_FAILED == "BILLING_CHECKOUT_FAILED"
    assert ErrorCode.SHOPIFY_BILLING_FAILED == "SHOPIFY_BILLING_FAILED"
    assert ErrorCode.STRIPE_CHECKOUT_FAILED != ErrorCode.SHOPIFY_BILLING_FAILED
