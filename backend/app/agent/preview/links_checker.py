"""Broken links checker for the public preview scan."""

from __future__ import annotations

import asyncio
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx

from app.agent.preview.models import PreviewCheckerResult, PreviewIssue

_MAX_LINKS = 30
_CONCURRENCY = 5
_HEAD_TIMEOUT_S = 10.0
_SKIP_SCHEMES = {"mailto", "tel", "javascript", "data"}


class _LinkParser(HTMLParser):
    """Extract href values from <a> tags."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        for k, v in attrs:
            if k == "href" and v:
                self.hrefs.append(v.strip())


def _resolve_links(hrefs: list[str], base_url: str) -> list[str]:
    """Resolve hrefs to absolute URLs, filtering out non-HTTP links and anchors."""
    base_parsed = urlparse(base_url)
    seen: set[str] = set()
    result: list[str] = []

    for href in hrefs:
        # Skip anchors and empty
        if not href or href.startswith("#"):
            continue
        parsed = urlparse(href)
        # Skip non-HTTP schemes
        if parsed.scheme and parsed.scheme in _SKIP_SCHEMES:
            continue
        # Resolve relative URLs
        absolute = urljoin(base_url, href)
        # Only keep HTTP(S)
        abs_parsed = urlparse(absolute)
        if abs_parsed.scheme not in {"http", "https"}:
            continue
        # Remove fragment
        clean = abs_parsed._replace(fragment="").geturl()
        if clean not in seen:
            seen.add(clean)
            result.append(clean)

    return result


async def _check_link(
    url: str,
    base_scheme: str,
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
) -> PreviewIssue | None:
    async with sem:
        try:
            resp = await client.head(url, timeout=_HEAD_TIMEOUT_S, follow_redirects=True)
            status = resp.status_code

            # Mixed content: HTTP link on an HTTPS page
            parsed = urlparse(url)
            if base_scheme == "https" and parsed.scheme == "http":
                return PreviewIssue(
                    severity="minor",
                    title="Mixed content link",
                    description=f"Link to {url} uses HTTP on an HTTPS page, which may trigger browser security warnings.",
                    category="links",
                )

            if status == 404:
                return PreviewIssue(
                    severity="major",
                    title=f"Broken link (404): {url}",
                    description=f"The link {url} returned 404 Not Found. Broken links hurt SEO and customer trust.",
                    category="links",
                )
            if status >= 500:
                return PreviewIssue(
                    severity="major",
                    title=f"Server error on link ({status}): {url}",
                    description=f"The link {url} returned a {status} server error.",
                    category="links",
                )
        except httpx.TimeoutException:
            return PreviewIssue(
                severity="minor",
                title=f"Link timed out: {url}",
                description=f"The link {url} did not respond within {_HEAD_TIMEOUT_S}s. It may be slow or unreachable.",
                category="links",
            )
        except Exception:
            pass  # Network errors on individual links are not reported
    return None


class LinksChecker:
    """Check for broken internal and external links."""

    async def check(
        self,
        html: str,
        store_url: str,
        client: httpx.AsyncClient,
    ) -> PreviewCheckerResult:
        parser = _LinkParser()
        parser.feed(html)

        resolved = _resolve_links(parser.hrefs, store_url)[:_MAX_LINKS]
        base_scheme = urlparse(store_url).scheme

        sem = asyncio.Semaphore(_CONCURRENCY)
        tasks = [_check_link(url, base_scheme, client, sem) for url in resolved]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        issues: list[PreviewIssue] = []
        for r in results:
            if isinstance(r, PreviewIssue):
                issues.append(r)

        return PreviewCheckerResult(
            checker_name="links",
            issues=issues,
            metrics={
                "links_checked": len(resolved),
                "broken_count": len(issues),
            },
        )
