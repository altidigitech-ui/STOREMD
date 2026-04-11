"""Shared pytest fixtures for StoreMD backend tests."""

import os

# Load test env vars BEFORE any app imports
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault(
    "SUPABASE_JWT_SECRET",
    "super-secret-jwt-token-with-at-least-32-characters-long",
)
os.environ.setdefault("SHOPIFY_API_KEY", "test_shopify_key")
os.environ.setdefault("SHOPIFY_API_SECRET", "test_shopify_secret")
os.environ.setdefault("SHOPIFY_API_VERSION", "2026-01")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("FERNET_KEY", "VMjCuPyYNhncDHwzPRsSXEuPyR4azJjvzUseGcXuewg=")
os.environ.setdefault("ANTHROPIC_API_KEY", "test_anthropic_key")

import jwt as pyjwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.config import settings


def create_test_jwt(merchant_id: str = "merchant-uuid-1") -> str:
    """Create a valid test JWT for Supabase auth."""
    payload = {
        "sub": merchant_id,
        "role": "authenticated",
        "exp": 9999999999,
        "aud": "authenticated",
    }
    return pyjwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")


@pytest_asyncio.fixture
async def client():
    """Async HTTP test client for the FastAPI app.

    Mocks Supabase and Redis to avoid real connections.
    """
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.setex = AsyncMock()
    mock_redis.delete = AsyncMock()
    mock_redis.incr = AsyncMock(return_value=1)
    mock_redis.expire = AsyncMock()
    mock_redis.ttl = AsyncMock(return_value=60)

    mock_supabase = MagicMock()
    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.in_.return_value = mock_table
    mock_table.limit.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.maybe_single.return_value = mock_table
    mock_table.single.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.update.return_value = mock_table
    # Default: maybe_single returns a dict (merchant record)
    mock_table.execute.return_value = MagicMock(data={"id": "test", "plan": "free"})
    mock_supabase.table.return_value = mock_table

    with (
        patch("app.dependencies._redis", mock_redis),
        patch("app.dependencies._supabase_service", mock_supabase),
        patch("app.dependencies._supabase_anon", mock_supabase),
    ):
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Headers with a valid JWT for authenticated tests."""
    return {"Authorization": f"Bearer {create_test_jwt('merchant-uuid-1')}"}


@pytest.fixture
def free_plan_headers() -> dict[str, str]:
    """Headers for a merchant with the Free plan."""
    return {"Authorization": f"Bearer {create_test_jwt('merchant-free-uuid')}"}


@pytest.fixture
def pro_plan_headers() -> dict[str, str]:
    """Headers for a merchant with the Pro plan."""
    return {"Authorization": f"Bearer {create_test_jwt('merchant-pro-uuid')}"}


@pytest.fixture
def mock_shopify(mocker):
    """Mock ShopifyClient — no real API calls."""
    client = mocker.AsyncMock()
    client.shop_domain = "teststore.myshopify.com"
    return client


@pytest.fixture
def mock_claude(mocker):
    """Mock Claude API — predefined response."""
    mock = mocker.patch("app.services.claude.client.messages.create", create=True)
    mock.return_value = mocker.Mock(
        content=[mocker.Mock(text='{"score": 72, "trend": "up", "top_issues": []}')]
    )
    return mock


@pytest.fixture
def mock_memory(mocker):
    """Mock StoreMemory — no real Mem0 calls."""
    memory = mocker.AsyncMock()
    memory.recall_merchant.return_value = []
    memory.recall_store.return_value = []
    memory.recall_cross_store.return_value = []
    memory.recall_for_scan.return_value = {
        "merchant": [],
        "store": [],
        "cross_store": [],
    }
    return memory
