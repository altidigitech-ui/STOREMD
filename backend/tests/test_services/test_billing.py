"""Tests for StripeBillingService."""

import pytest
from unittest.mock import MagicMock

from app.services.stripe_billing import StripeBillingService, PLAN_HIERARCHY, USAGE_LIMITS


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
