"""Unit tests for StoreMemory (Mem0 wrapper)."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.agent.memory import StoreMemory


@pytest.fixture
def mock_mem0_client() -> MagicMock:
    """In-memory fake of Mem0's MemoryClient API."""
    client = MagicMock()
    # search returns list-shape by default (Mem0 hosted)
    client.search.return_value = [
        {"memory": "Score: 67 (mobile: 52, desktop: 81). Issues: 5."}
    ]
    return client


@pytest.mark.unit
@pytest.mark.asyncio
async def test_remember_and_recall_merchant(mock_mem0_client: MagicMock) -> None:
    memory = StoreMemory(client=mock_mem0_client)

    await memory.remember_merchant("merchant-1", "Prefers CSS fixes over uninstall")
    mock_mem0_client.add.assert_called_once()
    call_kwargs = mock_mem0_client.add.call_args.kwargs
    assert call_kwargs["user_id"] == "storemd:merchant-1"
    assert call_kwargs["metadata"]["type"] == "merchant"

    results = await memory.recall_merchant("merchant-1", "uninstall fix")
    assert results == [
        {"memory": "Score: 67 (mobile: 52, desktop: 81). Issues: 5."}
    ]
    mock_mem0_client.search.assert_called_once_with(
        query="uninstall fix",
        user_id="storemd:merchant-1",
        limit=10,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_recall_for_scan_returns_three_contexts(
    mock_mem0_client: MagicMock,
) -> None:
    memory = StoreMemory(client=mock_mem0_client)
    mock_mem0_client.search.side_effect = [
        [{"memory": "merchant pref"}],  # merchant
        [{"memory": "store baseline"}],  # store
        [{"memory": "cross-store signal"}],  # cross-store
    ]

    ctx = await memory.recall_for_scan(
        merchant_id="merchant-1",
        store_id="store-1",
        modules=["health", "agentic"],
    )

    assert ctx == {
        "merchant": [{"memory": "merchant pref"}],
        "store": [{"memory": "store baseline"}],
        "cross_store": [{"memory": "cross-store signal"}],
    }
    assert mock_mem0_client.search.call_count == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_graceful_degradation_when_mem0_raises(
    mock_mem0_client: MagicMock,
) -> None:
    """Mem0 errors should never bubble up — the wrapper returns []."""
    memory = StoreMemory(client=mock_mem0_client)
    mock_mem0_client.search.side_effect = RuntimeError("mem0 down")

    results = await memory.recall_merchant("merchant-1", "anything")
    assert results == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_graceful_degradation_when_no_client() -> None:
    """If Mem0 init failed, the wrapper still answers with sensible defaults."""
    memory = StoreMemory(client=None)
    # client wasn't built (e.g. mem0 package not installed)
    memory._client = None
    assert memory.is_available is False
    assert await memory.recall_merchant("m", "q") == []
    # remember should not raise
    await memory.remember_store("s", "anything")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_forget_merchant_calls_delete_all(
    mock_mem0_client: MagicMock,
) -> None:
    memory = StoreMemory(client=mock_mem0_client)
    await memory.forget_merchant("merchant-42")
    mock_mem0_client.delete_all.assert_called_once_with(
        user_id="storemd:merchant-42"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_learn_from_feedback_includes_reason_when_rejected(
    mock_mem0_client: MagicMock,
) -> None:
    memory = StoreMemory(client=mock_mem0_client)
    await memory.learn_from_feedback(
        merchant_id="merchant-1",
        issue_title="Uninstall Privy",
        scanner="app_impact",
        severity="critical",
        accepted=False,
        reason="need it for popups",
    )
    call_kwargs = mock_mem0_client.add.call_args.kwargs
    content = call_kwargs["messages"][0]["content"]
    assert "REJECTED" in content
    assert "need it for popups" in content
