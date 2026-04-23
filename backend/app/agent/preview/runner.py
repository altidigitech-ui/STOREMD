"""Orchestrator for the public preview scan.

Runs all checkers concurrently with asyncio.gather — no Celery, no LangGraph.
The entire scan completes inside a single HTTP request (≤ 30s total).
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import asdict

import httpx
import structlog

from app.agent.preview.accessibility_checker import AccessibilityChecker
from app.agent.preview.links_checker import LinksChecker
from app.agent.preview.models import (
    LockedModule,
    PreviewCheckerResult,
    PreviewIssue,
    PreviewScanResult,
)
from app.agent.preview.performance_checker import PerformanceChecker
from app.agent.preview.robots_checker import RobotsChecker
from app.agent.preview.security_checker import SecurityChecker
from app.agent.preview.seo_checker import SEOChecker

logger = structlog.get_logger()

LOCKED_MODULES = [
    LockedModule(
        "App Impact Analysis",
        "Find which installed apps slow your store down the most",
    ),
    LockedModule(
        "Ghost Billing Detection",
        "Find apps you're paying for but not using",
    ),
    LockedModule(
        "Code Residue Scanner",
        "Detect leftover code from uninstalled apps",
    ),
    LockedModule(
        "Listing Optimizer",
        "AI-powered product listing improvements",
    ),
    LockedModule(
        "Auto-Fix Engine",
        "One-click fixes for SEO, accessibility and broken links",
    ),
    LockedModule(
        "Email Health",
        "SPF/DKIM/DMARC checks on your sending domain",
    ),
    LockedModule(
        "Real Browser Testing",
        "Playwright-based performance and visual testing",
    ),
]

_CHECKS_AVAILABLE_AFTER_INSTALL = 21

_CONNECT_TIMEOUT = 10.0
_READ_TIMEOUT = 20.0
_TOTAL_TIMEOUT = 30.0


def _error_result(
    shop_domain: str,
    store_url: str,
    start: float,
    message: str,
) -> PreviewScanResult:
    return PreviewScanResult(
        shop_domain=shop_domain,
        store_url=store_url,
        preview_score=0,
        scan_duration_ms=int((time.monotonic() - start) * 1000),
        checks_run=0,
        checks_available_after_install=_CHECKS_AVAILABLE_AFTER_INSTALL,
        error=message,
        locked_modules=LOCKED_MODULES,
    )


async def run_preview_scan(shop_domain: str) -> PreviewScanResult:
    store_url = f"https://{shop_domain}"
    start = time.monotonic()

    timeout = httpx.Timeout(
        connect=_CONNECT_TIMEOUT,
        read=_READ_TIMEOUT,
        write=5.0,
        pool=5.0,
    )

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "StoreMD-Preview/1.0 (+https://storemd.vercel.app)"},
        ) as client:
            try:
                response = await client.get(store_url)
            except httpx.ConnectError:
                return _error_result(
                    shop_domain, store_url, start,
                    "Could not connect to your store. Please check the domain and try again.",
                )
            except httpx.TimeoutException:
                return _error_result(
                    shop_domain, store_url, start,
                    "Your store took too long to respond. Please try again later.",
                )

            html = response.text
            headers = response.headers
            elapsed_ms = response.elapsed.total_seconds() * 1000
            status_code = response.status_code
            redirect_count = len(response.history)

            # Password-protected store detection
            html_lower = html.lower()
            if (
                "password" in html_lower
                and "<form" in html_lower
                and 'id="login_form"' in html_lower
            ):
                return _error_result(
                    shop_domain, store_url, start,
                    "Your store is password-protected. Remove the password or install StoreMD directly to scan.",
                )

            # Run all checkers concurrently, sharing the same client for HTTP sub-requests
            seo = SEOChecker()
            a11y = AccessibilityChecker()
            security = SecurityChecker()
            perf = PerformanceChecker()
            links = LinksChecker()
            robots = RobotsChecker()

            checker_results = await asyncio.gather(
                seo.check(html, headers),
                a11y.check(html),
                security.check(headers, store_url),
                perf.check(html, headers, elapsed_ms, status_code, redirect_count),
                links.check(html, store_url, client),
                robots.check(store_url, client),
                return_exceptions=True,
            )

    except Exception as exc:
        logger.error("preview_scan_unexpected_error", shop=shop_domain, error=str(exc))
        return _error_result(
            shop_domain, store_url, start,
            "An unexpected error occurred while scanning. Please try again.",
        )

    # Aggregate results
    all_issues: list[PreviewIssue] = []
    checks_run = 0
    for result in checker_results:
        if isinstance(result, Exception):
            logger.warning("preview_checker_failed", error=str(result))
            continue
        checks_run += 1
        all_issues.extend(result.issues)

    # Score: start at 100, deduct for each issue
    score = 100
    for issue in all_issues:
        if issue.severity == "critical":
            score -= 10
        elif issue.severity == "major":
            score -= 5
        elif issue.severity == "minor":
            score -= 2
    score = max(0, min(100, score))

    summary = {
        "critical": sum(1 for i in all_issues if i.severity == "critical"),
        "major": sum(1 for i in all_issues if i.severity == "major"),
        "minor": sum(1 for i in all_issues if i.severity == "minor"),
        "info": sum(1 for i in all_issues if i.severity == "info"),
    }

    duration_ms = int((time.monotonic() - start) * 1000)

    logger.info(
        "preview_scan_complete",
        shop=shop_domain,
        score=score,
        issues=len(all_issues),
        checks_run=checks_run,
        duration_ms=duration_ms,
    )

    return PreviewScanResult(
        shop_domain=shop_domain,
        store_url=store_url,
        preview_score=score,
        scan_duration_ms=duration_ms,
        checks_run=checks_run,
        checks_available_after_install=_CHECKS_AVAILABLE_AFTER_INSTALL,
        issues=all_issues,
        summary=summary,
        locked_modules=LOCKED_MODULES,
    )
