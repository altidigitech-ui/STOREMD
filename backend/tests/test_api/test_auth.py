"""Tests for Shopify OAuth endpoints."""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.unit
@pytest.mark.asyncio
async def test_install_redirect_valid_domain(client):
    """GET /auth/install with valid shop domain redirects to Shopify."""
    response = await client.get(
        "/api/v1/auth/install",
        params={"shop": "teststore.myshopify.com"},
        follow_redirects=False,
    )
    assert response.status_code == 307
    location = response.headers["location"]
    assert "teststore.myshopify.com/admin/oauth/authorize" in location
    assert "client_id=" in location
    assert "scope=" in location
    assert "state=" in location


@pytest.mark.unit
@pytest.mark.asyncio
async def test_install_reject_invalid_domain(client):
    """GET /auth/install with invalid shop domain returns 400."""
    response = await client.get(
        "/api/v1/auth/install",
        params={"shop": "not-a-shopify-domain.com"},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "OAUTH_INVALID_SHOP_DOMAIN"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_install_reject_empty_shop(client):
    """GET /auth/install with empty shop param returns 422."""
    response = await client.get("/api/v1/auth/install")
    assert response.status_code == 422


@pytest.mark.unit
@pytest.mark.asyncio
async def test_install_reject_malicious_domain(client):
    """GET /auth/install rejects domain injection attempts."""
    # Domain with spaces / special chars
    response = await client.get(
        "/api/v1/auth/install",
        params={"shop": "evil store.myshopify.com"},
    )
    assert response.status_code == 400

    # Domain without .myshopify.com suffix
    response = await client.get(
        "/api/v1/auth/install",
        params={"shop": "myshopify.com"},
    )
    assert response.status_code == 400


@pytest.mark.unit
@pytest.mark.asyncio
async def test_callback_invalid_state(client):
    """GET /auth/callback with invalid state returns 403."""
    response = await client.get(
        "/api/v1/auth/callback",
        params={
            "code": "test_code",
            "state": "invalid_state_nonce",
            "shop": "teststore.myshopify.com",
        },
    )
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "OAUTH_STATE_INVALID"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_callback_invalid_domain(client):
    """GET /auth/callback with valid state but invalid domain returns 400."""
    from app.dependencies import _redis

    # Simulate a valid state in Redis
    shop = "not-valid-domain.com"
    state = "test_state_nonce"
    _redis.get = AsyncMock(return_value=shop)

    response = await client.get(
        "/api/v1/auth/callback",
        params={
            "code": "test_code",
            "state": state,
            "shop": shop,
        },
    )
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "OAUTH_INVALID_SHOP_DOMAIN"
