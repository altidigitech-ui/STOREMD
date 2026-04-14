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
    from app.services import email_service
    from app.services.report_generator import generate_weekly_report

    supabase = get_supabase_service()

    try:
        merchants = (
            supabase.table("merchants")
            .select("id, plan, email, notification_email")
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
    emailed = 0
    for merchant in merchants.data:
        try:
            stores = (
                supabase.table("stores")
                .select("id, shopify_shop_domain")
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

        recipient = (
            merchant.get("notification_email") or merchant.get("email") or ""
        )
        # Skip the placeholder addresses we mint during OAuth.
        deliverable = recipient and not recipient.endswith("@storemd.app")

        for store in stores.data or []:
            try:
                report = await generate_weekly_report(
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
                continue

            if not deliverable or not report:
                continue

            issues_count = (report.get("new_issues") or 0) + max(
                0,
                (report.get("score_delta") or 0) * -1,  # rough proxy if no count
            )
            top_action = report.get("top_action")
            try:
                if email_service.send_weekly_report(
                    merchant_email=recipient,
                    shop_domain=store.get("shopify_shop_domain")
                    or "your store",
                    current_score=int(report.get("score") or 0),
                    trend=str(report.get("trend") or "stable"),
                    issues_count=int(report.get("new_issues") or 0),
                    top_issue=top_action if top_action else None,
                ):
                    emailed += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "weekly_report_email_failed",
                    store_id=store["id"],
                    error=str(exc),
                )

    logger.info("weekly_reports_dispatched", sent=sent, emailed=emailed)
