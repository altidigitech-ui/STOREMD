"""Cross-store intelligence — daily aggregation task.

Scans the past 24h of scan_issues, identifies apps that caused critical
regressions on multiple stores, and writes a `signal_cross_store()`
memory so future scans can warn other stores using those apps.

Reference: docs/AGENT.md "BACKGROUND PROCESSING — ENTRE LES SCANS".
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import UTC, datetime, timedelta

import structlog

from tasks.celery_app import celery_app

logger = structlog.get_logger()


# An app must affect at least this many distinct stores in 24h before
# we emit a cross-store signal.
MIN_AFFECTED_STORES = 5


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task
def run_cross_store_analysis() -> None:
    """Daily 5 AM UTC — surface apps causing fleet-wide regressions."""
    _run_async(_run_cross_store_analysis_async())


async def _run_cross_store_analysis_async() -> None:
    from app.agent.memory import get_store_memory
    from app.dependencies import get_supabase_service

    supabase = get_supabase_service()

    since = datetime.now(UTC) - timedelta(hours=24)
    try:
        result = (
            supabase.table("scan_issues")
            .select("store_id, scanner, severity, title, context")
            .eq("scanner", "app_impact")
            .eq("severity", "critical")
            .gte("created_at", since.isoformat())
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("cross_store_query_failed", error=str(exc))
        return

    rows = result.data or []
    if not rows:
        logger.info("cross_store_no_critical_issues")
        return

    # app_name → set of store_ids affected
    by_app: dict[str, set[str]] = defaultdict(set)
    titles_by_app: dict[str, str] = {}
    for row in rows:
        ctx = row.get("context") or {}
        app_name = (
            ctx.get("app_title")
            or ctx.get("app_name")
            or ctx.get("app_handle")
            or "unknown"
        )
        store_id = row.get("store_id")
        if not store_id:
            continue
        by_app[app_name].add(store_id)
        titles_by_app.setdefault(app_name, row.get("title") or "")

    memory = get_store_memory()
    signals = 0
    for app_name, store_ids in by_app.items():
        affected = len(store_ids)
        if affected < MIN_AFFECTED_STORES:
            continue
        signal_text = (
            f"App '{app_name}' caused critical issues on {affected} stores "
            f"in the last 24h. Likely related to a recent update. "
            f"Sample issue: {titles_by_app.get(app_name, '')[:160]}."
        )
        try:
            await memory.signal_cross_store(signal_text)
            signals += 1
            logger.info(
                "cross_store_signal",
                app=app_name,
                affected_stores=affected,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "cross_store_signal_failed",
                app=app_name,
                error=str(exc),
            )

    logger.info(
        "cross_store_analysis_complete",
        candidate_apps=len(by_app),
        signals_emitted=signals,
    )
