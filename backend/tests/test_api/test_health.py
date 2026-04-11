"""Tests for GET /api/v1/health endpoint."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.unit
@pytest.mark.asyncio
async def test_healthcheck_healthy(client):
    """Healthcheck returns 200 when DB and Redis are connected."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["db"] == "connected"
    assert data["redis"] == "connected"
    assert "version" in data


@pytest.mark.unit
@pytest.mark.asyncio
async def test_healthcheck_db_down(client):
    """Healthcheck returns 503 when DB is unreachable."""
    # Make the supabase call raise
    from app.dependencies import _supabase_service

    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.limit.return_value = mock_table
    mock_table.execute.side_effect = Exception("Connection refused")

    with patch.object(_supabase_service, "table", return_value=mock_table):
        response = await client.get("/api/v1/health")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert "error" in data["db"]
    assert data["redis"] == "connected"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_healthcheck_redis_down(client):
    """Healthcheck returns 503 when Redis is unreachable."""
    from app.dependencies import _redis

    original_ping = _redis.ping
    _redis.ping = AsyncMock(side_effect=Exception("Connection refused"))

    try:
        response = await client.get("/api/v1/health")
    finally:
        _redis.ping = original_ping

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert "error" in data["redis"]
