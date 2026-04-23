"""Accessibility checker for the public preview scan.

Reuses _AccessibilityParser from the existing static accessibility scanner
to avoid duplicating HTML parsing logic.
"""

from __future__ import annotations

from app.agent.analyzers.accessibility import _AccessibilityParser
from app.agent.preview.models import PreviewCheckerResult, PreviewIssue


class AccessibilityChecker:
    """Check accessibility signals from the homepage HTML."""

    async def check(self, html: str) -> PreviewCheckerResult:
        parser = _AccessibilityParser()
        parser.feed(html)

        issues: list[PreviewIssue] = []
        missing_alt = parser.imgs_missing_alt

        if missing_alt > 5:
            issues.append(PreviewIssue(
                severity="critical",
                title=f"{missing_alt} images missing alt text",
                description=f"Found {missing_alt} images without alt attributes. This fails WCAG 2.1 Level A and excludes visually-impaired users from your content.",
                category="accessibility",
            ))
        elif missing_alt > 0:
            issues.append(PreviewIssue(
                severity="major",
                title=f"{missing_alt} image{'s' if missing_alt > 1 else ''} missing alt text",
                description=f"Found {missing_alt} image{'s' if missing_alt > 1 else ''} without alt attributes, violating WCAG 2.1 SC 1.1.1.",
                category="accessibility",
            ))

        missing_label = parser.inputs_missing_label()
        if missing_label > 0:
            issues.append(PreviewIssue(
                severity="major",
                title=f"{missing_label} form input{'s' if missing_label > 1 else ''} without label",
                description=f"Found {missing_label} <input> element{'s' if missing_label > 1 else ''} with no associated <label>. Screen readers cannot identify these fields.",
                category="accessibility",
            ))

        empty_links = parser.links_empty
        if empty_links > 0:
            issues.append(PreviewIssue(
                severity="major",
                title=f"{empty_links} link{'s' if empty_links > 1 else ''} with no text",
                description=f"Found {empty_links} anchor element{'s' if empty_links > 1 else ''} with no visible or aria text. Screen readers will announce these as empty.",
                category="accessibility",
            ))

        unnamed_buttons = parser.buttons_no_name
        if unnamed_buttons > 0:
            issues.append(PreviewIssue(
                severity="major",
                title=f"{unnamed_buttons} button{'s' if unnamed_buttons > 1 else ''} with no accessible name",
                description=f"Found {unnamed_buttons} <button> element{'s' if unnamed_buttons > 1 else ''} with no text or aria-label. Keyboard and screen-reader users cannot identify these controls.",
                category="accessibility",
            ))

        skips = parser.heading_skips()
        if skips > 0:
            issues.append(PreviewIssue(
                severity="minor",
                title="Heading hierarchy skips levels",
                description=f"Found {skips} heading level skip(s). Correct hierarchy (H1 → H2 → H3) is required for WCAG 2.1 SC 1.3.1.",
                category="accessibility",
            ))

        return PreviewCheckerResult(
            checker_name="accessibility",
            issues=issues,
            metrics={
                "imgs_total": parser.imgs_total,
                "imgs_missing_alt": missing_alt,
                "inputs_missing_label": missing_label,
                "links_empty": empty_links,
                "buttons_no_name": unnamed_buttons,
            },
        )
