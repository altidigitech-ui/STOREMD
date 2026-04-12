# CHANGELOG.md — Historique des versions StoreMD

> **Mis à jour à chaque deploy. Format Keep a Changelog.**
> **Chaque entrée : date, version, ce qui a changé (Added, Changed, Fixed, Removed).**

---

## FORMAT

```
## [X.Y.Z] — YYYY-MM-DD

### Added
- Nouvelles features

### Changed
- Modifications de features existantes

### Fixed
- Bugs corrigés

### Removed
- Features supprimées

### Security
- Fixes de sécurité

### Infrastructure
- Changements deploy, DB migrations, scaling
```

### Versioning

```
MAJOR (X) : Breaking changes API, refonte UI majeure
MINOR (Y) : Nouvelles features, nouveaux scanners
PATCH (Z) : Bug fixes, améliorations mineures
```

MVP launch = `1.0.0`. Chaque deploy incrémente le patch. Chaque nouveau scanner/feature incrémente le minor.

---

## VERSIONS

## [1.0.0] — 2026-04-12 — MVP Launch

Six implementation phases brought StoreMD from an empty repo to a
production-ready Shopify app: 19 scanners, 16 API routers, full Mem0
agent loop, browser automation, and a complete Next.js dashboard.

### Phase 1 — Fondations
- `CLAUDE.md`, `context.md`, 16 doc files in `docs/`
- 13 skill modules in `.claude/skills/`
- 5 slash commands, 2 sub-agents
- Repo structure (backend / frontend / database / docs)

### Phase 2 — Backend core (FastAPI + scanners)

#### Added
- FastAPI app with global `AppError` handler, structlog logging, Sentry init
- Pydantic `BaseSettings` config (`app/config.py`)
- DI: Supabase clients, Redis, JWT auth (`app/dependencies.py`)
- `BaseScanner` ABC + `ScannerRegistry`
- `LangGraph`-style `ScanOrchestrator` (5 nodes: load_memory →
  run_scanners → analyze → generate_fixes → save_results)
- 8 health scanners: `health_scorer`, `app_impact`, `residue_detector`,
  `ghost_billing`, `code_weight`, `security_monitor`, `pixel_health`
- 1 listings scanner: `listing_analyzer`
- Claude API service with rules-based fallback
- Fernet-encrypted Shopify token storage
- HMAC webhook validation (Shopify + Stripe)

### Phase 3 — Billing, webhooks, listings, fixes

#### Added
- Stripe checkout + customer portal + 5 webhook events
- Shopify webhooks (`app/uninstalled`, `products/*`, `themes/*`)
- One-Click Fix engine (apply / revert with `before_state` snapshot)
- Notifications API (list + mark read)

### Phase 4 — Frontend Next.js + PWA

#### Added
- Next.js 14 (App Router, TypeScript strict)
- Typed API client (`api.stores`, `api.scans`, `api.billing`,
  `api.notifications`, `api.feedback`, `api.fixes`)
- Dashboard shell (Health / Listings / AI Ready / Browser / Settings)
- Onboarding flow (auto-scan, score reveal, monitoring setup)
- SSR landing page + 4-tier pricing with Stripe checkout
- PWA: manifest, service worker, push + install + offline hooks
- 11 vitest unit tests (ScoreHero, IssueCard, useHealth)

### Phase 5 — Mem0, Ouroboros, agentic + compliance + benchmark

#### Added
- `StoreMemory` (Mem0 wrapper, hosted/self-hosted, graceful degradation)
- `OuroborosLearner` — feedback loop + pattern analysis
- 5 scanners: `agentic_readiness`, `hs_code_validator`, `broken_links`,
  `accessibility`, `bot_traffic`, `benchmark`
- Notification service (push + email + in-app, anti-spam 3/week)
- Weekly report generator + Celery beat (Sunday 09:00 UTC)
- Routes: `listings.py`, `agentic.py`, `compliance.py`
- GDPR `forget_merchant` on uninstall
- 22 new pytest tests

### Phase 6 — Browser Playwright + finitions (this release)

#### Added
- `BaseBrowserScanner` — Playwright lifecycle (Chromium headless,
  container-friendly args, mobile/desktop viewports)
- 3 browser scanners: `visual_store_test` (screenshot diff with Pillow),
  `real_user_simulation` (5-step purchase path timing),
  `accessibility_live` (axe-core injection + manual heuristics)
- `trend_analyzer` (declining streak detection)
- `content_theft` placeholder (Phase 2 stub)
- `tasks/browser_tasks.py` — dedicated Celery task with 90s/scanner
  + 5min total timeout, sequential execution
- `tasks/cross_store_tasks.py` — daily 5 AM UTC fleet-wide app
  regression detection
- `routes/browser.py` (visual diff, simulation), `routes/reports.py`,
  `routes/debug.py` (dev/staging only)
- Frontend: complete Browser page (screenshots, simulation timeline,
  axe violations) + new Reports page
- TypeScript types + api client extensions for browser/reports
- 16 new pytest tests (BaseBrowserScanner, VisualStoreTest,
  RealUserSimulation, TrendAnalyzer, ContentTheftScanner)

### Infrastructure
- 75 Python modules across `backend/app` + `backend/tasks`
- 50 TS/TSX files across `frontend/src`
- 19 scanners registered (`health: 11, listings: 1, agentic: 2,
  compliance: 2, browser: 3`)
- 16 API routers (15 always-on + `debug` in dev/staging only)
- Beat schedule: 5 cron jobs (Pro daily 03:00, Starter weekly Mon 04:00,
  Agency daily 03:15, weekly reports Sun 09:00, cross-store analysis 05:00)
- 99 backend pytest unit tests passing
- 11 frontend vitest tests passing
- Frontend `npm run build` produces 13 static routes
- `Dockerfile` (API) and `Dockerfile.worker` (Playwright Chromium) ready

---

## [Unreleased]

*Future deploys will be appended above this section.*
