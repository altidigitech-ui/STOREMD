"""StoreMemory — Mem0 client wrapper.

4 memory types (see docs/AGENT.md and .claude/skills/mem0-integration/SKILL.md):

| Type        | Scope        | user_id / agent_id                  | TTL     |
|-------------|--------------|-------------------------------------|---------|
| Merchant    | 1 merchant   | user_id="storemd:{merchant_id}"     | infini  |
| Store       | 1 store      | user_id="storemd:store:{store_id}"  | infini  |
| Cross-store | global       | agent_id="storemd:global"           | 90 jours|
| Agent       | the agent    | agent_id="storemd:agent"            | infini  |

The class works in two modes:
- Hosted Mem0 (MemoryClient) when MEM0_API_KEY is set
- Self-hosted (Memory) backed by pgvector in Supabase otherwise

Every Mem0 call is wrapped in a try/except so a Mem0 outage never breaks
a scan — the orchestrator just runs without the historical context.
"""

from __future__ import annotations

from typing import Any

import structlog

from app.config import settings

logger = structlog.get_logger()


# Mem0 imports are lazy/optional so the test suite can run without
# the package installed and so import errors don't crash the worker.
def _build_client() -> Any:
    try:
        if settings.MEM0_API_KEY:
            from mem0 import MemoryClient

            return MemoryClient(api_key=settings.MEM0_API_KEY)

        from mem0 import Memory

        # Self-hosted path: Mem0's pgvector backend.
        # SUPABASE_DB_URL is optional; if missing we use Mem0's defaults
        # (in-memory) — fine for dev/test, not for prod.
        config: dict = {}
        db_url = getattr(settings, "SUPABASE_DB_URL", "") or ""
        if db_url:
            config["vector_store"] = {
                "provider": "pgvector",
                "config": {
                    "connection_string": db_url,
                    "collection_name": "storemd_memories",
                },
            }
        return Memory(config=config) if config else Memory()
    except Exception as exc:  # noqa: BLE001 — Mem0 init can fail for many reasons
        logger.warning("mem0_init_failed", error=str(exc))
        return None


def _normalize_results(raw: Any) -> list[dict]:
    """Mem0 search returns either a list of dicts or {'results': [...]}.
    Always return a list of dicts."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        results = raw.get("results")
        if isinstance(results, list):
            return results
    return []


class StoreMemory:
    """Mem0 wrapper used by the agent layer.

    All public methods are async. Internally Mem0 is sync — calls are
    quick enough that we don't bother offloading to a thread.
    """

    def __init__(self, client: Any | None = None) -> None:
        # Allow injection in tests; default to building the real client.
        self._client = client if client is not None else _build_client()

    @property
    def is_available(self) -> bool:
        return self._client is not None

    # ------------------------------------------------------------------
    # Merchant memory
    # ------------------------------------------------------------------

    async def remember_merchant(self, merchant_id: str, context: str) -> None:
        if not self._client:
            return
        try:
            self._client.add(
                messages=[{"role": "system", "content": context}],
                user_id=f"storemd:{merchant_id}",
                metadata={"saas": "storemd", "type": "merchant"},
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "mem0_remember_merchant_failed",
                merchant_id=merchant_id,
                error=str(exc),
            )

    async def recall_merchant(
        self, merchant_id: str, query: str, limit: int = 10
    ) -> list[dict]:
        if not self._client:
            return []
        try:
            raw = self._client.search(
                query=query,
                user_id=f"storemd:{merchant_id}",
                limit=limit,
            )
            return _normalize_results(raw)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "mem0_recall_merchant_failed",
                merchant_id=merchant_id,
                error=str(exc),
            )
            return []

    # ------------------------------------------------------------------
    # Store memory
    # ------------------------------------------------------------------

    async def remember_store(self, store_id: str, context: str) -> None:
        if not self._client:
            return
        try:
            self._client.add(
                messages=[{"role": "system", "content": context}],
                user_id=f"storemd:store:{store_id}",
                metadata={"saas": "storemd", "type": "store"},
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "mem0_remember_store_failed",
                store_id=store_id,
                error=str(exc),
            )

    async def recall_store(
        self, store_id: str, query: str, limit: int = 10
    ) -> list[dict]:
        if not self._client:
            return []
        try:
            raw = self._client.search(
                query=query,
                user_id=f"storemd:store:{store_id}",
                limit=limit,
            )
            return _normalize_results(raw)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "mem0_recall_store_failed",
                store_id=store_id,
                error=str(exc),
            )
            return []

    # ------------------------------------------------------------------
    # Cross-store intelligence
    # ------------------------------------------------------------------

    async def signal_cross_store(self, signal: str) -> None:
        if not self._client:
            return
        try:
            self._client.add(
                messages=[{"role": "system", "content": signal}],
                agent_id="storemd:global",
                metadata={"saas": "storemd", "type": "cross_store"},
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("mem0_signal_cross_store_failed", error=str(exc))

    async def recall_cross_store(self, query: str, limit: int = 5) -> list[dict]:
        if not self._client:
            return []
        try:
            raw = self._client.search(
                query=query,
                agent_id="storemd:global",
                limit=limit,
            )
            return _normalize_results(raw)
        except Exception as exc:  # noqa: BLE001
            logger.warning("mem0_recall_cross_store_failed", error=str(exc))
            return []

    # ------------------------------------------------------------------
    # Agent memory (meta-level patterns)
    # ------------------------------------------------------------------

    async def remember_agent(self, context: str) -> None:
        if not self._client:
            return
        try:
            self._client.add(
                messages=[{"role": "system", "content": context}],
                agent_id="storemd:agent",
                metadata={"saas": "storemd", "type": "agent"},
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("mem0_remember_agent_failed", error=str(exc))

    async def recall_agent(self, query: str, limit: int = 5) -> list[dict]:
        if not self._client:
            return []
        try:
            raw = self._client.search(
                query=query,
                agent_id="storemd:agent",
                limit=limit,
            )
            return _normalize_results(raw)
        except Exception as exc:  # noqa: BLE001
            logger.warning("mem0_recall_agent_failed", error=str(exc))
            return []

    # ------------------------------------------------------------------
    # Feedback loop (Ouroboros)
    # ------------------------------------------------------------------

    async def learn_from_feedback(
        self,
        merchant_id: str,
        issue_title: str,
        scanner: str,
        severity: str,
        accepted: bool,
        reason: str | None = None,
    ) -> None:
        """Persist merchant feedback as a merchant memory.

        The next scan can `recall_merchant()` and surface this when
        crafting recommendations.
        """
        verdict = "ACCEPTED" if accepted else "REJECTED"
        suffix = "" if accepted else f" Reason: {reason or 'not specified'}."
        context = (
            f"Recommendation '{issue_title}' "
            f"(scanner: {scanner}, severity: {severity}): {verdict}.{suffix}"
        )
        await self.remember_merchant(merchant_id, context)

    # ------------------------------------------------------------------
    # Convenience — recall everything an orchestrator needs for a scan
    # ------------------------------------------------------------------

    async def recall_for_scan(
        self,
        merchant_id: str,
        store_id: str,
        modules: list[str] | None = None,
    ) -> dict[str, list[dict]]:
        """Load all 3 contexts (merchant, store, cross-store) for a scan."""
        modules = modules or []
        query = f"store health scan {' '.join(modules)}".strip()

        merchant_ctx = await self.recall_merchant(merchant_id, query)
        store_ctx = await self.recall_store(store_id, query)
        cross_store_ctx = await self.recall_cross_store(
            "app risks alerts global patterns"
        )

        return {
            "merchant": merchant_ctx,
            "store": store_ctx,
            "cross_store": cross_store_ctx,
        }

    # ------------------------------------------------------------------
    # GDPR cleanup
    # ------------------------------------------------------------------

    async def forget_merchant(self, merchant_id: str) -> None:
        if not self._client:
            return
        try:
            self._client.delete_all(user_id=f"storemd:{merchant_id}")
            logger.info("mem0_forget_merchant", merchant_id=merchant_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "mem0_forget_merchant_failed",
                merchant_id=merchant_id,
                error=str(exc),
            )

    async def forget_store(self, store_id: str) -> None:
        if not self._client:
            return
        try:
            self._client.delete_all(user_id=f"storemd:store:{store_id}")
            logger.info("mem0_forget_store", store_id=store_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "mem0_forget_store_failed",
                store_id=store_id,
                error=str(exc),
            )


# Lazy singleton — instantiated on first access.
_memory: StoreMemory | None = None


def get_store_memory() -> StoreMemory:
    """Process-wide StoreMemory singleton."""
    global _memory
    if _memory is None:
        _memory = StoreMemory()
    return _memory
