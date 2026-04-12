"""Celery tasks for the Playwright browser scanners.

Browser scanners run in their own Celery task because:
- They're heavy (RAM, CPU, time)
- They need the worker image (Dockerfile.worker) which has Chromium
- They must run sequentially (not parallel) — Playwright is RAM-greedy

The orchestrator already groups browser scanners under `group="browser"`
and runs them sequentially via _run_sequential() with a 90s per-scanner
timeout — so a regular run_scan() that includes the "browser" module
will already pick them up. This module exposes a dedicated task for
cases where we want to run *only* the browser scans (e.g. on-demand
re-render after a theme update).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import structlog

from app.core.exceptions import ErrorCode, ShopifyError
from app.dependencies import get_supabase_service
from tasks.celery_app import celery_app

logger = structlog.get_logger()


# Hard caps from .claude/skills/browser-automation/SKILL.md
PER_SCANNER_TIMEOUT_S = 90
TOTAL_TIMEOUT_S = 5 * 60  # 5 minutes


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def run_browser_scan(
    self,
    scan_id: str,
    store_id: str,
    merchant_id: str,
) -> None:
    """Run only the browser scanners for a given scan.

    Useful for triggering Playwright work outside of the main scan
    pipeline (theme update webhook, on-demand visual diff, etc).
    """
    _run_async(
        _run_browser_scan_async(self, scan_id, store_id, merchant_id)
    )


async def _run_browser_scan_async(
    task,
    scan_id: str,
    store_id: str,
    merchant_id: str,
) -> None:
    from app.agent.browser.accessibility_live import AccessibilityLiveTest
    from app.agent.browser.real_user_simulation import RealUserSimulation
    from app.agent.browser.visual_store_test import VisualStoreTest
    from app.agent.memory import get_store_memory
    from app.services.shopify import ShopifyClient

    supabase = get_supabase_service()

    # Mark scan as running
    supabase.table("scans").update(
        {
            "status": "running",
            "started_at": datetime.now(UTC).isoformat(),
        }
    ).eq("id", scan_id).execute()

    try:
        store = (
            supabase.table("stores")
            .select("*")
            .eq("id", store_id)
            .single()
            .execute()
        )
        merchant = (
            supabase.table("merchants")
            .select("shopify_access_token_encrypted")
            .eq("id", merchant_id)
            .single()
            .execute()
        )
        if not store.data or not merchant.data:
            raise ValueError("Store or merchant not found")

        encrypted_token = merchant.data["shopify_access_token_encrypted"]
        shopify = ShopifyClient(
            store.data["shopify_shop_domain"], encrypted_token
        )

        memory = get_store_memory()
        memory_context: list[dict] = []
        try:
            ctx = await memory.recall_for_scan(
                merchant_id=merchant_id,
                store_id=store_id,
                modules=["browser"],
            )
            memory_context = list(ctx.get("merchant", [])) + list(
                ctx.get("store", [])
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "browser_scan_memory_failed",
                scan_id=scan_id,
                error=str(exc),
            )

        # Sequential — Playwright is RAM-heavy.
        scanners = [VisualStoreTest(), RealUserSimulation(), AccessibilityLiveTest()]
        results: dict = {}
        errors: list[str] = []
        deadline = asyncio.get_event_loop().time() + TOTAL_TIMEOUT_S

        for scanner in scanners:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                logger.warning(
                    "browser_scan_total_timeout",
                    scan_id=scan_id,
                    pending=scanner.name,
                )
                errors.append(
                    f"Scanner {scanner.name} skipped — total timeout"
                )
                break
            timeout = min(PER_SCANNER_TIMEOUT_S, remaining)
            try:
                result = await asyncio.wait_for(
                    scanner.scan(store_id, shopify, memory_context),
                    timeout=timeout,
                )
                results[scanner.name] = {
                    "issues": len(result.issues),
                    "metrics": result.metrics,
                }
                # Persist issues immediately.
                for issue in result.issues:
                    try:
                        supabase.table("scan_issues").insert(
                            {
                                "scan_id": scan_id,
                                "store_id": store_id,
                                "merchant_id": merchant_id,
                                "module": issue.module,
                                "scanner": issue.scanner,
                                "severity": issue.severity,
                                "title": issue.title,
                                "description": issue.description,
                                "impact": issue.impact,
                                "impact_value": (
                                    float(issue.impact_value)
                                    if issue.impact_value is not None
                                    else None
                                ),
                                "impact_unit": issue.impact_unit,
                                "fix_type": issue.fix_type,
                                "fix_description": issue.fix_description,
                                "auto_fixable": issue.auto_fixable,
                                "context": issue.context,
                            }
                        ).execute()
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(
                            "browser_issue_insert_failed",
                            scanner=scanner.name,
                            error=str(exc),
                        )
            except asyncio.TimeoutError:
                logger.warning(
                    "browser_scanner_timeout",
                    scanner=scanner.name,
                    timeout=timeout,
                )
                errors.append(
                    f"Scanner {scanner.name} timed out after {timeout}s"
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "browser_scanner_failed",
                    scanner=scanner.name,
                    error=str(exc),
                )
                errors.append(f"Scanner {scanner.name}: {exc}")

        # Mark scan complete (browser-only).
        supabase.table("scans").update(
            {
                "status": "completed",
                "partial_scan": bool(errors),
                "completed_at": datetime.now(UTC).isoformat(),
                "scanner_results": results,
            }
        ).eq("id", scan_id).execute()

        logger.info(
            "browser_scan_completed",
            scan_id=scan_id,
            scanners=len(results),
            errors=len(errors),
        )

    except ShopifyError as exc:
        if exc.code == ErrorCode.SHOPIFY_RATE_LIMIT:
            logger.warning("browser_scan_retry_rate_limit", scan_id=scan_id)
            supabase.table("scans").update({"status": "pending"}).eq(
                "id", scan_id
            ).execute()
            task.retry(countdown=180)
        else:
            _mark_failed(supabase, scan_id, str(exc), exc.code.value)
            raise
    except Exception as exc:  # noqa: BLE001
        logger.error("browser_scan_failed", scan_id=scan_id, error=str(exc))
        _mark_failed(supabase, scan_id, str(exc), ErrorCode.SCAN_FAILED.value)
        raise


def _mark_failed(supabase, scan_id: str, message: str, code: str) -> None:
    supabase.table("scans").update(
        {
            "status": "failed",
            "error_message": message[:500],
            "error_code": code,
            "completed_at": datetime.now(UTC).isoformat(),
        }
    ).eq("id", scan_id).execute()
