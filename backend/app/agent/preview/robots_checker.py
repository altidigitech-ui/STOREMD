"""Robots.txt and sitemap checker for the public preview scan."""

from __future__ import annotations

import httpx

from app.agent.preview.models import PreviewCheckerResult, PreviewIssue

_TIMEOUT_S = 5.0


class RobotsChecker:
    """Check robots.txt and sitemap.xml availability."""

    async def check(
        self,
        store_url: str,
        client: httpx.AsyncClient,
    ) -> PreviewCheckerResult:
        issues: list[PreviewIssue] = []
        metrics: dict = {}

        robots_url = f"{store_url.rstrip('/')}/robots.txt"
        sitemap_url = f"{store_url.rstrip('/')}/sitemap.xml"

        # --- robots.txt ---
        robots_text: str | None = None
        try:
            resp = await client.get(robots_url, timeout=_TIMEOUT_S, follow_redirects=True)
            metrics["robots_status"] = resp.status_code
            if resp.status_code == 404:
                issues.append(PreviewIssue(
                    severity="minor",
                    title="robots.txt not found",
                    description="Your store has no /robots.txt file. Without it, crawlers have no guidance on which pages to index.",
                    category="robots",
                    fix_available_after_install=True,
                ))
            elif resp.status_code < 400:
                robots_text = resp.text
                # Blocked entirely?
                for line in robots_text.splitlines():
                    stripped = line.strip()
                    if stripped.lower().startswith("disallow:"):
                        value = stripped[len("disallow:"):].strip()
                        if value == "/":
                            issues.append(PreviewIssue(
                                severity="critical",
                                title="robots.txt blocks all crawlers",
                                description="Your robots.txt contains 'Disallow: /' which blocks search engines from indexing your entire store. This will devastate your search visibility.",
                                category="robots",
                                fix_available_after_install=True,
                            ))
                            break
        except Exception:
            metrics["robots_status"] = None

        # --- sitemap.xml ---
        try:
            resp = await client.get(sitemap_url, timeout=_TIMEOUT_S, follow_redirects=True)
            metrics["sitemap_status"] = resp.status_code
            if resp.status_code == 404:
                issues.append(PreviewIssue(
                    severity="major",
                    title="sitemap.xml not found",
                    description="Your store has no /sitemap.xml. Without a sitemap, search engines may miss pages and index your store more slowly.",
                    category="robots",
                    fix_available_after_install=True,
                ))
            elif resp.status_code >= 500:
                issues.append(PreviewIssue(
                    severity="major",
                    title=f"sitemap.xml server error ({resp.status_code})",
                    description=f"Your /sitemap.xml returned a {resp.status_code} error. Search engines cannot use a broken sitemap.",
                    category="robots",
                    fix_available_after_install=True,
                ))
        except Exception:
            metrics["sitemap_status"] = None

        # robots.txt exists but doesn't reference a sitemap
        if robots_text is not None and "sitemap:" not in robots_text.lower():
            issues.append(PreviewIssue(
                severity="info",
                title="robots.txt does not reference sitemap",
                description="Your robots.txt exists but doesn't include a Sitemap: directive. Adding one helps search engines discover your sitemap faster.",
                category="robots",
                fix_available_after_install=True,
            ))

        return PreviewCheckerResult(
            checker_name="robots",
            issues=issues,
            metrics=metrics,
        )
