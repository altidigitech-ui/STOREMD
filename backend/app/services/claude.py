"""Claude API client — analyze scan results and generate fixes."""

from __future__ import annotations

import time

import anthropic
import structlog

from app.config import settings
from app.core.exceptions import AgentError, ErrorCode

logger = structlog.get_logger()

# Lazy client initialization
_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


# ---------------------------------------------------------------------------
# Prompts (from docs/AGENT.md)
# ---------------------------------------------------------------------------

ANALYSIS_PROMPT = """You are StoreMD, an AI agent that monitors Shopify store health.

STORE INFO:
- Name: {store_name}
- Domain: {shop_domain}
- Theme: {theme_name}
- Apps: {apps_count} installed
- Products: {products_count}
- Shopify Plan: {shopify_plan}

SCAN RESULTS (raw data from scanners):
{scanner_results_json}

MERCHANT HISTORY (from memory):
{merchant_memory}

MERCHANT PREFERENCES (learned from past feedback):
{merchant_preferences}

CROSS-STORE INTELLIGENCE:
{cross_store_signals}

INSTRUCTIONS:
1. Analyze the scan results considering the merchant's history.
2. Calculate the health score (0-100) using weights:
   - Mobile speed: 30%
   - Desktop speed: 20%
   - App impact: 20%
   - Code quality: 15%
   - SEO basics: 15%
3. Compare with the merchant's baseline score (from history).
4. Identify the top 3 most impactful issues, sorted by impact.
5. For each issue, provide a clear recommendation.
6. If the merchant has rejected similar recommendations before, suggest ALTERNATIVES.
7. Note the overall trend (improving, stable, degrading).

RESPOND IN JSON:
{{
  "score": <int 0-100>,
  "mobile_score": <int 0-100>,
  "desktop_score": <int 0-100>,
  "trend": "up|down|stable",
  "summary": "<1 paragraph health assessment>",
  "top_issues": [
    {{
      "title": "<short title>",
      "severity": "critical|major|minor",
      "impact": "<human-readable impact>",
      "impact_value": <float>,
      "impact_unit": "seconds|dollars|products|percent",
      "scanner": "<scanner_name>",
      "recommendation": "<what to do, in simple language>",
      "fix_type": "one_click|manual|developer",
      "alternative": "<alternative if merchant rejected similar before, or null>"
    }}
  ]
}}"""

FIX_PROMPT = """Generate a clear, actionable fix for this Shopify store issue.

ISSUE:
- Title: {issue_title}
- Scanner: {scanner}
- Severity: {severity}
- Impact: {impact}
- Context: {context_json}

MERCHANT PREFERENCES:
{preferences}

INSTRUCTIONS:
- Write in simple, non-technical language.
- Be specific: say WHAT to do, WHERE to do it, and WHY.
- If one_click fix is possible, describe what will happen automatically.
- If manual, provide step-by-step instructions.
- Keep it under 3 sentences.

RESPOND IN JSON:
{{
  "fix_description": "<clear action to take>",
  "fix_type": "one_click|manual|developer",
  "estimated_impact": "<what improves>",
  "steps": ["<step 1>", "<step 2>"] or null,
  "auto_fixable": <bool>
}}"""


# ---------------------------------------------------------------------------
# API functions
# ---------------------------------------------------------------------------


async def claude_analyze(prompt: str) -> str:
    """Call Claude API for scan analysis.

    Model: claude-sonnet-4-20250514, temperature 0.3, max_tokens 4096.
    """
    client = _get_client()
    start = time.perf_counter()

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        )

        duration_ms = round((time.perf_counter() - start) * 1000)
        text = response.content[0].text

        logger.info(
            "claude_analyze_complete",
            tokens_input=response.usage.input_tokens,
            tokens_output=response.usage.output_tokens,
            duration_ms=duration_ms,
        )

        return text

    except anthropic.RateLimitError as exc:
        raise AgentError(
            code=ErrorCode.CLAUDE_API_RATE_LIMIT,
            message="Claude API rate limited",
            status_code=429,
        ) from exc
    except anthropic.APITimeoutError as exc:
        raise AgentError(
            code=ErrorCode.CLAUDE_API_TIMEOUT,
            message="Claude API timeout",
            status_code=504,
        ) from exc
    except anthropic.APIError as exc:
        raise AgentError(
            code=ErrorCode.CLAUDE_API_ERROR,
            message=f"Claude API error: {exc}",
            status_code=502,
        ) from exc


async def claude_generate_fix(prompt: str) -> str:
    """Call Claude API for fix generation.

    Model: claude-sonnet-4-20250514, temperature 0.5, max_tokens 1024.
    """
    client = _get_client()
    start = time.perf_counter()

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            temperature=0.5,
            messages=[{"role": "user", "content": prompt}],
        )

        duration_ms = round((time.perf_counter() - start) * 1000)
        text = response.content[0].text

        logger.info(
            "claude_fix_complete",
            tokens_input=response.usage.input_tokens,
            tokens_output=response.usage.output_tokens,
            duration_ms=duration_ms,
        )

        return text

    except anthropic.RateLimitError as exc:
        raise AgentError(
            code=ErrorCode.CLAUDE_API_RATE_LIMIT,
            message="Claude API rate limited",
            status_code=429,
        ) from exc
    except anthropic.APITimeoutError as exc:
        raise AgentError(
            code=ErrorCode.CLAUDE_API_TIMEOUT,
            message="Claude API timeout",
            status_code=504,
        ) from exc
    except anthropic.APIError as exc:
        raise AgentError(
            code=ErrorCode.CLAUDE_API_ERROR,
            message=f"Claude API error: {exc}",
            status_code=502,
        ) from exc
