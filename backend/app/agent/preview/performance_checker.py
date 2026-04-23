"""Performance checker for the public preview scan."""

from __future__ import annotations

import httpx

from app.agent.preview.models import PreviewCheckerResult, PreviewIssue


class PerformanceChecker:
    """Check performance signals from the homepage response."""

    async def check(
        self,
        html: str,
        headers: httpx.Headers,
        elapsed_ms: float,
        status_code: int,
        redirect_count: int,
    ) -> PreviewCheckerResult:
        issues: list[PreviewIssue] = []
        html_bytes = len(html.encode())

        # TTFB
        if elapsed_ms > 3000:
            issues.append(PreviewIssue(
                severity="critical",
                title=f"Very slow server response ({elapsed_ms / 1000:.1f}s)",
                description=f"Your store took {elapsed_ms / 1000:.1f} seconds to respond. Google's Core Web Vitals benchmark is under 600ms. Slow servers directly hurt SEO rankings.",
                category="performance",
            ))
        elif elapsed_ms > 1500:
            issues.append(PreviewIssue(
                severity="major",
                title=f"Slow server response ({elapsed_ms / 1000:.1f}s)",
                description=f"Your store took {elapsed_ms / 1000:.1f} seconds to respond. Aim for under 600ms for a good Core Web Vitals score.",
                category="performance",
            ))

        # HTML size
        if html_bytes > 500_000:
            issues.append(PreviewIssue(
                severity="major",
                title=f"HTML payload very large ({html_bytes // 1000} KB)",
                description=f"Your homepage HTML is {html_bytes // 1000} KB. HTML over 500 KB often indicates excessive inline scripts or styles from installed apps.",
                category="performance",
            ))
        elif html_bytes > 200_000:
            issues.append(PreviewIssue(
                severity="minor",
                title=f"HTML payload large ({html_bytes // 1000} KB)",
                description=f"Your homepage HTML is {html_bytes // 1000} KB. Leaner HTML (under 200 KB) loads faster and ranks better.",
                category="performance",
            ))

        # Redirects
        if redirect_count > 2:
            issues.append(PreviewIssue(
                severity="minor",
                title=f"Excessive redirects ({redirect_count})",
                description=f"Found {redirect_count} HTTP redirects before reaching your homepage. Each redirect adds latency and can hurt crawl budget.",
                category="performance",
            ))

        # Compression
        content_encoding = headers.get("content-encoding", "").lower()
        if not content_encoding:
            issues.append(PreviewIssue(
                severity="major",
                title="No response compression",
                description="Your server is not sending compressed responses (no Content-Encoding header). Enabling gzip or Brotli can reduce HTML transfer size by 70–80%.",
                category="performance",
            ))

        return PreviewCheckerResult(
            checker_name="performance",
            issues=issues,
            metrics={
                "elapsed_ms": elapsed_ms,
                "html_bytes": html_bytes,
                "redirect_count": redirect_count,
                "content_encoding": content_encoding or None,
            },
        )
