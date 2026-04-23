"""Security header checker for the public preview scan."""

from __future__ import annotations

import httpx

from app.agent.preview.models import PreviewCheckerResult, PreviewIssue


class SecurityChecker:
    """Check HTTP security headers from the homepage response."""

    async def check(self, headers: httpx.Headers, store_url: str) -> PreviewCheckerResult:
        issues: list[PreviewIssue] = []

        if "strict-transport-security" not in headers:
            issues.append(PreviewIssue(
                severity="major",
                title="HSTS not enabled",
                description="The Strict-Transport-Security header is missing. Without HSTS, browsers may load your store over HTTP, exposing customers to man-in-the-middle attacks.",
                category="security",
            ))

        if "x-content-type-options" not in headers:
            issues.append(PreviewIssue(
                severity="minor",
                title="X-Content-Type-Options header missing",
                description="The X-Content-Type-Options: nosniff header is missing. This can allow browsers to MIME-sniff responses and execute malicious scripts.",
                category="security",
            ))

        if "x-frame-options" not in headers:
            issues.append(PreviewIssue(
                severity="minor",
                title="X-Frame-Options header missing",
                description="The X-Frame-Options header is missing. Without it, your store could be embedded in an iframe and used for clickjacking attacks.",
                category="security",
            ))

        return PreviewCheckerResult(
            checker_name="security",
            issues=issues,
            metrics={
                "has_hsts": "strict-transport-security" in headers,
                "has_xcto": "x-content-type-options" in headers,
                "has_xfo": "x-frame-options" in headers,
            },
        )
