"""Celery tasks — weekly report generation.

Triggered by the beat schedule every Sunday at 9 AM UTC. Iterates over
all merchants on Starter+ plans and generates one report per active store.
"""

from __future__ import annotations

import asyncio

import structlog

from tasks.celery_app import celery_app

logger = structlog.get_logger()


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# Plans that receive the weekly report.
ELIGIBLE_PLANS = ("starter", "pro", "agency")


@celery_app.task
def send_weekly_reports() -> None:
    """Build + send weekly reports for all eligible merchants."""
    _run_async(_send_weekly_reports_async())


async def _send_weekly_reports_async() -> None:
    from app.dependencies import get_supabase_service
    from app.services.report_generator import generate_weekly_report

    supabase = get_supabase_service()

    try:
        merchants = (
            supabase.table("merchants")
            .select("id, plan")
            .in_("plan", list(ELIGIBLE_PLANS))
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("weekly_report_query_failed", error=str(exc))
        return

    if not merchants.data:
        logger.info("weekly_report_no_merchants")
        return

    sent = 0
    for merchant in merchants.data:
        try:
            stores = (
                supabase.table("stores")
                .select("id")
                .eq("merchant_id", merchant["id"])
                .eq("status", "active")
                .execute()
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "weekly_report_stores_failed",
                merchant_id=merchant["id"],
                error=str(exc),
            )
            continue

        for store in stores.data or []:
            try:
                await generate_weekly_report(
                    store_id=store["id"],
                    merchant_id=merchant["id"],
                    supabase=supabase,
                )
                sent += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "weekly_report_send_failed",
                    store_id=store["id"],
                    error=str(exc),
                )

    logger.info("weekly_reports_dispatched", sent=sent)
