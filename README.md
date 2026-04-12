# StoreMD

**AI agent that monitors Shopify store health 24/7.**

StoreMD scans your store's speed, apps, code, listings, and AI readiness — then fixes issues in 1 click. Not a passive tool. An agent that detects, analyzes, acts, and learns.

---

## What it does

StoreMD is a Shopify app (embedded, OAuth) with 5 modules and 43 features:

| Module | Features | What it covers |
|--------|----------|---------------|
| **Store Health** | 20 | Speed score, app impact, bot filter, ghost billing, code residue, security |
| **Listings** | 14 | Product score, SEO, alt text, dead listings, bulk operations |
| **Agentic Readiness** | 4 | ChatGPT/Copilot/Gemini compatibility, GTIN, metafields, HS codes |
| **Compliance & Fixes** | 3 | WCAG accessibility (EAA), broken links, one-click fix engine |
| **Browser Automation** | 2 | Visual diff (Playwright screenshots), real user simulation (purchase path timing) |

### How it works

```
1. DETECT   — Webhooks, cron scans, manual triggers
2. ANALYZE  — Scanners + Claude API + Mem0 memory (personalized context)
3. ACT      — Push notifications + 1-click fixes via Shopify API
4. LEARN    — Merchant feedback → Mem0 → each scan gets smarter (Ouroboros)
```

### Pricing

| Plan | Price | Stores | Scans | Listings |
|------|-------|--------|-------|----------|
| Free | $0 | 1 | 3/month | 5 products |
| Starter | $39/mo | 1 | Weekly | 100 products |
| Pro | $99/mo | 3 | Daily | 1,000 + browser tests |
| Agency | $249/mo | 10 | Daily | Unlimited + API + white-label |

---

## Tech stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.12+, FastAPI, Celery, Redis |
| Agent | LangGraph, Claude API (Anthropic), Mem0 |
| Browser | Playwright (Chromium headless) |
| Frontend | Next.js 14, TypeScript, Tailwind, shadcn/ui |
| Database | Supabase PostgreSQL + RLS + pgvector |
| Deploy | Railway (backend + worker) + Vercel (frontend) |
| Payments | Stripe (Checkout, Portal, Webhooks) |
| Monitoring | Sentry, LangSmith, structlog |

---

## Repo structure

```
altidigitech-ui/
├── CLAUDE.md                    # Claude Code instructions (loaded every session)
├── context.md                   # Business vision, features, personas, pricing
├── README.md                    # This file
│
├── backend/                     # 75 Python modules
│   ├── app/
│   │   ├── main.py              # FastAPI app — mounts 15 routers (16 in dev/staging)
│   │   ├── config.py            # Pydantic BaseSettings (env vars)
│   │   ├── dependencies.py      # DI (Depends)
│   │   ├── api/routes/          # auth, scans, stores, billing, fixes, listings,
│   │   │                        # agentic, compliance, browser, reports, feedback,
│   │   │                        # notifications, health, webhooks_*, debug (dev only)
│   │   ├── agent/
│   │   │   ├── orchestrator.py  # 5-node pipeline (load_memory → run → analyze → fix → save)
│   │   │   ├── memory.py        # StoreMemory (Mem0 wrapper, 4 layers)
│   │   │   ├── learner.py       # Ouroboros feedback loop + pattern analysis
│   │   │   ├── analyzers/       # 16 scanners + base.py
│   │   │   └── browser/         # 3 Playwright scanners + base.py
│   │   ├── services/            # Shopify, Stripe, Supabase, claude, notification,
│   │   │                        # report_generator, webhook_registration
│   │   ├── models/              # Pydantic models + schemas
│   │   └── core/                # Exceptions, security, logging
│   ├── tasks/                   # celery_app, scan_tasks, browser_tasks,
│   │                            # report_tasks, cross_store_tasks
│   ├── tests/                   # pytest — 99 unit tests passing
│   ├── Dockerfile               # API service (Python 3.12-slim + uvicorn)
│   └── Dockerfile.worker        # Celery worker + Chromium for Playwright
│
├── frontend/                    # 50 TS/TSX files, 13 static routes built
│   ├── src/
│   │   ├── app/                 # Next.js App Router (dashboard, onboarding,
│   │   │                        # pricing, reports, browser)
│   │   ├── components/          # ui/ + dashboard/ + landing/ + onboarding/ +
│   │   │                        # layout/ + scan/ + shared/
│   │   ├── hooks/               # use-scan, use-store, use-health,
│   │   │                        # use-push-notifications, use-install-prompt, etc.
│   │   ├── lib/                 # API client (typed namespaces), Supabase, utils
│   │   └── types/               # TypeScript types — full backend schema mirrored
│   ├── public/                  # PWA manifest, service worker, icons
│   └── tests/                   # vitest — 11 unit tests passing
│
├── database/
│   ├── schema.sql               # Full schema (generated from docs/DATABASE.md)
│   └── migrations/              # Numbered SQL migrations
│
├── docs/                        # Technical documentation (16 files)
│   ├── FEATURES.md              # 43 features spec (plan, scanner, endpoint, component)
│   ├── ARCH.md                  # Architecture (layers, LangGraph, scan pipeline)
│   ├── DATABASE.md              # Full PostgreSQL schema + RLS + triggers
│   ├── API.md                   # REST API reference (30 endpoints)
│   ├── SHOPIFY.md               # OAuth, GraphQL, webhooks, scopes
│   ├── AGENT.md                 # Agent 4 layers, Claude prompts, Ouroboros
│   ├── SECURITY.md              # Fernet, HMAC, JWT, RLS, CORS, OWASP
│   ├── ERRORS.md                # 58 error codes + handlers + frontend mapping
│   ├── UI.md                    # Design system, colors, components, layout
│   ├── PWA.md                   # Service worker, push, install prompt, offline
│   ├── COPY.md                  # All app copy in English
│   ├── ONBOARDING.md            # 6-step user journey with metrics
│   ├── DEPLOY.md                # Railway + Vercel + Supabase setup
│   ├── TESTS.md                 # pytest + vitest + Playwright strategy
│   ├── MONITORING.md            # Sentry, structlog, LangSmith, business metrics
│   └── CHANGELOG.md             # Version history
│
└── .claude/                     # Claude Code configuration
    ├── settings.json            # Hooks, permissions, rules
    ├── skills/                  # 13 skill files (patterns + code examples)
    │   ├── shopify-api/         # Shopify OAuth, GraphQL, webhooks, rate limits
    │   ├── agent-loop/          # LangGraph pipeline, 4 layers, Ouroboros
    │   ├── scan-pipeline/       # Scanner groups, parallelism, BaseScanner
    │   ├── feature-impl/        # End-to-end feature checklist (DB→scanner→API→UI→tests)
    │   ├── saas-debug-pipeline/ # Debug across the full stack
    │   ├── mem0-integration/    # Memory types, recall, learn, GDPR cleanup
    │   ├── browser-automation/  # Playwright visual test, simulation, a11y
    │   ├── agentic-readiness/   # ChatGPT Shopping compatibility scanner
    │   ├── supabase-patterns/   # RLS, queries, migrations, storage
    │   ├── stripe-billing/      # Checkout, portal, webhooks, usage metering
    │   ├── playwright-testing/  # E2E tests for our app (not merchant stores)
    │   ├── systematic-debugging/# 5-step debug method
    │   └── owasp-security/      # OWASP Top 10 applied to our stack
    ├── commands/                # 5 slash commands
    │   ├── deploy.md            # /deploy — Railway + Vercel + post-checks
    │   ├── full-test.md         # /full-test — pytest + vitest + lint + security
    │   ├── add-scanner.md       # /add-scanner — wizard to create a new scanner
    │   ├── db-migrate.md        # /db-migrate — apply SQL migration safely
    │   └── scan-debug.md        # /scan-debug — diagnose a failed scan
    └── agents/                  # 2 sub-agents
        ├── qa-agent.md          # Code review before commit
        └── scanner-agent.md     # Expert scanner writer
```

---

## Getting started

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker (for local Redis)
- Supabase account
- Shopify Partner account
- Stripe account
- Anthropic API key

### Local development

```bash
# 1. Clone
git clone https://github.com/altidigitech-ui/altidigitech-ui.git
cd altidigitech-ui

# 2. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # Fill in your keys
uvicorn app.main:app --reload --port 8000

# 3. Celery worker (separate terminal)
celery -A tasks.celery_app worker --beat --loglevel=info

# 4. Redis
docker run -d -p 6379:6379 redis:7

# 5. Frontend
cd frontend
npm install
cp .env.local.example .env.local    # Fill in NEXT_PUBLIC_ vars
npm run dev    # http://localhost:3000

# 6. Database
# Apply database/migrations/001_initial.sql in Supabase SQL Editor
# Run: NOTIFY pgrst, 'reload schema';
```

### Deploy to production

See `docs/DEPLOY.md` for the complete guide. Summary:

1. **Supabase** — Create project, apply migrations, create storage buckets
2. **Stripe** — Create products (Starter/Pro/Agency), configure webhooks
3. **Shopify Partner** — Create app, set OAuth URLs
4. **Railway** — Create project with 2 services (api + worker) + Redis add-on
5. **Vercel** — Import repo, set root to `frontend/`, configure env vars
6. **DNS** — Point `storemd.com` → Vercel, `api.storemd.com` → Railway

---

## Documentation

All documentation is in `docs/` and `.claude/skills/`. Start with:

1. `CLAUDE.md` — Stack, structure, patterns, rules
2. `context.md` — Business vision, features, pricing
3. `docs/FEATURES.md` — All 43 features with specs
4. `docs/ARCH.md` — System architecture

For Claude Code users: CLAUDE.md is loaded automatically. Skills are loaded on demand when working in a specific domain.

---

## Key design decisions

**Why not shopify-python-api?** — Deprecated, thread-safety issues. We use `httpx` directly for all Shopify API calls.

**Why Mem0 for memory?** — The DB stores facts (scan results). Mem0 stores intelligence (merchant preferences, patterns, cross-store signals). This enables personalized recommendations that improve with every scan.

**Why LangGraph?** — The scan pipeline is a stateful graph, not a linear script. LangGraph manages the flow: detect → load memory → run scanners → analyze → generate fixes → notify → save. Conditional edges (should we notify?) and graceful degradation (scanner fails → continue) are built into the graph.

**Why Playwright in production?** — The Shopify API gives us data. Playwright gives us reality. A PageSpeed score of 72 doesn't tell you that a popup blocks the product page for 6 seconds. Real User Simulation does.

**Why one app, not five?** — StoreMD tells merchants "you have too many apps." Selling 5 separate apps would be hypocritical. One app, 5 modules, one install.

---

## World exclusives

Four features no competitor has:

1. **Agentic Readiness Scanner** — "Your store is 34% ready for ChatGPT Shopping"
2. **Visual Store Test** — Playwright screenshot diff between scans with cause correlation
3. **Real User Simulation** — Full purchase path timed with bottleneck identification
4. **Accessibility Live Test** — WCAG verified in real browser rendering, not static HTML

---

## License

Proprietary. All rights reserved.

---

## Built by

**FoundryTwo** — Alti (strategy), Fabrice (build), Romain (distribution).
