"""Tests for scan API endpoints."""

import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_scan_success(client, auth_headers):
    """POST /scans — create a scan returns 201."""
    # Mock: no running scan, insert returns scan data
    from app.dependencies import _supabase_service

    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.in_.return_value = mock_table
    mock_table.maybe_single.return_value = mock_table
    mock_table.single.return_value = mock_table
    mock_table.limit.return_value = mock_table

    call_count = {"n": 0}

    def table_side_effect(name):
        call_count["n"] += 1
        t = MagicMock()
        t.select.return_value = t
        t.eq.return_value = t
        t.in_.return_value = t
        t.maybe_single.return_value = t
        t.single.return_value = t
        t.limit.return_value = t

        if name == "merchants":
            t.execute.return_value = MagicMock(data={
                "id": "merchant-uuid-1",
                "plan": "starter",
                "onboarding_completed": True,
            })
        elif name == "stores":
            t.execute.return_value = MagicMock(data={
                "id": "store-1",
                "merchant_id": "merchant-uuid-1",
                "shopify_shop_domain": "test.myshopify.com",
            })
        elif name == "scans":
            # First call: check running scans (empty)
            # Second call: insert
            if call_count["n"] <= 3:
                t.execute.return_value = MagicMock(data=[])
            else:
                t.insert.return_value = t
                t.execute.return_value = MagicMock(data=[{
                    "id": "scan-uuid-1",
                    "status": "pending",
                    "modules": ["health"],
                    "trigger": "manual",
                    "created_at": "2026-04-09T10:00:00Z",
                }])
        return t

    with (
        patch.object(_supabase_service, "table", side_effect=table_side_effect),
        patch("tasks.scan_tasks.run_scan") as mock_task,
    ):
        mock_task.delay = MagicMock()

        response = await client.post(
            "/api/v1/stores/store-1/scans",
            json={"modules": ["health"]},
            headers=auth_headers,
        )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert data["modules"] == ["health"]
    assert "id" in data


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_scan_plan_required(client, auth_headers):
    """POST /scans with browser module on free plan returns 403."""
    from app.dependencies import _supabase_service

    def table_side_effect(name):
        t = MagicMock()
        t.select.return_value = t
        t.eq.return_value = t
        t.maybe_single.return_value = t
        t.single.return_value = t
        t.limit.return_value = t

        if name == "merchants":
            t.execute.return_value = MagicMock(data={
                "id": "merchant-uuid-1",
                "plan": "free",
            })
        elif name == "stores":
            t.execute.return_value = MagicMock(data={
                "id": "store-1",
                "merchant_id": "merchant-uuid-1",
            })
        return t

    with patch.object(_supabase_service, "table", side_effect=table_side_effect):
        response = await client.post(
            "/api/v1/stores/store-1/scans",
            json={"modules": ["browser"]},
            headers=auth_headers,
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUTH_PLAN_REQUIRED"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_scan_already_running(client, auth_headers):
    """POST /scans when scan is running returns 409."""
    from app.dependencies import _supabase_service

    def table_side_effect(name):
        t = MagicMock()
        t.select.return_value = t
        t.eq.return_value = t
        t.in_.return_value = t
        t.maybe_single.return_value = t
        t.single.return_value = t
        t.limit.return_value = t

        if name == "merchants":
            t.execute.return_value = MagicMock(data={
                "id": "merchant-uuid-1",
                "plan": "starter",
            })
        elif name == "stores":
            t.execute.return_value = MagicMock(data={
                "id": "store-1",
                "merchant_id": "merchant-uuid-1",
            })
        elif name == "scans":
            t.execute.return_value = MagicMock(data=[{"id": "existing-scan"}])
        return t

    with patch.object(_supabase_service, "table", side_effect=table_side_effect):
        response = await client.post(
            "/api/v1/stores/store-1/scans",
            json={"modules": ["health"]},
            headers=auth_headers,
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SCAN_ALREADY_RUNNING"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_scan_no_auth(client):
    """POST /scans without JWT returns 401."""
    response = await client.post(
        "/api/v1/stores/store-1/scans",
        json={"modules": ["health"]},
    )
    assert response.status_code == 401


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_scan_invalid_module(client, auth_headers):
    """POST /scans with invalid module returns 422."""
    response = await client.post(
        "/api/v1/stores/store-1/scans",
        json={"modules": ["invalid_module"]},
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_health_no_scans(client, auth_headers):
    """GET /health with no scans returns empty response."""
    from app.dependencies import _supabase_service

    def table_side_effect(name):
        t = MagicMock()
        t.select.return_value = t
        t.eq.return_value = t
        t.maybe_single.return_value = t
        t.single.return_value = t
        t.order.return_value = t
        t.limit.return_value = t

        if name == "merchants":
            t.execute.return_value = MagicMock(data={
                "id": "merchant-uuid-1",
                "plan": "starter",
            })
        elif name == "stores":
            t.execute.return_value = MagicMock(data={
                "id": "store-1",
                "merchant_id": "merchant-uuid-1",
            })
        elif name == "scans":
            t.execute.return_value = MagicMock(data=[])
        return t

    with patch.object(_supabase_service, "table", side_effect=table_side_effect):
        response = await client.get(
            "/api/v1/stores/store-1/health",
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["score"] is None
    assert data["trend"] == "stable"
