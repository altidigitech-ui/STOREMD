"""Scan orchestrator — LangGraph state machine for the scan pipeline.

Nodes:
1. load_memory     — Load Mem0 context (graceful degradation)
2. run_scanners    — Execute scanners by group (parallel/sequential)
3. analyze         — Claude API interprets results (fallback: rules-based)
4. generate_fixes  — Claude API generates recommendations
5. save_results    — Persist scan + issues to Supabase
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import structlog

from app.agent.analyzers import ScannerRegistry
from app.agent.analyzers.base import BaseScanner, ScannerResult
from app.models.scan import AgentState, ScanIssue

if TYPE_CHECKING:
    from supabase import Client as SupabaseClient

    from app.services.shopify import ShopifyClient

logger = structlog.get_logger()

# Score weights from AGENT.md
SCORE_WEIGHTS = {
    "mobile_speed": 0.30,
    "desktop_speed": 0.20,
    "app_impact": 0.20,
    "code_quality": 0.15,
    "seo_basics": 0.15,
}


class ScanOrchestrator:
    """Orchestrates the scan pipeline through LangGraph-style nodes."""

    def __init__(
        self,
        shopify: ShopifyClient,
        supabase: SupabaseClient,
        claude_analyze_fn=None,
        claude_fix_fn=None,
        memory=None,
    ) -> None:
        self.shopify = shopify
        self.supabase = supabase
        self.claude_analyze = claude_analyze_fn
        self.claude_fix = claude_fix_fn
        self.memory = memory
        self.registry = ScannerRegistry()

    async def run(self, state: AgentState) -> AgentState:
        """Execute the full scan pipeline sequentially."""
        state = await self.node_load_memory(state)
        await self._update_progress(state.scan_id, 10, "Loading store history...")
        state = await self.node_run_scanners(state)
        await self._update_progress(state.scan_id, 85, "Calculating health score...")
        state = await self.node_analyze(state)
        await self._update_progress(state.scan_id, 95, "Generating recommendations...")
        state = await self.node_generate_fixes(state)
        state = await self.node_save_results(state)
        await self._update_progress(state.scan_id, 100, "Done")
        return state

    async def _update_progress(
        self, scan_id: str, progress: int, current_step: str
    ) -> None:
        """Best-effort progress write — never break a scan on a transient
        Supabase glitch."""
        try:
            self.supabase.table("scans").update({
                "progress": progress,
                "current_step": current_step,
            }).eq("id", scan_id).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("progress_update_failed", error=str(exc))

    # ------------------------------------------------------------------
    # Node 1: Load Memory
    # ------------------------------------------------------------------

    async def node_load_memory(self, state: AgentState) -> AgentState:
        """Load Mem0 context (merchant + store + cross-store).

        Graceful degradation: a Mem0 outage never breaks a scan. The
        StoreMemory wrapper itself swallows errors and returns []; we
        keep the try/except as a final safety net.
        """
        if not self.memory:
            logger.info("memory_skipped", reason="no_memory_client")
            return state

        try:
            context = await self.memory.recall_for_scan(
                merchant_id=state.merchant_id,
                store_id=state.store_id,
                modules=state.modules,
            )
            # historical_context = merchant + store memories combined
            state.historical_context = list(context.get("merchant", [])) + list(
                context.get("store", [])
            )
            # merchant_preferences kept as a list for Claude prompt formatting
            state.merchant_preferences = context.get("merchant", [])
            state.cross_store_signals = context.get("cross_store", [])
            logger.info(
                "memory_loaded",
                store_id=state.store_id,
                merchant_memories=len(context.get("merchant", [])),
                store_memories=len(context.get("store", [])),
                cross_store_signals=len(context.get("cross_store", [])),
            )
        except Exception as exc:  # noqa: BLE001 — degrade gracefully
            logger.warning("memory_load_failed", error=str(exc))

        return state

    # ------------------------------------------------------------------
    # Node 2: Run Scanners
    # ------------------------------------------------------------------

    async def node_run_scanners(self, state: AgentState) -> AgentState:
        """Execute scanners by group: parallel API, parallel external, sequential browser."""
        plan = await self._get_merchant_plan(state.merchant_id)
        eligible = await self.registry.get_eligible(state.modules, plan)

        # Separate by group
        group_api = [s for s in eligible if s.group == "shopify_api"]
        group_ext = [s for s in eligible if s.group == "external"]
        group_browser = [s for s in eligible if s.group == "browser"]

        # Group 1 — Shopify API (parallel)
        if group_api:
            await self._update_progress(
                state.scan_id, 20, "Analyzing theme and apps..."
            )
        await self._run_parallel(group_api, state, timeout=120)

        # Group 2 — External (parallel)
        if group_ext:
            await self._update_progress(
                state.scan_id, 50, "Checking external signals..."
            )
        await self._run_parallel(group_ext, state, timeout=60)

        # Group 3 — Browser (sequential, Pro only)
        if group_browser:
            await self._update_progress(
                state.scan_id, 70, "Running browser tests..."
            )
        await self._run_sequential(group_browser, state, timeout=90)

        return state

    async def _run_parallel(
        self, scanners: list[BaseScanner], state: AgentState, timeout: int
    ) -> None:
        if not scanners:
            return

        async def run_one(scanner: BaseScanner) -> tuple[str, ScannerResult | None]:
            try:
                result = await asyncio.wait_for(
                    scanner.scan(state.store_id, self.shopify, state.historical_context),
                    timeout=timeout,
                )
                logger.info(
                    "scanner_completed",
                    scanner=scanner.name,
                    issues=len(result.issues),
                )
                return scanner.name, result
            except asyncio.TimeoutError:
                logger.warning("scanner_timeout", scanner=scanner.name, timeout=timeout)
                state.errors.append(f"Scanner {scanner.name} timed out after {timeout}s")
                return scanner.name, None
            except Exception as exc:
                logger.warning("scanner_failed", scanner=scanner.name, error=str(exc))
                state.errors.append(f"Scanner {scanner.name}: {exc}")
                return scanner.name, None

        results = await asyncio.gather(*[run_one(s) for s in scanners])
        for name, result in results:
            if result is not None:
                state.scanner_results[name] = result

    async def _run_sequential(
        self, scanners: list[BaseScanner], state: AgentState, timeout: int
    ) -> None:
        for scanner in scanners:
            try:
                result = await asyncio.wait_for(
                    scanner.scan(state.store_id, self.shopify, state.historical_context),
                    timeout=timeout,
                )
                state.scanner_results[scanner.name] = result
                logger.info("scanner_completed", scanner=scanner.name)
            except asyncio.TimeoutError:
                logger.warning("scanner_timeout", scanner=scanner.name, timeout=timeout)
                state.errors.append(f"Scanner {scanner.name} timed out after {timeout}s")
            except Exception as exc:
                logger.warning("scanner_failed", scanner=scanner.name, error=str(exc))
                state.errors.append(f"Scanner {scanner.name}: {exc}")

    # ------------------------------------------------------------------
    # Node 3: Analyze
    # ------------------------------------------------------------------

    async def node_analyze(self, state: AgentState) -> AgentState:
        """Interpret scanner results. Use Claude API with rules-based fallback."""
        if self.claude_analyze:
            try:
                analysis = await self._claude_analyze(state)
                state.score = analysis.get("score", 50)
                state.mobile_score = analysis.get("mobile_score", 50)
                state.desktop_score = analysis.get("desktop_score", 50)

                # Merge Claude-generated issues with scanner issues
                for issue_data in analysis.get("top_issues", []):
                    state.issues.append(ScanIssue(
                        module=issue_data.get("module", "health"),
                        scanner=issue_data.get("scanner", "claude_analysis"),
                        severity=issue_data.get("severity", "minor"),
                        title=issue_data.get("title", ""),
                        description=issue_data.get("recommendation", ""),
                        impact=issue_data.get("impact"),
                        impact_value=issue_data.get("impact_value"),
                        impact_unit=issue_data.get("impact_unit"),
                        fix_type=issue_data.get("fix_type"),
                    ))
                return state
            except Exception as exc:
                logger.warning("claude_analysis_failed", error=str(exc))
                # Fall through to rules-based

        # Rules-based fallback
        self._analyze_rules_based(state)
        return state

    def _analyze_rules_based(self, state: AgentState) -> None:
        """Calculate score and collect issues without Claude API."""
        scores: dict[str, int] = {}

        # Mobile/desktop speed from health_scorer
        if "health_scorer" in state.scanner_results:
            m = state.scanner_results["health_scorer"].metrics
            scores["mobile_speed"] = m.get("mobile_score", 50)
            scores["desktop_speed"] = m.get("desktop_score", 50)

        # App impact
        if "app_impact" in state.scanner_results:
            total_ms = state.scanner_results["app_impact"].metrics.get("total_impact_ms", 0)
            scores["app_impact"] = max(10, min(100, 100 - total_ms // 30))

        # Code quality
        code_issues = 0
        if "residue_detector" in state.scanner_results:
            code_issues += len(state.scanner_results["residue_detector"].issues)
        if "ghost_billing" in state.scanner_results:
            code_issues += len(state.scanner_results["ghost_billing"].issues)
        if "code_weight" in state.scanner_results:
            total_kb = state.scanner_results["code_weight"].metrics.get("total_js_kb", 0)
            if total_kb > 1000:
                code_issues += 2
        scores["code_quality"] = max(0, 100 - code_issues * 15)

        # SEO basics — derive from listing_analyzer issues. Each SEO-flavored
        # issue (title/description/alt/image) costs 5 points, floored at 20.
        if "listing_analyzer" in state.scanner_results:
            la = state.scanner_results["listing_analyzer"]
            seo_keywords = ("seo", "title", "description", "alt", "image")
            seo_issues = sum(
                1 for i in la.issues
                if any(k in i.title.lower() for k in seo_keywords)
            )
            scores["seo_basics"] = max(20, 100 - seo_issues * 5)
        else:
            # No listings data — neutral score, don't penalize.
            scores["seo_basics"] = 70

        # Composite — only weight categories backed by a scanner that
        # actually ran on this merchant's plan. Normalize the remaining
        # weights so we don't silently fill in 50 or 100 for missing
        # categories and inflate (or deflate) the score.
        effective_weights: dict[str, float] = {}
        if "health_scorer" in state.scanner_results:
            effective_weights["mobile_speed"] = SCORE_WEIGHTS["mobile_speed"]
            effective_weights["desktop_speed"] = SCORE_WEIGHTS["desktop_speed"]
        if "app_impact" in state.scanner_results:
            effective_weights["app_impact"] = SCORE_WEIGHTS["app_impact"]
        if any(
            s in state.scanner_results
            for s in ("residue_detector", "ghost_billing", "code_weight")
        ):
            effective_weights["code_quality"] = SCORE_WEIGHTS["code_quality"]
        if "listing_analyzer" in state.scanner_results:
            effective_weights["seo_basics"] = SCORE_WEIGHTS["seo_basics"]

        weight_sum = sum(effective_weights.values())
        if weight_sum > 0:
            normalized = {k: v / weight_sum for k, v in effective_weights.items()}
            state.score = round(
                sum(scores.get(k, 50) * w for k, w in normalized.items())
            )
        else:
            state.score = 50

        state.mobile_score = scores.get("mobile_speed", 50)
        state.desktop_score = scores.get("desktop_speed", 50)

        # Collect issues from all scanners
        for result in state.scanner_results.values():
            state.issues.extend(result.issues)

        # Sort by impact_value descending
        state.issues.sort(key=lambda i: i.impact_value or 0, reverse=True)

    async def _claude_analyze(self, state: AgentState) -> dict:
        """Call Claude API for analysis."""
        # Build scanner results summary
        results_summary = {}
        for name, result in state.scanner_results.items():
            results_summary[name] = {
                "issues_count": len(result.issues),
                "metrics": result.metrics,
                "issues": [
                    {"title": i.title, "severity": i.severity, "impact": i.impact}
                    for i in result.issues[:10]  # Cap at 10 per scanner
                ],
            }

        from app.services.claude import ANALYSIS_PROMPT

        prompt = ANALYSIS_PROMPT.format(
            store_name=state.metadata.get("store_name", "Unknown"),
            shop_domain=state.metadata.get("shop_domain", "unknown"),
            theme_name=state.metadata.get("theme_name", "Unknown"),
            apps_count=state.metadata.get("apps_count", 0),
            products_count=state.metadata.get("products_count", 0),
            shopify_plan=state.metadata.get("shopify_plan", "unknown"),
            scanner_results_json=json.dumps(results_summary, indent=2),
            merchant_memory=json.dumps(state.historical_context[:5]),
            merchant_preferences=json.dumps(state.merchant_preferences),
            cross_store_signals=json.dumps(state.cross_store_signals[:5]),
        )

        response_text = await self.claude_analyze(prompt)
        return json.loads(response_text)

    # ------------------------------------------------------------------
    # Node 4: Generate Fixes
    # ------------------------------------------------------------------

    async def node_generate_fixes(self, state: AgentState) -> AgentState:
        """Generate fix descriptions using Claude API (or skip if unavailable)."""
        if not self.claude_fix:
            return state

        # Only generate fixes for issues without fix_description
        for issue in state.issues[:5]:  # Top 5 issues only
            if issue.fix_description:
                continue
            try:
                from app.services.claude import FIX_PROMPT

                prompt = FIX_PROMPT.format(
                    issue_title=issue.title,
                    scanner=issue.scanner,
                    severity=issue.severity,
                    impact=issue.impact or "Unknown",
                    context_json=json.dumps(issue.context),
                    preferences=json.dumps(state.merchant_preferences),
                )
                response_text = await self.claude_fix(prompt)
                fix_data = json.loads(response_text)
                issue.fix_description = fix_data.get("fix_description", "")
                issue.fix_type = fix_data.get("fix_type", issue.fix_type)
                issue.auto_fixable = fix_data.get("auto_fixable", False)
            except Exception as exc:
                logger.warning(
                    "fix_generation_failed",
                    issue=issue.title,
                    error=str(exc),
                )

        return state

    # ------------------------------------------------------------------
    # Node 5: Save Results
    # ------------------------------------------------------------------

    async def node_save_results(self, state: AgentState) -> AgentState:
        """Persist scan results and issues to Supabase."""
        now = datetime.now(UTC).isoformat()

        # Update scan record
        scan_update = {
            "status": "completed",
            "score": state.score,
            "mobile_score": state.mobile_score,
            "desktop_score": state.desktop_score,
            "issues_count": len(state.issues),
            "critical_count": sum(1 for i in state.issues if i.severity == "critical"),
            "partial_scan": bool(state.errors),
            "completed_at": now,
            "scanner_results": {
                name: {"issues": len(r.issues), "metrics": r.metrics}
                for name, r in state.scanner_results.items()
            },
        }

        self.supabase.table("scans").update(scan_update).eq(
            "id", state.scan_id
        ).execute()

        # Insert scan issues
        for issue in state.issues:
            self.supabase.table("scan_issues").insert({
                "scan_id": state.scan_id,
                "store_id": state.store_id,
                "merchant_id": state.merchant_id,
                "module": issue.module,
                "scanner": issue.scanner,
                "severity": issue.severity,
                "title": issue.title,
                "description": issue.description,
                "impact": issue.impact,
                "impact_value": float(issue.impact_value) if issue.impact_value else None,
                "impact_unit": issue.impact_unit,
                "fix_type": issue.fix_type,
                "fix_description": issue.fix_description,
                "auto_fixable": issue.auto_fixable,
                "context": issue.context,
            }).execute()

        # Persist installed apps to store_apps for the dashboard.
        # Best effort — never fail the scan on a write hiccup.
        try:
            await self._persist_store_apps(state)
        except Exception as exc:  # noqa: BLE001
            logger.warning("persist_store_apps_failed", error=str(exc))

        # Sync shop metadata (name/theme/plan/etc) into stores table so
        # the dashboard has real values instead of nulls.
        try:
            self._update_store_metadata(state, now)
        except Exception as exc:  # noqa: BLE001
            logger.warning("store_metadata_update_failed", error=str(exc))

        logger.info(
            "scan_results_saved",
            scan_id=state.scan_id,
            score=state.score,
            issues=len(state.issues),
            partial=bool(state.errors),
        )

        # Update Mem0 — store baseline + cross-store signals.
        # Failures here are best-effort: the scan is already saved.
        previous_score = self._previous_score_from_history(
            state.historical_context
        )

        if self.memory:
            await self._update_memory_after_scan(state)

        # Score-drop notification (after Mem0 write so the new baseline
        # is in place for the next scan).
        if (
            previous_score is not None
            and state.score is not None
            and previous_score - state.score >= 5
        ):
            await self._notify_score_drop(state, previous_score)

        # Transactional emails (welcome on first scan, score-drop on regression).
        # Queries Supabase directly so we don't rely on Mem0 for "is this the
        # first scan?" — Mem0 might have been wiped or never wrote.
        try:
            await self._send_post_scan_emails(state)
        except Exception as exc:  # noqa: BLE001 — emails never break a scan
            logger.warning("post_scan_emails_failed", error=str(exc))

        return state

    def _update_store_metadata(self, state: AgentState, now: str) -> None:
        """Pull what the health_scorer learned about the shop into the
        stores row so the dashboard has real data instead of nulls."""
        hs = state.scanner_results.get("health_scorer")
        if not hs:
            return
        m = hs.metrics
        update: dict = {}
        if m.get("shop_name"):
            update["name"] = m["shop_name"]
        if m.get("primary_domain"):
            update["primary_domain"] = m["primary_domain"]
        if m.get("currency"):
            update["currency"] = m["currency"]
        if m.get("country"):
            update["country"] = m["country"]
        if m.get("theme_name") and m["theme_name"] != "Unknown":
            update["theme_name"] = m["theme_name"]
        if m.get("products_count") is not None:
            update["products_count"] = m["products_count"]
        if m.get("apps_count_known", True) and m.get("apps_count") is not None:
            update["apps_count"] = m["apps_count"]
        if m.get("shopify_plan"):
            update["shopify_plan"] = m["shopify_plan"]
        if not update:
            return
        update["last_scanned_at"] = now
        self.supabase.table("stores").update(update).eq(
            "id", state.store_id
        ).execute()
        logger.info(
            "store_metadata_updated",
            store_id=state.store_id,
            fields=list(update.keys()),
        )

    async def _persist_store_apps(self, state: AgentState) -> None:
        """Refresh the store_apps table from the latest scan signals.

        Uses health_scorer.metrics["apps"] for identity (always present
        when the read_apps scope is granted) and optionally enriches each
        row with app_impact.metrics["app_impacts"] (Starter+) for
        scripts_count + impact_ms. Falls back to a flat 300ms estimate
        per app when app_impact didn't run.
        """
        hs_result = state.scanner_results.get("health_scorer")
        if not hs_result:
            return
        apps = hs_result.metrics.get("apps") or []
        if not apps:
            return

        ai_result = state.scanner_results.get("app_impact")
        impact_by_handle: dict[str, dict] = {}
        if ai_result:
            for item in ai_result.metrics.get("app_impacts") or []:
                handle = (item.get("app_handle") or "").lower()
                if handle:
                    impact_by_handle[handle] = item

        rows = []
        for app in apps:
            handle = (app.get("handle") or "").lower()
            ai = impact_by_handle.get(handle)
            rows.append({
                "store_id": state.store_id,
                "merchant_id": state.merchant_id,
                "shopify_app_id": app.get("shopify_app_id"),
                "name": app.get("name") or "Unknown app",
                "handle": app.get("handle"),
                "developer": app.get("developer"),
                "scopes": app.get("scopes") or [],
                "scripts_count": (ai or {}).get("scripts_count", 0),
                "impact_ms": (ai or {}).get("estimated_impact_ms", 300),
                "status": "active",
            })

        # Replace the existing snapshot for this store. Service-role key
        # bypasses RLS, so the merchant filter on delete is just defense
        # in depth.
        self.supabase.table("store_apps").delete().eq(
            "store_id", state.store_id
        ).eq("merchant_id", state.merchant_id).execute()

        if rows:
            self.supabase.table("store_apps").insert(rows).execute()

        logger.info(
            "store_apps_persisted",
            store_id=state.store_id,
            count=len(rows),
            with_impact=sum(1 for r in rows if r["scripts_count"] > 0),
        )

    @staticmethod
    def _previous_score_from_history(memories: list[dict]) -> int | None:
        """Find the most recent stored Score: N in the merchant/store memory."""
        import re as _re

        pattern = _re.compile(r"Score:\s*(\d+)")
        for mem in memories:
            text = str(mem.get("memory") or mem.get("content") or "")
            match = pattern.search(text)
            if match:
                return int(match.group(1))
        return None

    async def _notify_score_drop(
        self, state: AgentState, previous_score: int
    ) -> None:
        try:
            from app.services.notification import (
                format_score_drop_notification,
                send_notification,
            )

            cause = "recent app or theme change"
            for issue in state.issues:
                if issue.severity == "critical":
                    cause = issue.title
                    break

            payload = format_score_drop_notification(
                previous_score=previous_score,
                current_score=state.score or 0,
                probable_cause=cause,
            )

            await send_notification(
                merchant_id=state.merchant_id,
                store_id=state.store_id,
                channel="push",
                supabase=self.supabase,
                **payload,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("score_drop_notification_failed", error=str(exc))

    async def _send_post_scan_emails(self, state: AgentState) -> None:
        """Welcome on first completed scan + score-drop alert on ≥5 regression.

        Best-effort — if anything fails (missing email, Resend down, query
        glitch) we just log and move on.
        """
        from app.services import email_service

        if state.score is None:
            return

        merchant_res = (
            self.supabase.table("merchants")
            .select("email,notification_email,shopify_shop_domain")
            .eq("id", state.merchant_id)
            .single()
            .execute()
        )
        merchant = getattr(merchant_res, "data", None)
        if not merchant:
            return

        # Prefer the merchant-configured notification address, fall back to
        # the Supabase auth email. Skip the placeholder @storemd.app addresses
        # we mint during OAuth — they don't route anywhere.
        recipient = merchant.get("notification_email") or merchant.get("email")
        if not recipient or recipient.endswith("@storemd.app"):
            return

        shop_domain = merchant.get("shopify_shop_domain") or "your store"

        # Count completed scans (excluding this one) to detect first scan.
        prior = (
            self.supabase.table("scans")
            .select("id,score", count="exact")
            .eq("store_id", state.store_id)
            .eq("status", "completed")
            .neq("id", state.scan_id)
            .order("completed_at", desc=True)
            .limit(1)
            .execute()
        )
        prior_count = getattr(prior, "count", None)
        prior_rows = prior.data or []
        prior_score = prior_rows[0].get("score") if prior_rows else None

        if prior_count == 0:
            email_service.send_welcome_email(
                merchant_email=recipient,
                shop_domain=shop_domain,
                score=state.score,
            )
            return

        if (
            prior_score is not None
            and prior_score - state.score >= 5
        ):
            email_service.send_score_drop_alert(
                merchant_email=recipient,
                shop_domain=shop_domain,
                old_score=prior_score,
                new_score=state.score,
                issues_count=len(state.issues),
            )

    async def _update_memory_after_scan(self, state: AgentState) -> None:
        """Write the new baseline + cross-store signals to Mem0."""
        try:
            critical_count = sum(
                1 for i in state.issues if i.severity == "critical"
            )
            modules = ", ".join(state.modules) if state.modules else "health"
            now = datetime.now(UTC).isoformat()
            baseline = (
                f"Scan {state.scan_id} completed. "
                f"Score: {state.score} "
                f"(mobile: {state.mobile_score}, desktop: {state.desktop_score}). "
                f"Issues: {len(state.issues)} ({critical_count} critical). "
                f"Modules: {modules}. "
                f"Date: {now}."
            )
            await self.memory.remember_store(state.store_id, baseline)
        except Exception as exc:  # noqa: BLE001
            logger.warning("memory_remember_store_failed", error=str(exc))

        # Cross-store: signal apps that caused critical issues.
        for issue in state.issues:
            if issue.scanner != "app_impact" or issue.severity != "critical":
                continue
            try:
                app_name = issue.context.get("app_title") or issue.context.get(
                    "app_name", "unknown"
                )
                signal = (
                    f"App '{app_name}' caused critical issue on store "
                    f"{state.store_id}: {issue.title}. "
                    f"Impact: {issue.impact or 'unknown'}."
                )
                await self.memory.signal_cross_store(signal)
            except Exception as exc:  # noqa: BLE001
                logger.warning("memory_cross_store_signal_failed", error=str(exc))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _get_merchant_plan(self, merchant_id: str) -> str:
        """Get the merchant's current plan."""
        result = (
            self.supabase.table("merchants")
            .select("plan")
            .eq("id", merchant_id)
            .single()
            .execute()
        )
        return result.data.get("plan", "free") if result.data else "free"
