"""Notification service — push (web-push), email (Resend), in-app.

Single entry point: send_notification(). It handles:
- Anti-spam (max push per week)
- DB persistence (table `notifications`)
- Channel-specific delivery (push / email / in_app)
- 410 Gone subscription cleanup for push

Reference: docs/AGENT.md "NOTIFICATIONS — LA VOIX DE L'AGENT".
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.config import settings

logger = structlog.get_logger()


MAX_PUSH_PER_WEEK_DEFAULT = 3


# ---------------------------------------------------------------------------
# Anti-spam
# ---------------------------------------------------------------------------


async def can_notify(
    merchant_id: str,
    channel: str = "push",
    supabase: Any | None = None,
) -> bool:
    """Return True if the merchant hasn't hit their push cap this week.

    Email and in-app are unrestricted.
    """
    if channel != "push":
        return True

    if supabase is None:
        from app.dependencies import get_supabase_service

        supabase = get_supabase_service()

    week_start = datetime.now(UTC) - timedelta(days=7)
    try:
        result = (
            supabase.table("notifications")
            .select("id", count="exact")
            .eq("merchant_id", merchant_id)
            .eq("channel", "push")
            .gte("sent_at", week_start.isoformat())
            .execute()
        )
        count = result.count or 0
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "can_notify_count_failed",
            merchant_id=merchant_id,
            error=str(exc),
        )
        count = 0

    # The merchant's preferred limit is on the merchants row (column
    # `notification_max_push_per_week`). If absent, use the default.
    max_per_week = MAX_PUSH_PER_WEEK_DEFAULT
    try:
        merchant_row = (
            supabase.table("merchants")
            .select("notification_max_push_per_week")
            .eq("id", merchant_id)
            .maybe_single()
            .execute()
        )
        if merchant_row and merchant_row.data:
            value = merchant_row.data.get("notification_max_push_per_week")
            if isinstance(value, int) and value > 0:
                max_per_week = value
    except Exception:  # noqa: BLE001
        pass

    return count < max_per_week


# ---------------------------------------------------------------------------
# Public API — send_notification
# ---------------------------------------------------------------------------


async def send_notification(
    merchant_id: str,
    store_id: str | None,
    channel: str,
    title: str,
    body: str,
    action_url: str | None = None,
    category: str = "general",
    supabase: Any | None = None,
) -> dict | None:
    """Persist a notification row, then deliver via the chosen channel.

    Returns the inserted notification dict, or None if anti-spam denied
    or persistence failed.
    """
    if supabase is None:
        from app.dependencies import get_supabase_service

        supabase = get_supabase_service()

    if not await can_notify(merchant_id, channel, supabase):
        logger.info(
            "notification_skipped_rate_limit",
            merchant_id=merchant_id,
            channel=channel,
            category=category,
        )
        return None

    payload = {
        "merchant_id": merchant_id,
        "store_id": store_id,
        "channel": channel,
        "title": title,
        "body": body,
        "action_url": action_url,
        "category": category,
        "read": False,
        "sent_at": datetime.now(UTC).isoformat(),
    }

    try:
        result = supabase.table("notifications").insert(payload).execute()
        record = result.data[0] if result.data else None
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "notification_persist_failed",
            merchant_id=merchant_id,
            error=str(exc),
        )
        return None

    # Channel delivery — best-effort, persistence already done.
    if channel == "push":
        await _deliver_push(merchant_id, title, body, action_url, category, supabase)
    elif channel == "email":
        await _deliver_email(merchant_id, title, body, supabase)
    # in_app: no extra delivery — the dashboard polls the table.

    logger.info(
        "notification_sent",
        merchant_id=merchant_id,
        channel=channel,
        category=category,
    )
    return record


# ---------------------------------------------------------------------------
# Push delivery (pywebpush)
# ---------------------------------------------------------------------------


async def _deliver_push(
    merchant_id: str,
    title: str,
    body: str,
    action_url: str | None,
    category: str,
    supabase: Any,
) -> None:
    if not settings.VAPID_PRIVATE_KEY:
        logger.info("push_skipped_no_vapid")
        return

    try:
        subs_res = (
            supabase.table("push_subscriptions")
            .select("id, subscription")
            .eq("merchant_id", merchant_id)
            .execute()
        )
        subscriptions = subs_res.data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "push_subscriptions_fetch_failed",
            merchant_id=merchant_id,
            error=str(exc),
        )
        return

    for sub in subscriptions:
        sub_payload = sub.get("subscription")
        if not sub_payload:
            continue
        await send_push(
            subscription=sub_payload,
            title=title,
            body=body,
            action_url=action_url or "/dashboard",
            tag=category,
            subscription_id=sub.get("id"),
            supabase=supabase,
        )


async def send_push(
    subscription: dict,
    title: str,
    body: str,
    action_url: str = "/dashboard",
    tag: str = "storemd",
    subscription_id: str | None = None,
    supabase: Any | None = None,
) -> bool:
    """Send a single web-push notification.

    On 410 Gone (subscription expired) we delete the row from
    push_subscriptions. Other failures are logged and swallowed.
    """
    try:
        from pywebpush import WebPushException, webpush
    except Exception as exc:  # noqa: BLE001
        logger.warning("pywebpush_unavailable", error=str(exc))
        return False

    payload = json.dumps(
        {
            "title": title,
            "body": body,
            "action_url": action_url,
            "tag": tag,
        }
    )

    try:
        webpush(
            subscription_info=subscription,
            data=payload,
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": f"mailto:{settings.VAPID_CONTACT_EMAIL}"},
        )
        return True
    except WebPushException as exc:
        status = (
            exc.response.status_code
            if getattr(exc, "response", None)
            else None
        )
        if status == 410 and subscription_id and supabase is not None:
            try:
                supabase.table("push_subscriptions").delete().eq(
                    "id", subscription_id
                ).execute()
                logger.info(
                    "push_subscription_pruned",
                    subscription_id=subscription_id,
                )
            except Exception as drop_exc:  # noqa: BLE001
                logger.warning(
                    "push_subscription_prune_failed",
                    error=str(drop_exc),
                )
        else:
            logger.warning("push_send_failed", error=str(exc), status=status)
        return False


# ---------------------------------------------------------------------------
# Email delivery (Resend)
# ---------------------------------------------------------------------------


async def _deliver_email(
    merchant_id: str,
    title: str,
    body: str,
    supabase: Any,
) -> None:
    if not settings.RESEND_API_KEY:
        logger.info("email_skipped_no_resend")
        return

    try:
        merchant = (
            supabase.table("merchants")
            .select("notification_email")
            .eq("id", merchant_id)
            .maybe_single()
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("email_lookup_failed", error=str(exc))
        return

    if not merchant or not merchant.data:
        return
    to_email = merchant.data.get("notification_email")
    if not to_email:
        return

    await send_email(
        to=to_email,
        subject=title,
        body_html=f"<p>{body}</p>",
    )


async def send_email(to: str, subject: str, body_html: str) -> bool:
    """Send a transactional email through Resend."""
    if not settings.RESEND_API_KEY:
        return False
    try:
        import resend  # type: ignore[import-not-found]

        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send(
            {
                "from": "StoreMD <noreply@storemd.com>",
                "to": [to],
                "subject": subject,
                "html": body_html,
            }
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("email_send_failed", to=to, error=str(exc))
        return False


# ---------------------------------------------------------------------------
# Pre-formatted notifications (used by orchestrator + report tasks)
# ---------------------------------------------------------------------------


def format_score_drop_notification(
    previous_score: int,
    current_score: int,
    probable_cause: str,
) -> dict:
    delta = previous_score - current_score
    return {
        "title": f"Score dropped {delta} points",
        "body": (
            f"Your health score went from {previous_score} to {current_score}. "
            f"Probable cause: {probable_cause}."
        ),
        "action_url": "/dashboard/health",
        "category": "score_drop",
    }


def format_weekly_report_notification(
    score: int,
    delta: int,
    resolved: int,
    new_issues: int,
) -> dict:
    trend = f"+{delta}" if delta > 0 else str(delta)
    return {
        "title": f"Weekly Report: Score {score} ({trend})",
        "body": (
            f"{resolved} issues resolved, {new_issues} new. "
            "Open your dashboard for details."
        ),
        "action_url": "/dashboard/health",
        "category": "weekly_report",
    }
