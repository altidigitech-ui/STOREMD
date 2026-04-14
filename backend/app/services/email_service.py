"""Resend-backed transactional email service.

Four canonical messages:
  * welcome           — fired after the merchant's first scan completes
  * score_drop        — fired when the score drops by 5+ between scans
  * weekly_report     — fired by the Sunday/Monday cron for paid plans
  * uninstall_feedback — fired from the app/uninstalled webhook

Every send is wrapped: a missing API key, a transport error, or a
malformed merchant row never propagates to the caller. Email is a
nice-to-have side effect — it must not break a scan or a webhook.
"""

from __future__ import annotations

from typing import Any

import structlog

from app.config import settings

logger = structlog.get_logger()

DEFAULT_FROM = "StoreMD <noreply@storemd.vercel.app>"


def _dashboard_url() -> str:
    base = (settings.APP_URL or "https://storemd.vercel.app").rstrip("/")
    return f"{base}/dashboard"


def _is_configured() -> bool:
    return bool(settings.RESEND_API_KEY)


def _resend():
    """Lazy-import + lazy-config so unit tests don't need the SDK."""
    import resend  # type: ignore

    resend.api_key = settings.RESEND_API_KEY
    return resend


def _wrap(title: str, inner_html: str) -> str:
    """Tiny inline-styled wrapper. No external CSS, no remote assets."""
    return f"""\
<!doctype html>
<html>
  <body style="margin:0;padding:0;background-color:#f5f7fa;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#1f2937;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f5f7fa;padding:32px 0;">
      <tr>
        <td align="center">
          <table width="560" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
            <tr>
              <td style="padding:24px 32px;border-bottom:1px solid #eef0f3;">
                <span style="font-size:18px;font-weight:600;color:#2563eb;">StoreMD</span>
                <span style="font-size:13px;color:#6b7280;margin-left:8px;">{title}</span>
              </td>
            </tr>
            <tr>
              <td style="padding:32px;">
                {inner_html}
              </td>
            </tr>
            <tr>
              <td style="padding:16px 32px;border-top:1px solid #eef0f3;font-size:12px;color:#9ca3af;">
                You're receiving this because you installed StoreMD on your Shopify store.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""


def _cta(label: str, url: str) -> str:
    return (
        f'<a href="{url}" '
        'style="display:inline-block;background-color:#2563eb;color:#ffffff;'
        'text-decoration:none;font-weight:600;padding:12px 22px;border-radius:8px;'
        'margin-top:16px;">'
        f"{label} →</a>"
    )


def _send(
    *,
    to: str,
    subject: str,
    html: str,
    log_event: str,
    log_context: dict[str, Any] | None = None,
) -> bool:
    """Internal best-effort sender. Returns True on success."""
    ctx = log_context or {}
    if not to:
        logger.warning("email_skip_no_recipient", event=log_event, **ctx)
        return False

    if not _is_configured():
        logger.warning(
            "email_skip_no_resend_key",
            event=log_event,
            recipient=to,
            **ctx,
        )
        return False

    try:
        resend = _resend()
        resend.Emails.send(
            {
                "from": DEFAULT_FROM,
                "to": [to],
                "subject": subject,
                "html": html,
            }
        )
        logger.info("email_sent", event=log_event, recipient=to, **ctx)
        return True
    except Exception as exc:  # noqa: BLE001 — emails are non-blocking
        logger.warning(
            "email_send_failed",
            event=log_event,
            recipient=to,
            error=str(exc),
            **ctx,
        )
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def send_welcome_email(
    merchant_email: str, shop_domain: str, score: int
) -> bool:
    subject = f"Your store health score is ready — {score}/100"
    inner = f"""
    <h1 style="margin:0 0 8px;font-size:22px;font-weight:600;color:#111827;">
      Your first scan is in.
    </h1>
    <p style="margin:0 0 24px;color:#4b5563;font-size:14px;">
      We just finished diagnosing <strong>{shop_domain}</strong>.
    </p>
    <div style="text-align:center;background-color:#eff6ff;border:1px solid #dbeafe;border-radius:12px;padding:24px;margin:24px 0;">
      <div style="font-size:48px;font-weight:700;color:#2563eb;line-height:1;">{score}</div>
      <div style="font-size:13px;color:#6b7280;margin-top:6px;">/ 100 health score</div>
    </div>
    <p style="margin:0 0 8px;color:#4b5563;font-size:14px;">
      Inside your dashboard you'll find:
    </p>
    <ul style="margin:0;padding-left:20px;color:#4b5563;font-size:14px;line-height:1.6;">
      <li>The exact apps and scripts slowing your store down</li>
      <li>Broken tracking, ghost charges, dead listings</li>
      <li>One-click fixes for the issues we can resolve for you</li>
    </ul>
    <p style="margin:24px 0 0;">{_cta("View your full report", _dashboard_url())}</p>
    """
    return _send(
        to=merchant_email,
        subject=subject,
        html=_wrap("Welcome", inner),
        log_event="welcome_email",
        log_context={"shop_domain": shop_domain, "score": score},
    )


def send_score_drop_alert(
    merchant_email: str,
    shop_domain: str,
    old_score: int,
    new_score: int,
    issues_count: int,
) -> bool:
    delta = old_score - new_score
    subject = f"⚠️ {shop_domain} dropped from {old_score} to {new_score}"
    inner = f"""
    <h1 style="margin:0 0 8px;font-size:22px;font-weight:600;color:#b45309;">
      Your score just dropped by {delta} points.
    </h1>
    <p style="margin:0 0 16px;color:#4b5563;font-size:14px;">
      Something changed on <strong>{shop_domain}</strong> between your last
      two scans. We found <strong>{issues_count}</strong> issue{'s' if issues_count != 1 else ''}
      worth your attention.
    </p>
    <table cellpadding="0" cellspacing="0" style="margin:24px 0;width:100%;">
      <tr>
        <td style="background-color:#f9fafb;border-radius:8px;padding:16px;text-align:center;width:48%;">
          <div style="font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;">Previous</div>
          <div style="font-size:28px;font-weight:700;color:#374151;margin-top:4px;">{old_score}</div>
        </td>
        <td style="width:4%;"></td>
        <td style="background-color:#fef3c7;border-radius:8px;padding:16px;text-align:center;width:48%;">
          <div style="font-size:11px;color:#92400e;text-transform:uppercase;letter-spacing:.05em;">Now</div>
          <div style="font-size:28px;font-weight:700;color:#b45309;margin-top:4px;">{new_score}</div>
        </td>
      </tr>
    </table>
    <p style="margin:0 0 8px;color:#4b5563;font-size:14px;">
      Common causes: a new app installed, a theme update, a tracking pixel
      that stopped firing.
    </p>
    <p style="margin:24px 0 0;">{_cta("See what changed", _dashboard_url())}</p>
    """
    return _send(
        to=merchant_email,
        subject=subject,
        html=_wrap("Score drop alert", inner),
        log_event="score_drop_email",
        log_context={
            "shop_domain": shop_domain,
            "old_score": old_score,
            "new_score": new_score,
            "issues_count": issues_count,
        },
    )


def send_weekly_report(
    merchant_email: str,
    shop_domain: str,
    current_score: int,
    trend: str,
    issues_count: int,
    top_issue: str | None,
) -> bool:
    arrow = {"up": "↑", "down": "↓"}.get(trend, "→")
    arrow_color = {"up": "#16a34a", "down": "#dc2626"}.get(trend, "#6b7280")
    subject = f"Weekly report — {shop_domain}: {current_score}/100"
    top_issue_block = (
        f"""<div style="background-color:#fef2f2;border-left:3px solid #f87171;padding:12px 16px;border-radius:6px;margin:16px 0;">
          <div style="font-size:11px;color:#991b1b;text-transform:uppercase;letter-spacing:.05em;font-weight:600;">Top action</div>
          <div style="font-size:14px;color:#1f2937;margin-top:4px;">{top_issue}</div>
        </div>"""
        if top_issue
        else ""
    )
    inner = f"""
    <h1 style="margin:0 0 8px;font-size:22px;font-weight:600;color:#111827;">
      Here's how {shop_domain} is doing.
    </h1>
    <p style="margin:0 0 24px;color:#4b5563;font-size:14px;">
      Your weekly StoreMD digest.
    </p>
    <table cellpadding="0" cellspacing="0" style="width:100%;margin:16px 0;">
      <tr>
        <td style="background-color:#eff6ff;border-radius:8px;padding:16px;text-align:center;width:48%;">
          <div style="font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;">Score</div>
          <div style="font-size:28px;font-weight:700;color:#2563eb;margin-top:4px;">
            {current_score} <span style="color:{arrow_color};font-size:20px;">{arrow}</span>
          </div>
        </td>
        <td style="width:4%;"></td>
        <td style="background-color:#f9fafb;border-radius:8px;padding:16px;text-align:center;width:48%;">
          <div style="font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;">Open issues</div>
          <div style="font-size:28px;font-weight:700;color:#374151;margin-top:4px;">{issues_count}</div>
        </td>
      </tr>
    </table>
    {top_issue_block}
    <p style="margin:24px 0 0;">{_cta("Open dashboard", _dashboard_url())}</p>
    """
    return _send(
        to=merchant_email,
        subject=subject,
        html=_wrap("Weekly report", inner),
        log_event="weekly_report_email",
        log_context={
            "shop_domain": shop_domain,
            "score": current_score,
            "trend": trend,
            "issues_count": issues_count,
        },
    )


def send_uninstall_feedback(merchant_email: str, shop_domain: str) -> bool:
    subject = "Sorry to see you go — quick feedback?"
    inner = f"""
    <h1 style="margin:0 0 8px;font-size:22px;font-weight:600;color:#111827;">
      Thanks for trying StoreMD.
    </h1>
    <p style="margin:0 0 16px;color:#4b5563;font-size:14px;">
      We saw you uninstalled the app on <strong>{shop_domain}</strong>. No
      hard feelings — but if you have a minute, we'd love to know why.
    </p>
    <p style="margin:0 0 16px;color:#4b5563;font-size:14px;">
      Common answers we hear:
    </p>
    <ul style="margin:0 0 16px;padding-left:20px;color:#4b5563;font-size:14px;line-height:1.6;">
      <li>Didn't surface anything actionable</li>
      <li>Too expensive for the value</li>
      <li>Found a different tool that does the same thing</li>
      <li>Just trying it out, no real plan to keep it</li>
    </ul>
    <p style="margin:0 0 16px;color:#4b5563;font-size:14px;">
      Just hit reply — even one line helps us improve. Thanks.
    </p>
    """
    return _send(
        to=merchant_email,
        subject=subject,
        html=_wrap("Uninstall feedback", inner),
        log_event="uninstall_feedback_email",
        log_context={"shop_domain": shop_domain},
    )
