# CLAUDE.md — StoreMD

> **Ce fichier est chargé automatiquement à chaque session Claude Code.**
> **Lis-le EN ENTIER avant de toucher au code.**

---

## PROJET

StoreMD — Agent IA qui diagnostique la santé complète des stores Shopify.
43 features, 5 modules : Store Health, Listings, Agentic Readiness, Compliance & Fixes, Browser Automation.
App Shopify (OAuth, embedded) + PWA. Pricing : Free → Starter $39 → Pro $99 → Agency $249.

Repo GitHub : `altidigitech-ui`. Standalone, pas de monorepo, pas de shared kernel.

---

## STACK TECHNIQUE

### Backend
- **Python 3.12+** — FastAPI (async, Pydantic v2)
- **Celery** + **Redis** — background jobs (scans, browser automation, reports)
- **LangGraph** — orchestration agent 4 couches (DETECT → ANALYZE → ACT → LEARN)
- **Claude API** (Anthropic) — LLM primaire pour l'analyse
- **Mem0** — mémoire persistante agent (merchant, store, cross-store, agent memory)
- **Playwright** — browser automation (Visual Store Test, Real User Simulation, Accessibility Live Test)
- **httpx** — HTTP client async (Shopify API, services externes)
- **Deploy : Railway** (backend API + Celery worker, services séparés)

### Frontend
- **Next.js 14** — App Router, TypeScript strict, SSR pour SEO landing page
- **Tailwind CSS** + **shadcn/ui** — design system
- **Shopify App Bridge** — embedded app dans le Shopify Admin
- **Shopify Polaris** — guidelines UI pour la cohérence Shopify
- **PWA** — service worker, manifest.json, push notifications (web-push)
- **Deploy : Vercel**

### Database
- **Supabase PostgreSQL** — tables métier + auth + billing + agent
- **RLS (Row Level Security)** — OBLIGATOIRE sur chaque table
- **pgvector** — stockage Mem0 (si self-hosted)

### Services externes
- **Shopify Admin API** — GraphQL (version 2025-04+)
- **Stripe** — Checkout, Customer Portal, Webhooks (4 plans)
- **Resend** — emails transactionnels
- **Sentry** — error tracking
- **LangSmith** — LLM tracing + cost tracking

---

## STRUCTURE DU PROJET

```
altidigitech-ui/                       # Racine du repo GitHub
├── CLAUDE.md                          # CE FICHIER
├── context.md                         # Vision business, features, personas, pricing
│
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app, startup, middleware, CORS
│   │   ├── config.py                  # Settings Pydantic BaseSettings (env vars)
│   │   ├── dependencies.py            # Injection de dépendances (DI)
│   │   │
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── auth.py            # Shopify OAuth install/callback + session
│   │   │   │   ├── scans.py           # CRUD scans, trigger scan, scan results
│   │   │   │   ├── stores.py          # Store info, settings, apps list
│   │   │   │   ├── listings.py        # Product analyses, catalogue scan
│   │   │   │   ├── agentic.py         # Agentic readiness score, fixes, HS codes
│   │   │   │   ├── compliance.py      # Accessibility, broken links
│   │   │   │   ├── browser.py         # Visual test, user simulation
│   │   │   │   ├── fixes.py           # One-click fix apply/revert
│   │   │   │   ├── billing.py         # Stripe checkout, portal
│   │   │   │   ├── notifications.py   # Notification preferences, list
│   │   │   │   ├── reports.py         # Weekly reports, export
│   │   │   │   ├── feedback.py        # Ouroboros feedback accept/reject
│   │   │   │   ├── webhooks_shopify.py # Shopify webhooks receiver
│   │   │   │   ├── webhooks_stripe.py  # Stripe webhooks receiver
│   │   │   │   └── health.py          # Healthcheck endpoint
│   │   │   └── middleware/
│   │   │       ├── auth.py            # JWT validation Supabase
│   │   │       ├── rate_limit.py      # Rate limiting Redis
│   │   │       └── hmac.py            # HMAC validation Shopify webhooks
│   │   │
│   │   ├── agent/
│   │   │   ├── orchestrator.py        # LangGraph state machine
│   │   │   ├── state.py               # AgentState dataclass
│   │   │   ├── memory.py              # StoreMemory — Mem0 client wrapper
│   │   │   ├── learner.py             # Ouroboros feedback loop
│   │   │   │
│   │   │   ├── detectors/
│   │   │   │   ├── webhook_handler.py # Shopify events → trigger scan
│   │   │   │   ├── cron_scanner.py    # Scans planifiés (nightly, weekly)
│   │   │   │   └── realtime_monitor.py # App updates, permission changes
│   │   │   │
│   │   │   ├── analyzers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py            # BaseScanner ABC
│   │   │   │   ├── health_scorer.py   # Score /100 composite + diagnostic 3 couches
│   │   │   │   ├── app_impact.py      # Impact chaque app sur le load time
│   │   │   │   ├── bot_traffic.py     # Bot filter + AI crawler monitor
│   │   │   │   ├── residue_detector.py # Code mort d'apps désinstallées
│   │   │   │   ├── ghost_billing.py   # Apps désinstallées qui facturent encore
│   │   │   │   ├── code_weight.py     # Poids JS/CSS par source
│   │   │   │   ├── security_monitor.py # SSL, headers, permissions apps
│   │   │   │   ├── pixel_health.py    # GA4, Meta Pixel, TikTok Pixel
│   │   │   │   ├── email_health.py    # SPF, DKIM, DMARC
│   │   │   │   ├── broken_links.py    # Liens cassés internes + externes
│   │   │   │   ├── listing_analyzer.py # Score /100 par listing produit
│   │   │   │   ├── agentic_readiness.py # Compatibilité ChatGPT/Copilot/Gemini
│   │   │   │   ├── hs_code_validator.py # Validation HS codes produits
│   │   │   │   ├── accessibility.py   # WCAG 2.1 scan statique
│   │   │   │   ├── benchmark.py       # Benchmark vs stores similaires
│   │   │   │   ├── content_theft.py   # Détection copie contenu (Phase 2)
│   │   │   │   └── trend_analyzer.py  # Tendances inter-scans (background)
│   │   │   │
│   │   │   ├── actors/
│   │   │   │   ├── notification.py    # Push + email + in-app
│   │   │   │   ├── fix_generator.py   # Claude API → recommandations langage simple
│   │   │   │   ├── one_click_fixer.py # Appliquer fix via Shopify API write
│   │   │   │   └── report_generator.py # Weekly report HTML + PDF
│   │   │   │
│   │   │   └── browser/
│   │   │       ├── visual_store_test.py      # Screenshots + diff visuel
│   │   │       ├── real_user_simulation.py   # Parcours achat Homepage→Checkout
│   │   │       └── accessibility_live.py     # WCAG rendu réel Playwright
│   │   │
│   │   ├── services/
│   │   │   ├── shopify.py             # Shopify GraphQL client + rate limit + retry
│   │   │   ├── stripe_billing.py      # Stripe Checkout, Portal, Webhooks
│   │   │   ├── supabase.py            # Supabase client + helpers
│   │   │   ├── email.py               # Resend email service
│   │   │   └── push.py                # Web-push notifications
│   │   │
│   │   ├── models/
│   │   │   ├── scan.py                # ScanResult, ScanIssue, ScanStatus
│   │   │   ├── store.py               # Store, StoreApp
│   │   │   ├── merchant.py            # Merchant, Subscription
│   │   │   ├── product.py             # ProductAnalysis, AgenticCheck
│   │   │   ├── fix.py                 # Fix, FixStatus
│   │   │   └── schemas.py             # Pydantic request/response schemas
│   │   │
│   │   └── core/
│   │       ├── exceptions.py          # AppError hierarchy + ErrorCode enum
│   │       ├── security.py            # Fernet encrypt/decrypt, HMAC, JWT helpers
│   │       └── logging.py             # structlog config
│   │
│   ├── tasks/
│   │   ├── celery_app.py              # Celery config + beat schedule
│   │   ├── scan_tasks.py              # Celery tasks scans
│   │   ├── browser_tasks.py           # Celery tasks Playwright
│   │   └── report_tasks.py            # Celery tasks reports
│   │
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_scans.py
│   │   ├── test_shopify.py
│   │   ├── test_billing.py
│   │   ├── test_analyzers/
│   │   │   ├── test_health_scorer.py
│   │   │   ├── test_app_impact.py
│   │   │   └── ...
│   │   └── mocks/
│   │       ├── shopify_responses.py
│   │       └── claude_responses.py
│   │
│   ├── pyproject.toml
│   ├── Dockerfile                     # API service
│   ├── Dockerfile.worker              # Celery worker service
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── app/                       # Next.js App Router
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx               # Landing page (SSR, SEO)
│   │   │   ├── dashboard/
│   │   │   │   ├── layout.tsx         # Dashboard layout avec navigation onglets
│   │   │   │   ├── page.tsx           # Redirect vers /dashboard/health
│   │   │   │   ├── health/
│   │   │   │   │   └── page.tsx       # Onglet Store Health
│   │   │   │   ├── listings/
│   │   │   │   │   └── page.tsx       # Onglet Listings
│   │   │   │   ├── agentic/
│   │   │   │   │   └── page.tsx       # Onglet AI Ready (Agentic + Compliance)
│   │   │   │   ├── browser/
│   │   │   │   │   └── page.tsx       # Onglet Browser Tests (Pro only)
│   │   │   │   └── settings/
│   │   │   │       └── page.tsx       # Settings (alerts, notifications, plan)
│   │   │   ├── onboarding/
│   │   │   │   └── page.tsx           # Premier scan + activation monitoring
│   │   │   └── pricing/
│   │   │       └── page.tsx           # Plans + upgrade
│   │   │
│   │   ├── components/
│   │   │   ├── ui/                    # shadcn/ui components
│   │   │   ├── dashboard/             # ScoreCard, IssueList, TrendChart
│   │   │   ├── scan/                  # ScanProgress, ScanResult
│   │   │   └── shared/               # OneClickFix, FixSuggestion, ErrorState
│   │   │
│   │   ├── lib/
│   │   │   ├── api.ts                 # API client typed (fetch wrapper)
│   │   │   ├── supabase.ts            # Supabase browser client
│   │   │   └── utils.ts
│   │   │
│   │   ├── hooks/
│   │   │   ├── use-scan.ts
│   │   │   ├── use-store.ts
│   │   │   └── use-subscription.ts
│   │   │
│   │   └── types/
│   │       ├── scan.ts
│   │       ├── store.ts
│   │       └── api.ts
│   │
│   ├── public/
│   │   ├── manifest.json             # PWA manifest
│   │   ├── sw.js                     # Service worker
│   │   └── icons/
│   │
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── package.json
│
├── database/
│   ├── schema.sql                     # Schéma complet (source de vérité = docs/DATABASE.md)
│   └── migrations/
│       └── 001_initial.sql
│
├── docs/                              # Documentation technique détaillée
└── .claude/                           # Skills, commands, agents Claude Code
```

---

## PATTERNS OBLIGATOIRES

### Python — Backend

```python
# 1. TOUJOURS Pydantic v2 pour la validation
from pydantic import BaseModel, Field

class ScanRequest(BaseModel):
    store_id: str = Field(..., min_length=1)
    modules: list[str] = Field(default=["health"])

# 2. TOUJOURS l'injection de dépendances FastAPI
from app.dependencies import get_supabase, get_shopify_client

@router.post("/scans")
async def create_scan(
    request: ScanRequest,
    supabase: SupabaseClient = Depends(get_supabase),
    shopify: ShopifyClient = Depends(get_shopify_client),
):
    ...

# 3. TOUJOURS AppError, JAMAIS HTTPException directement
from app.core.exceptions import AppError, ErrorCode

raise AppError(
    code=ErrorCode.SCAN_FAILED,
    message="Scan failed: Shopify API timeout",
    status_code=502,
    context={"store_id": store_id, "timeout_ms": 30000},
)

# 4. TOUJOURS structlog, JAMAIS print() ou logging.info()
import structlog
logger = structlog.get_logger()
logger.info("scan_started", store_id=store_id, modules=modules)

# 5. TOUJOURS typer les retours
async def get_store(store_id: str) -> Store | None:
    ...

# 6. TOUJOURS async pour les I/O
async def fetch_products(shop_domain: str) -> list[Product]:
    ...

# 7. TOUJOURS httpx (async), JAMAIS requests (sync)
async with httpx.AsyncClient() as client:
    response = await client.get(url, headers=headers)
```

### TypeScript — Frontend

```typescript
// 1. JAMAIS de `any`. Utiliser `unknown` ou type explicite.
// ❌ const data: any = await response.json()
// ✅ const data = await response.json() as ScanResult

// 2. TOUJOURS typer les props
interface ScoreCardProps {
  score: number;
  trend: "up" | "down" | "stable";
  label: string;
}
export function ScoreCard({ score, trend, label }: ScoreCardProps) { ... }

// 3. TOUJOURS le API client centralisé
import { api } from "@/lib/api";
const scan = await api.scans.create({ storeId, modules: ["health"] });

// 4. TOUJOURS gérer loading/error
const { data, isLoading, error } = useScan(scanId);
if (isLoading) return <Skeleton />;
if (error) return <ErrorState message={error.message} />;
```

### Supabase

```sql
-- TOUJOURS RLS sur chaque table
ALTER TABLE scans ENABLE ROW LEVEL SECURITY;
CREATE POLICY "merchants_own_scans" ON scans
    FOR ALL USING (merchant_id = auth.uid());

-- TOUJOURS NOTIFY après changement de schéma
NOTIFY pgrst, 'reload schema';

-- TOUJOURS indexer les colonnes de filtrage fréquent
CREATE INDEX idx_scans_store_id ON scans(store_id);
CREATE INDEX idx_scans_created_at ON scans(created_at DESC);
```

---

## INTERDICTIONS

### Python
- ❌ `HTTPException` directement → ✅ `AppError` avec `ErrorCode`
- ❌ `print()` → ✅ `structlog.get_logger()`
- ❌ `requests` (sync) → ✅ `httpx` (async)
- ❌ `datetime.now()` → ✅ `datetime.now(UTC)` (toujours UTC)
- ❌ `os.getenv()` inline → ✅ `config.py` via Pydantic `BaseSettings`
- ❌ `try: ... except Exception:` → ✅ Catch exceptions spécifiques
- ❌ SQL brut sans paramètres → ✅ Parameterized queries
- ❌ Secrets en dur dans le code → ✅ Env vars via `config.py`
- ❌ `from typing import Optional` → ✅ `str | None` (Python 3.12+)
- ❌ Token Shopify en clair en DB → ✅ Fernet encryption

### TypeScript
- ❌ `any` → ✅ Types explicites ou `unknown`
- ❌ `console.log` en production → ✅ Logger structuré
- ❌ `fetch()` inline partout → ✅ `api` client dans `lib/api.ts`
- ❌ CSS inline ou modules CSS → ✅ Tailwind uniquement
- ❌ `var` → ✅ `const` / `let`
- ❌ `enum` → ✅ `as const` objects ou union types

### Architecture
- ❌ Logique métier dans les routes API → ✅ Services layer
- ❌ Appel Shopify API depuis le frontend → ✅ Toujours via le backend
- ❌ Modifier la DB sans migration numérotée → ✅ `database/migrations/`
- ❌ Commit sur `main` directement → ✅ Branch + PR
- ❌ Deploy sans tests qui passent → ✅ CI vérifie avant merge

---

## ERROR HANDLING

Hiérarchie centralisée. Catalogue complet dans `docs/ERRORS.md`.

```python
# app/core/exceptions.py

class AppError(Exception):
    """Base. TOUTES les erreurs héritent de celle-ci."""
    def __init__(self, code: ErrorCode, message: str, status_code: int = 500,
                 context: dict | None = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.context = context or {}

class ShopifyError(AppError): ...      # API Shopify (rate limit, token expiré, etc.)
class ScanError(AppError): ...         # Erreurs pendant un scan
class BillingError(AppError): ...      # Stripe (checkout, webhook, plan)
class AuthError(AppError): ...         # Auth/permissions
class AgentError(AppError): ...        # Claude API, Mem0, LangGraph

# Handler global — main.py
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    logger.error("app_error", code=exc.code, message=exc.message, **exc.context)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )
```

---

## VARIABLES D'ENVIRONNEMENT

```bash
# === Supabase ===
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...     # Backend only, JAMAIS exposé au frontend

# === Shopify ===
SHOPIFY_API_KEY=xxx
SHOPIFY_API_SECRET=xxx
SHOPIFY_API_VERSION=2025-04
SHOPIFY_SCOPES=read_products,write_products,read_themes,write_themes,read_orders,read_online_store

# === Stripe ===
STRIPE_SECRET_KEY=sk_...
STRIPE_PUBLISHABLE_KEY=pk_...
STRIPE_WEBHOOK_SECRET=whsec_...

# === Claude API ===
ANTHROPIC_API_KEY=sk-ant-...

# === Mem0 ===
MEM0_API_KEY=xxx                      # Si hosted. Sinon config pgvector dans Supabase.

# === Redis ===
REDIS_URL=redis://...                  # Railway managed Redis

# === Resend ===
RESEND_API_KEY=re_...

# === Sentry ===
SENTRY_DSN=https://...

# === LangSmith ===
LANGCHAIN_API_KEY=ls_...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=storemd

# === App ===
APP_ENV=development|staging|production
APP_URL=https://storemd.com
BACKEND_URL=https://api.storemd.com
FERNET_KEY=xxx                         # Chiffrement tokens Shopify
```

Chargées via Pydantic `BaseSettings` dans `backend/app/config.py`.
Frontend : uniquement les vars préfixées `NEXT_PUBLIC_`.

---

## SHOPIFY SCOPES

```
read_products       → Catalogue scan, listing analyzer, agentic readiness
write_products      → One-Click Fix (alt text, metafields, descriptions)
read_themes         → Theme analysis, residue detection, code weight
write_themes        → One-Click Fix (supprimer code résiduel)
read_orders         → Traffic analytics, bot filter data
read_online_store   → Pages, blog posts, navigation
```

L'app demande TOUTES les scopes au moment de l'install.
Le merchant voit la liste complète pendant le OAuth consent screen.

---

## API REST — ROUTES PRINCIPALES

```
# Auth
GET    /api/v1/auth/install              # Shopify OAuth redirect
GET    /api/v1/auth/callback             # Shopify OAuth callback
POST   /api/v1/auth/logout               # Logout

# Stores
GET    /api/v1/stores/{store_id}         # Store info
GET    /api/v1/stores/{store_id}/apps    # Apps installées + impact

# Scans
POST   /api/v1/stores/{store_id}/scans           # Trigger scan
GET    /api/v1/stores/{store_id}/scans           # List scans (paginated)
GET    /api/v1/stores/{store_id}/scans/{scan_id} # Scan result + issues
GET    /api/v1/stores/{store_id}/health          # Current health score + trend

# Listings
GET    /api/v1/stores/{store_id}/listings/scan       # Product analyses
GET    /api/v1/stores/{store_id}/listings/priorities  # Priorisation revenue

# Agentic
GET    /api/v1/stores/{store_id}/agentic/score    # Agentic readiness score
POST   /api/v1/stores/{store_id}/agentic/fixes    # Generate + apply agentic fixes
GET    /api/v1/stores/{store_id}/products/hs-codes # HS code validation

# Compliance
GET    /api/v1/stores/{store_id}/accessibility    # WCAG scan
GET    /api/v1/stores/{store_id}/links/broken     # Broken links

# Browser (Pro)
GET    /api/v1/stores/{store_id}/visual/diff      # Visual store test
GET    /api/v1/stores/{store_id}/simulation       # User simulation results

# Fixes
POST   /api/v1/stores/{store_id}/fixes/{fix_id}/apply   # Apply fix
POST   /api/v1/stores/{store_id}/fixes/{fix_id}/revert  # Revert fix

# Feedback (Ouroboros)
POST   /api/v1/feedback                           # Accept/reject recommendation

# Billing
POST   /api/v1/billing/checkout                   # Create Stripe checkout
GET    /api/v1/billing/portal                     # Stripe customer portal URL

# Notifications
GET    /api/v1/notifications                      # List (paginated)
PATCH  /api/v1/notifications/{id}/read            # Mark read

# Reports
GET    /api/v1/stores/{store_id}/reports/latest   # Latest weekly report

# Webhooks (pas de JWT — HMAC/signature validation)
POST   /api/v1/webhooks/shopify                   # Shopify webhooks
POST   /api/v1/webhooks/stripe                    # Stripe webhooks

# Healthcheck
GET    /api/v1/health                             # Status + DB + Redis
```

Versionné `/api/v1/`. JSON. Paginé cursor-based. Auth JWT sauf webhooks (HMAC).

---

## WORKFLOW DE DÉVELOPPEMENT

### Ajouter une feature (end-to-end)

1. **Lire** `docs/FEATURES.md` — trouver la feature, son module, son plan requis
2. **DB** — migration dans `database/migrations/`, RLS policy, `NOTIFY pgrst`
3. **Scanner** — dans `backend/app/agent/analyzers/`, hérite de `BaseScanner`
4. **Service** — logique métier dans `backend/app/services/`
5. **Endpoint** — route dans `backend/app/api/routes/`, Pydantic schemas
6. **Frontend** — composant + page si nécessaire
7. **Tests** — pytest backend + vitest frontend
8. **Checklist** — `.claude/skills/feature-impl/SKILL.md`

### Ajouter un scanner

Command `/add-scanner` ou skill `.claude/skills/scan-pipeline/SKILL.md`.

### Deploy

Command `/deploy` ou `docs/DEPLOY.md`.

---

## CONVENTIONS

### Nommage

| Élément | Convention | Exemple |
|---------|-----------|---------|
| Fichiers Python | snake_case | `health_scorer.py` |
| Classes Python | PascalCase | `HealthScorer` |
| Fonctions Python | snake_case | `calculate_score()` |
| Fichiers TS/TSX | kebab-case | `score-card.tsx` |
| Composants React | PascalCase | `ScoreCard` |
| Tables DB | snake_case pluriel | `scans`, `scan_issues` |
| Colonnes DB | snake_case | `store_id`, `created_at` |
| Env vars | SCREAMING_SNAKE | `SUPABASE_URL` |
| Branches git | type/description | `feat/agentic-scanner`, `fix/scan-timeout` |

### Commits

```
feat(scanner): add agentic readiness analyzer
fix(api): handle Shopify rate limit 429
refactor(agent): extract memory loading to separate node
docs(arch): update scan pipeline diagram
test(billing): add Stripe webhook mock
chore(deps): bump langchain to 0.3.x
```

---

## RÉFÉRENCES

| Tu travailles sur... | Lis d'abord |
|---------------------|-------------|
| N'importe quoi | `context.md` |
| Une feature | `docs/FEATURES.md` |
| Le schéma DB | `docs/DATABASE.md` |
| L'API Shopify | `docs/SHOPIFY.md` + `.claude/skills/shopify-api/SKILL.md` |
| L'agent IA | `docs/AGENT.md` + `.claude/skills/agent-loop/SKILL.md` |
| Un scanner | `.claude/skills/scan-pipeline/SKILL.md` |
| Le billing Stripe | `.claude/skills/stripe-billing/SKILL.md` |
| La sécurité | `docs/SECURITY.md` + `.claude/skills/owasp-security/SKILL.md` |
| Supabase / DB | `.claude/skills/supabase-patterns/SKILL.md` |
| Le frontend | `docs/UI.md` |
| Le deploy | `docs/DEPLOY.md` |
| Les tests | `docs/TESTS.md` |
| Un bug | `.claude/skills/systematic-debugging/SKILL.md` |
| Mem0 / mémoire | `.claude/skills/mem0-integration/SKILL.md` |
| Playwright | `.claude/skills/browser-automation/SKILL.md` |
| Agentic Commerce | `.claude/skills/agentic-readiness/SKILL.md` |

---

## RÈGLES ABSOLUES

1. **JAMAIS de code sans tests.** Chaque endpoint, scanner, service : minimum 1 test happy path + 1 test error.
2. **JAMAIS de migration DB sans RLS.** Table créée = RLS policy dans le même fichier.
3. **JAMAIS d'appel Shopify API sans rate limit handling.** 429 → exponential backoff retry.
4. **JAMAIS de token Shopify en clair en DB.** Fernet encryption.
5. **JAMAIS de `any` en TypeScript.** Zéro tolérance.
6. **JAMAIS de logique métier dans les routes.** Routes → Services → DB/API.
7. **JAMAIS de commit sur `main`.** Feature branch → PR → merge.
8. **TOUJOURS vérifier le plan merchant** avant feature payante. Mapping dans `docs/FEATURES.md`.
9. **TOUJOURS structlog** avec context (store_id, merchant_id, scan_id).
10. **TOUJOURS UTC** pour les dates. Le frontend convertit en timezone locale.
