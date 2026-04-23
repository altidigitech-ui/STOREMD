"""SEO checker for the public preview scan."""

from __future__ import annotations

from html.parser import HTMLParser

import httpx

from app.agent.preview.models import PreviewCheckerResult, PreviewIssue


class _SEOParser(HTMLParser):
    """Single-pass HTML parser for SEO meta signals."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: str | None = None
        self.description: str | None = None
        self.canonical: str | None = None
        self.og_title: str | None = None
        self.og_description: str | None = None
        self.og_image: str | None = None
        self.twitter_card: str | None = None
        self.html_lang: str | None = None
        self.h1_count = 0
        self.headings: list[int] = []

        self._in_title = False
        self._title_buf: list[str] = []
        self._h_open: int | None = None
        self._h_buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k.lower(): (v or "") for k, v in attrs}

        if tag == "html":
            lang = a.get("lang", "").strip()
            if lang:
                self.html_lang = lang
            return

        if tag == "title":
            self._in_title = True
            self._title_buf = []
            return

        if tag == "meta":
            name = a.get("name", "").lower().strip()
            prop = a.get("property", "").lower().strip()
            content = a.get("content", "").strip()

            if name == "description":
                self.description = content
            elif prop == "og:title":
                self.og_title = content
            elif prop == "og:description":
                self.og_description = content
            elif prop == "og:image":
                self.og_image = content
            elif name == "twitter:card":
                self.twitter_card = content
            return

        if tag == "link":
            rel = a.get("rel", "").lower().strip()
            if "canonical" in rel:
                self.canonical = a.get("href", "").strip() or None
            return

        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(tag[1])
            if level == 1:
                self.h1_count += 1
            self._h_open = level
            self._h_buf = []
            return

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_buf.append(data)
        if self._h_open is not None:
            self._h_buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self._in_title:
            self.title = "".join(self._title_buf).strip() or None
            self._in_title = False
            self._title_buf = []
            return

        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"} and self._h_open is not None:
            text = "".join(self._h_buf).strip()
            if text:
                self.headings.append(self._h_open)
            self._h_open = None
            self._h_buf = []
            return

    def heading_skips(self) -> int:
        skips = 0
        prev: int | None = None
        for level in self.headings:
            if prev is not None and level > prev + 1:
                skips += 1
            prev = level
        return skips


class SEOChecker:
    """Check SEO signals from the homepage HTML."""

    async def check(self, html: str, headers: httpx.Headers) -> PreviewCheckerResult:
        parser = _SEOParser()
        parser.feed(html)

        issues: list[PreviewIssue] = []

        # Title
        if not parser.title:
            issues.append(PreviewIssue(
                severity="critical",
                title="Missing page title",
                description="Your homepage has no <title> tag. Search engines use this as the primary ranking signal and display it in search results.",
                category="seo",
            ))
        else:
            length = len(parser.title)
            if length > 60:
                issues.append(PreviewIssue(
                    severity="minor",
                    title="Page title too long",
                    description=f"Your title is {length} characters. Google truncates titles over 60 characters in search results.",
                    category="seo",
                ))
            elif length < 10:
                issues.append(PreviewIssue(
                    severity="minor",
                    title="Page title too short",
                    description=f"Your title is only {length} characters. A descriptive title (10–60 chars) improves click-through rates.",
                    category="seo",
                ))

        # Meta description
        if parser.description is None:
            issues.append(PreviewIssue(
                severity="critical",
                title="Missing meta description",
                description="No <meta name=\"description\"> found. Google uses this as the snippet in search results, directly affecting click-through rate.",
                category="seo",
            ))
        else:
            length = len(parser.description)
            if length > 160:
                issues.append(PreviewIssue(
                    severity="minor",
                    title="Meta description too long",
                    description=f"Your meta description is {length} characters. Google truncates descriptions over 160 characters.",
                    category="seo",
                ))
            elif length < 50:
                issues.append(PreviewIssue(
                    severity="minor",
                    title="Meta description too short",
                    description=f"Your meta description is only {length} characters. Aim for 50–160 characters to maximise snippet quality.",
                    category="seo",
                ))

        # Canonical
        if not parser.canonical:
            issues.append(PreviewIssue(
                severity="major",
                title="Missing canonical URL",
                description="No <link rel=\"canonical\"> found. Without it, duplicate content across URL variants can dilute your search ranking.",
                category="seo",
            ))

        # OG tags
        missing_og = []
        if not parser.og_title:
            missing_og.append("og:title")
        if not parser.og_description:
            missing_og.append("og:description")
        if not parser.og_image:
            missing_og.append("og:image")
        if missing_og:
            issues.append(PreviewIssue(
                severity="major",
                title="Missing Open Graph tags",
                description=f"Missing: {', '.join(missing_og)}. OG tags control how your store looks when shared on Facebook, LinkedIn, and other platforms.",
                category="seo",
            ))

        # Twitter Card
        if not parser.twitter_card:
            issues.append(PreviewIssue(
                severity="minor",
                title="Missing Twitter Card tags",
                description="No <meta name=\"twitter:card\"> found. Twitter Card tags improve how your links appear when shared on X/Twitter.",
                category="seo",
            ))

        # H1 count
        if parser.h1_count == 0:
            issues.append(PreviewIssue(
                severity="major",
                title="No H1 heading found",
                description="Your homepage has no <h1> tag. Search engines rely on H1 to understand the primary topic of a page.",
                category="seo",
            ))
        elif parser.h1_count > 1:
            issues.append(PreviewIssue(
                severity="major",
                title=f"Multiple H1 headings ({parser.h1_count})",
                description=f"Your page has {parser.h1_count} H1 tags. There should be exactly one H1 per page for optimal SEO signal clarity.",
                category="seo",
            ))

        # Heading hierarchy
        skips = parser.heading_skips()
        if skips > 0:
            issues.append(PreviewIssue(
                severity="minor",
                title="Heading hierarchy skips levels",
                description=f"Found {skips} heading level skip(s) (e.g. H1 → H3 with no H2). This breaks screen-reader navigation and confuses search engines.",
                category="seo",
            ))

        # HTML lang attribute
        if not parser.html_lang:
            issues.append(PreviewIssue(
                severity="minor",
                title="Missing language attribute on <html>",
                description="The <html> element has no lang attribute. This helps search engines index your content in the right language and region.",
                category="seo",
            ))

        return PreviewCheckerResult(
            checker_name="seo",
            issues=issues,
            metrics={
                "title_length": len(parser.title) if parser.title else 0,
                "description_length": len(parser.description) if parser.description else 0,
                "h1_count": parser.h1_count,
            },
        )
