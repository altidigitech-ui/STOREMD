# MONITORING.md — Monitoring & Alerting StoreMD

> **Sentry (errors), structlog (logs), LangSmith (LLM), métriques business.**
> **Savoir AVANT les merchants que quelque chose ne va pas.**

---

## STACK MONITORING

```
┌─────────────────────────────────────────────────────────┐
│                    MONITORING STACK                       │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Sentry      │  │  structlog   │  │  LangSmith   │  │
│  │              │  │              │  │              │  │
│  │  Exceptions  │  │  JSON logs   │  │  LLM traces  │  │
│  │  Performance │  │  Structured  │  │  Cost track  │  │
│  │  Alerts      │  │  Contextual  │  │  Latency     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐                     │
│  │  Healthcheck  │  │  Métriques   │                     │
│  │              │  │  business    │                     │
│  │  /api/v1/    │  │              │                     │
│  │  health      │  │  MRR, churn, │                     │
│  │              │  │  scan rate,  │                     │
│  │  DB + Redis  │  │  fix rate    │                     │
│  └──────────────┘  └──────────────┘                     │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 1. SENTRY — ERROR TRACKING

### Setup backend

```python
# app/main.py

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration

def init_sentry():
    if settings.APP_ENV == "test":
        return  # Pas de Sentry en test

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            CeleryIntegration(),
            HttpxIntegration(),
        ],
        traces_sample_rate=0.1 if settings.APP_ENV == "production" else 1.0,
        profiles_sample_rate=0.1,
        environment=settings.APP_ENV,
        release=settings.APP_VERSION,

        # Filtrer les données sensibles
        before_send=filter_sensitive_data,

        # Ne pas capturer les erreurs attendues (rate limit, plan required)
        before_send_transaction=None,
    )


def filter_sensitive_data(event, hint):
    """Supprime les données sensibles avant d'envoyer à Sentry."""
    # Supprimer les headers Authorization
    if "request" in event and "headers" in event["request"]:
        headers = event["request"]["headers"]
        if isinstance(headers, dict):
            headers.pop("Authorization", None)
            headers.pop("X-Shopify-Access-Token", None)

    # Supprimer les tokens dans les breadcrumbs
    if "breadcrumbs" in event:
        for crumb in event.get("breadcrumbs", {}).get("values", []):
            data = crumb.get("data", {})
            for key in list(data.keys()):
                if "token" in key.lower() or "secret" in key.lower() or "key" in key.lower():
                    data[key] = "[FILTERED]"

    return event
```

### Setup frontend

```typescript
// lib/sentry.ts

import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NODE_ENV,
  tracesSampleRate: 0.1,
  replaysSessionSampleRate: 0,    // Pas de session replay (privacy)
  replaysOnErrorSampleRate: 0.1,  // Replay uniquement sur erreur

  // Ignorer les erreurs réseau banales
  ignoreErrors: [
    "Network request failed",
    "Failed to fetch",
    "AbortError",
    "ResizeObserver loop limit exceeded",
  ],
});
```

### Erreurs à NE PAS envoyer à Sentry

Ces erreurs sont attendues et gérées — elles polluent Sentry si on les capture :

```python
# Dans le handler global, ne pas capturer certaines erreurs
SENTRY_IGNORE_CODES = {
    ErrorCode.RATE_LIMIT_EXCEEDED,      # Normal sous charge
    ErrorCode.PLAN_REQUIRED,            # Feature gating attendu
    ErrorCode.SCAN_LIMIT_REACHED,       # Usage limit attendu
    ErrorCode.SCAN_ALREADY_RUNNING,     # Double-click merchant
    ErrorCode.WEBHOOK_DUPLICATE,        # Idempotency normal
    ErrorCode.JWT_EXPIRED,              # Session expirée, refresh
    ErrorCode.FIX_ALREADY_APPLIED,      # Double-click fix
}

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    logger.error("app_error", code=exc.code, message=exc.message, **exc.context)

    # Ne pas envoyer à Sentry les erreurs business attendues
    if exc.code not in SENTRY_IGNORE_CODES and exc.status_code >= 500:
        sentry_sdk.capture_exception(exc)

    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )
```

### Alertes Sentry

Configurer dans Sentry Dashboard → Alerts :

| Alerte | Condition | Notification |
|--------|-----------|-------------|
| New issue (500) | Nouvelle exception 500 non vue avant | Slack + email immédiat |
| Issue spike | >10 occurrences de la même erreur en 5 min | Slack immédiat |
| HMAC failures | >5 `HMAC_INVALID` en 1h | Email (possible attaque) |
| Shopify token errors | >3 `SHOPIFY_TOKEN_EXPIRED` en 1h | Email (vérifier les tokens) |
| Claude API errors | >5 `CLAUDE_API_ERROR` en 30 min | Slack (Claude down ?) |
| Scan failure rate | >20% des scans échouent en 1h | Slack + email |

---

## 2. STRUCTLOG — LOGS STRUCTURÉS

### Configuration

```python
# app/core/logging.py

import structlog
import logging

def setup_logging():
    """Configure structlog pour le backend StoreMD."""

    # Processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.APP_ENV == "production":
        # Production : JSON pour Railway logs / parsing
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Dev : format lisible
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

### Patterns de logging

```python
import structlog
logger = structlog.get_logger()

# ─── SCAN LIFECYCLE ───

logger.info("scan_started",
    scan_id=scan_id,
    store_id=store_id,
    merchant_id=merchant_id,
    modules=modules,
    trigger=trigger,
)

logger.info("scanner_completed",
    scan_id=scan_id,
    scanner="app_impact",
    issues_found=3,
    duration_ms=2400,
)

logger.warning("scanner_failed",
    scan_id=scan_id,
    scanner="broken_links",
    error="Timeout after 60s",
)

logger.info("scan_completed",
    scan_id=scan_id,
    store_id=store_id,
    score=67,
    mobile_score=52,
    desktop_score=81,
    issues_count=5,
    critical_count=1,
    duration_ms=42000,
    partial=False,
)

logger.error("scan_failed",
    scan_id=scan_id,
    store_id=store_id,
    error="ShopifyError: Rate limit exceeded",
    retry=True,
)

# ─── AUTH ───

logger.info("oauth_completed", shop="mystore.myshopify.com", merchant_id="xxx")
logger.warning("hmac_validation_failed", shop="unknown.myshopify.com", topic="products/create")
logger.info("merchant_created", shop="mystore.myshopify.com")

# ─── BILLING ───

logger.info("plan_activated", merchant_id="xxx", plan="pro")
logger.info("plan_changed", merchant_id="xxx", old_plan="starter", new_plan="pro")
logger.info("plan_canceled", merchant_id="xxx")
logger.warning("invoice_payment_failed", merchant_id="xxx")

# ─── FIXES ───

logger.info("fix_applied", fix_id="xxx", fix_type="alt_text", store_id="yyy")
logger.info("fix_reverted", fix_id="xxx", store_id="yyy")
logger.error("fix_apply_failed", fix_id="xxx", error="Shopify API write failed")

# ─── NOTIFICATIONS ───

logger.info("notification_sent", merchant_id="xxx", channel="push", category="score_drop")
logger.warning("push_delivery_failed", merchant_id="xxx", error="Subscription expired")

# ─── AGENT ───

logger.info("mem0_recall", merchant_id="xxx", memories_count=5, duration_ms=120)
logger.warning("mem0_unavailable", error="Connection timeout")
logger.info("claude_api_call", model="claude-sonnet-4-20250514", tokens_input=3200, tokens_output=1100, cost_usd=0.013, duration_ms=2400)
logger.info("cross_store_signal", app="Reviews+", affected_stores=47)

# ─── LIFECYCLE ───

logger.info("app_uninstalled", shop="mystore.myshopify.com", merchant_id="xxx")
logger.info("webhook_processed", source="shopify", topic="products/create", shop="mystore.myshopify.com")
```

### Contexte automatique par requête

```python
# app/api/middleware/logging.py

from starlette.middleware.base import BaseHTTPMiddleware
import structlog

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Injecter le contexte dans tous les logs de cette requête
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request.headers.get("X-Request-ID", str(uuid4())),
            path=request.url.path,
            method=request.method,
        )

        response = await call_next(request)

        # Log la requête complétée
        logger.info("request_completed",
            status_code=response.status_code,
            duration_ms=int((time.monotonic() - start) * 1000),
        )

        return response
```

### Ce qu'on NE LOGUE JAMAIS

```python
# ❌ INTERDIT
logger.info("auth", token=access_token)                    # Token
logger.info("merchant", email="john@example.com")          # PII
logger.info("webhook", payload=webhook_payload)            # Payload complet (PII)
logger.info("shopify", api_secret=settings.SHOPIFY_SECRET) # Secret
logger.info("stripe", card="4242...")                       # Données carte
logger.debug("query", sql=raw_sql_query)                   # SQL brut avec données
```

---

## 3. LANGSMITH — LLM MONITORING

### Configuration

```python
# Env vars (dans Railway)
LANGCHAIN_API_KEY=ls_xxx
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=storemd

# LangSmith trace automatiquement tous les appels LangGraph
# Pas de code supplémentaire nécessaire — juste les env vars
```

### Ce que LangSmith capture

| Donnée | Utilité |
|--------|---------|
| Chaque appel Claude API (input/output) | Débugger les analyses incorrectes |
| Tokens consommés par appel | Tracking coûts |
| Latence par appel | Détecter les ralentissements |
| LangGraph execution trace | Voir le flow complet d'un scan |
| Erreurs Claude API | Rate limits, timeouts |

### Métriques à surveiller dans LangSmith

| Métrique | Seuil d'alerte | Action |
|----------|---------------|--------|
| Latence moyenne Claude API | >5s | Vérifier la complexité des prompts |
| Coût moyen par scan | >$0.10 | Optimiser les prompts (trop de contexte ?) |
| Taux d'erreur Claude API | >5% | Vérifier rate limits, fallback actif ? |
| Tokens input moyen | >15,000 | Tronquer le contexte Mem0 |

### Custom tracking (en plus de LangSmith auto)

```python
# app/services/claude.py

async def claude_analyze(prompt: str) -> str:
    start = time.monotonic()

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
    )

    duration_ms = int((time.monotonic() - start) * 1000)
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens

    # Estimation coût (Sonnet 4 pricing)
    cost_usd = (input_tokens * 0.003 + output_tokens * 0.015) / 1000

    logger.info("claude_api_call",
        model="claude-sonnet-4-20250514",
        tokens_input=input_tokens,
        tokens_output=output_tokens,
        cost_usd=round(cost_usd, 4),
        duration_ms=duration_ms,
    )

    return response.content[0].text
```

---

## 4. HEALTHCHECK

### Endpoint

```python
# app/api/routes/health.py

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.config import settings

router = APIRouter(tags=["health"])

@router.get("/api/v1/health")
async def healthcheck():
    """Status du backend. Pas d'auth.
    
    Vérifie : DB (Supabase), Redis, et retourne le status.
    Railway utilise cet endpoint pour les health checks automatiques.
    """
    health = {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
    }

    # DB check
    try:
        supabase = get_supabase_service()
        result = supabase.table("merchants").select("id").limit(1).execute()
        health["db"] = "connected"
    except Exception as exc:
        health["db"] = "error"
        health["status"] = "unhealthy"
        logger.error("healthcheck_db_failed", error=str(exc)[:200])

    # Redis check
    try:
        redis = get_redis()
        await redis.ping()
        health["redis"] = "connected"
    except Exception as exc:
        health["redis"] = "error"
        health["status"] = "unhealthy"
        logger.error("healthcheck_redis_failed", error=str(exc)[:200])

    # Celery check (optionnel — coûteux, faire périodiquement pas à chaque call)
    # health["celery"] = await check_celery_health()

    status_code = 200 if health["status"] == "healthy" else 503
    return JSONResponse(content=health, status_code=status_code)
```

### Railway config

```
Service storemd-api :
  Health Check Path     : /api/v1/health
  Health Check Timeout  : 10s
  Health Check Interval : 30s
  Restart Policy        : on failure (max 3 retries)
```

---

## 5. MÉTRIQUES BUSINESS

### Métriques à tracker

Ces métriques ne sont pas dans un outil externe — elles sont calculées à partir de la DB et loguées périodiquement.

```python
# tasks/metrics_tasks.py

@celery.task
async def log_daily_metrics():
    """Celery beat — daily à 6 AM UTC. Log les métriques business."""
    supabase = get_supabase_service()

    # ─── MERCHANTS ───

    total_merchants = await count_query(supabase, "merchants", {})
    active_merchants = await count_query(supabase, "merchants",
        {"onboarding_completed": True})
    by_plan = await count_by_plan(supabase)

    logger.info("metrics_merchants",
        total=total_merchants,
        active=active_merchants,
        free=by_plan.get("free", 0),
        starter=by_plan.get("starter", 0),
        pro=by_plan.get("pro", 0),
        agency=by_plan.get("agency", 0),
    )

    # ─── REVENUE ───

    mrr = (
        by_plan.get("starter", 0) * 39
        + by_plan.get("pro", 0) * 99
        + by_plan.get("agency", 0) * 249
    )

    logger.info("metrics_revenue", mrr_usd=mrr)

    # ─── SCANS ───

    scans_24h = await count_scans_last_24h(supabase)
    scans_success = await count_scans_last_24h(supabase, status="completed")
    scans_failed = await count_scans_last_24h(supabase, status="failed")
    scans_partial = await count_scans_last_24h(supabase, partial=True)

    success_rate = (scans_success / scans_24h * 100) if scans_24h > 0 else 0

    logger.info("metrics_scans",
        total_24h=scans_24h,
        success=scans_success,
        failed=scans_failed,
        partial=scans_partial,
        success_rate_pct=round(success_rate, 1),
    )

    # ─── FIXES ───

    fixes_applied_24h = await count_fixes_last_24h(supabase, status="applied")
    fixes_reverted_24h = await count_fixes_last_24h(supabase, status="reverted")
    fixes_failed_24h = await count_fixes_last_24h(supabase, status="failed")

    logger.info("metrics_fixes",
        applied_24h=fixes_applied_24h,
        reverted_24h=fixes_reverted_24h,
        failed_24h=fixes_failed_24h,
    )

    # ─── FEEDBACK (OUROBOROS) ───

    feedback_24h = await count_feedback_last_24h(supabase)
    acceptance_rate = await calculate_acceptance_rate(supabase, days=30)

    logger.info("metrics_feedback",
        total_24h=feedback_24h,
        acceptance_rate_30d_pct=round(acceptance_rate, 1),
    )

    # ─── AGENT COSTS ───

    claude_cost_24h = await calculate_claude_cost_24h()

    logger.info("metrics_costs",
        claude_api_cost_24h_usd=round(claude_cost_24h, 2),
        estimated_monthly_usd=round(claude_cost_24h * 30, 2),
    )
```

### Celery beat schedule

```python
# tasks/celery_app.py (ajout au beat_schedule)

"daily-metrics": {
    "task": "tasks.metrics_tasks.log_daily_metrics",
    "schedule": crontab(hour=6, minute=0),  # 6 AM UTC daily
},
```

### Tableau de bord métriques

Pas d'outil externe au MVP. Les métriques sont dans les logs structlog (Railway logs). Requêtes pour extraire :

```bash
# Railway logs — filtrer les métriques
railway logs --service storemd-worker | grep "metrics_"

# Exemples de sortie (JSON) :
# {"event":"metrics_merchants","total":142,"active":98,"free":67,"starter":22,"pro":8,"agency":1,"timestamp":"2026-04-10T06:00:00Z"}
# {"event":"metrics_revenue","mrr_usd":2405,"timestamp":"2026-04-10T06:00:00Z"}
# {"event":"metrics_scans","total_24h":87,"success":82,"failed":3,"partial":2,"success_rate_pct":94.3,"timestamp":"2026-04-10T06:00:00Z"}
```

### Seuils d'alerte métriques

| Métrique | Seuil | Action |
|----------|-------|--------|
| Scan success rate | <90% | Investiguer les échecs (Shopify rate limit ? Claude down ?) |
| Fix failure rate | >10% | Vérifier les scopes Shopify, API write errors |
| Feedback acceptance rate (30d) | <50% | Les recommandations ne sont pas pertinentes — revoir les prompts |
| Claude API cost/scan | >$0.10 | Optimiser les prompts, réduire le contexte |
| MRR | tracking | Pas d'alerte — juste le suivi |
| Churn M1 | >8% | Analyser les raisons (survey uninstall) |
| Onboarding completion | <85% | Simplifier l'onboarding |
| Day 1 retention | <60% | Le "aha moment" ne fonctionne pas |

---

## 6. MONITORING INFRA

### Railway

Railway expose des métriques dans le dashboard :

| Métrique | Où | Seuil |
|----------|-----|-------|
| CPU usage | Railway → Service → Metrics | >80% sustained → scale |
| Memory usage | Railway → Service → Metrics | >80% → augmenter RAM ou optimiser |
| Request count | Railway → Service → Metrics | Trending |
| Response time p95 | Railway → Service → Metrics | >500ms → investiguer |
| Deploy status | Railway → Deployments | Doit être "Active" |

### Vercel

| Métrique | Où | Seuil |
|----------|-----|-------|
| Build time | Vercel → Deployments | >2min → optimiser le build |
| Edge response time | Vercel → Analytics | >200ms p95 |
| Error rate | Vercel → Logs | >1% |

### Supabase

| Métrique | Où | Seuil |
|----------|-----|-------|
| DB connections | Supabase → Database → Reports | >80% pool → upgrade plan |
| DB size | Supabase → Database → Reports | >80% quota → cleanup ou upgrade |
| API requests | Supabase → API → Reports | Trending (rate limits) |
| Auth users | Supabase → Authentication | = merchants count |

---

## 7. INCIDENT RESPONSE

### Quand quelque chose casse en prod

```
ÉTAPE 1 — DÉTECTER
  Signal : Sentry alert, healthcheck 503, merchant report, metrics anomaly

ÉTAPE 2 — ÉVALUER LA SÉVÉRITÉ
  P0 (critique)  : App down, data loss, security breach → fix immédiat
  P1 (haute)     : Feature majeure cassée, >10% merchants affectés → fix en 2h
  P2 (moyenne)   : Feature mineure cassée, <10% merchants → fix en 24h
  P3 (basse)     : Bug cosmétique, workaround existe → fix dans le sprint

ÉTAPE 3 — COMMUNIQUER
  P0/P1 : Status page update (si on en a une), email aux merchants affectés
  P2/P3 : Fix silencieux, changelog update

ÉTAPE 4 — FIXER
  Voir .claude/skills/systematic-debugging/SKILL.md
  Voir .claude/skills/saas-debug-pipeline/SKILL.md

ÉTAPE 5 — POST-MORTEM (P0/P1 uniquement)
  - Qu'est-ce qui s'est passé ?
  - Pourquoi ça s'est passé ?
  - Qu'est-ce qui a été fait pour fixer ?
  - Comment empêcher que ça se reproduise ?
  - Documenter dans docs/CHANGELOG.md
```

---

## INTERDICTIONS

- ❌ Logger des tokens, secrets, PII → ✅ Voir "Ce qu'on NE LOGUE JAMAIS"
- ❌ Capturer toutes les exceptions dans Sentry (pollution) → ✅ Filtrer les erreurs business attendues
- ❌ Métriques sans contexte (juste un nombre) → ✅ Toujours inclure la période, le scope
- ❌ Ignorer les alertes Sentry → ✅ Chaque nouvelle exception 500 est investiguée
- ❌ Monitoring qui coûte plus que le problème → ✅ Logs + Sentry free tier au MVP, scaler après
- ❌ Dashboard externe complexe au MVP → ✅ structlog + grep dans Railway logs
- ❌ LangSmith en mode "log everything" → ✅ Sample rate 0.1 en prod (1.0 en dev)
- ❌ Healthcheck qui fait une opération lourde → ✅ Juste DB ping + Redis ping
