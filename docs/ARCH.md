# ARCH.md — Architecture technique StoreMD

> **Comment le système fonctionne, couche par couche.**
> **Lire CLAUDE.md (stack, structure, patterns) et context.md (features, modules) avant ce fichier.**

---

## VUE D'ENSEMBLE

```
┌─────────────────────────────────────────────────────────────┐
│                   FRONTEND (Next.js 14)                      │
│  TypeScript strict + Tailwind + shadcn/ui                    │
│  Shopify App Bridge (embedded app)                           │
│  PWA (service worker, push notifications)                    │
│  Deploy: Vercel                                              │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API (HTTPS, JWT auth)
┌────────────────────────▼────────────────────────────────────┐
│                   BACKEND (FastAPI)                           │
│  Python 3.12+ / Pydantic v2 / async                         │
│  Routes → Services → Models                                 │
│  Deploy: Railway (service "storemd-api")                     │
└──────────┬─────────────────────────────────┬────────────────┘
           │ Celery dispatch                 │ Direct DB
┌──────────▼──────────────┐     ┌────────────▼────────────────┐
│   CELERY WORKER          │     │   DATA LAYER                │
│                          │     │                              │
│   Scan tasks             │     │   Supabase PostgreSQL + RLS  │
│   Browser tasks          │     │   Redis (cache + queue)      │
│   Report tasks           │     │   Supabase Storage (files)   │
│   Background analysis    │     │   Mem0 (vector memory)       │
│                          │     │                              │
│   Deploy: Railway        │     └──────────────────────────────┘
│   (service "storemd-     │
│    worker")              │
└──────────┬──────────────┘
           │
┌──────────▼──────────────────────────────────────────────────┐
│                   AGENT LAYER (dans le worker)               │
│                                                              │
│   LangGraph          Claude API          Mem0                │
│   (state machine)    (LLM analysis)      (persistent memory) │
│                                                              │
│   ┌──────────────────────────────────────────────────────┐  │
│   │  1. DETECT  ── Webhooks, crons, browser triggers     │  │
│   │  2. ANALYZE ── Claude API + contexte Mem0            │  │
│   │  3. ACT     ── Notifications + fixes + reports       │  │
│   │  4. LEARN   ── Feedback → Mem0 → Ouroboros           │  │
│   └──────────────────────────────────────────────────────┘  │
│                                                              │
│   Playwright (browser automation, container séparé si scale) │
└─────────────────────────────────────────────────────────────┘
```

---

## BACKEND — LAYERS

### Layer 1 : Routes (app/api/routes/)

Thin controllers. Pas de logique métier. Responsabilités :
- Validation input (Pydantic)
- Auth check (JWT middleware)
- Plan check (`check_plan_access`)
- Appel service
- Retour JSON

```python
@router.post("/scans")
async def create_scan(
    request: ScanRequest,
    store: Store = Depends(get_current_store),
    scan_service: ScanService = Depends(get_scan_service),
):
    await check_plan_access(store.merchant_id, request.modules)
    scan = await scan_service.trigger_scan(store, request.modules)
    return ScanResponse.model_validate(scan)
```

### Layer 2 : Services (app/services/)

Logique métier. Orchestrent DB, APIs externes, dispatch Celery.

```python
class ScanService:
    def __init__(self, supabase: SupabaseClient, shopify: ShopifyClient):
        self.supabase = supabase
        self.shopify = shopify

    async def trigger_scan(self, store: Store, modules: list[str]) -> Scan:
        # 1. Créer le scan record en DB (status: pending)
        scan = await self.create_scan_record(store.id, store.merchant_id, modules)
        # 2. Dispatch en background via Celery
        run_scan.delay(scan.id, store.id, modules)
        # 3. Retourner le scan (le client poll pour le résultat)
        return scan
```

### Layer 3 : Models (app/models/)

Pydantic models. Deux types :
- **DB models** : représentent les tables Supabase (scan.py, store.py, merchant.py)
- **Schemas** : request/response API (schemas.py)

### Layer 4 : Core (app/core/)

Transversal : exceptions (`AppError` hierarchy), security (Fernet, HMAC), logging (structlog).

---

## AGENT LAYER — DÉTAIL

### LangGraph State Machine

L'agent est un graph LangGraph. Chaque scan suit ce flow :

```
                    ┌─────────┐
                    │  START   │
                    └────┬────┘
                         │
                    ┌────▼────┐
                    │ DETECT  │  Identifier le trigger + charger les données Shopify
                    └────┬────┘
                         │
                    ┌────▼────────┐
                    │ LOAD MEMORY │  Récupérer contexte Mem0 (merchant prefs, historique, cross-store)
                    └────┬────────┘
                         │
                    ┌────▼──────────┐
                    │ RUN SCANNERS  │  Exécuter les analyzers selon les modules demandés
                    └────┬──────────┘
                         │
                    ┌────▼────────┐
                    │  ANALYZE    │  Claude API interprète les résultats avec contexte Mem0
                    └────┬────────┘
                         │
                    ┌────▼──────────────┐
                    │ GENERATE FIXES    │  Claude API génère les recommandations
                    └────┬──────────────┘
                         │
                    ┌────▼────────┐
                    │   NOTIFY    │  Push/email/in-app si alertes
                    └────┬────────┘
                         │
                    ┌────▼──────────┐
                    │ SAVE RESULTS  │  Persister scan + issues + score en DB
                    └────┬──────────┘
                         │
                    ┌────▼────┐
                    │   END   │
                    └─────────┘
```

```python
# app/agent/orchestrator.py

from langgraph.graph import StateGraph, END
from app.agent.state import AgentState

class ScanOrchestrator:
    def __init__(self, memory: StoreMemory, shopify: ShopifyClient,
                 supabase: SupabaseClient):
        self.memory = memory
        self.shopify = shopify
        self.supabase = supabase

    def build_graph(self) -> CompiledGraph:
        graph = StateGraph(AgentState)

        graph.add_node("detect", self.detect)
        graph.add_node("load_memory", self.load_memory)
        graph.add_node("run_scanners", self.run_scanners)
        graph.add_node("analyze", self.analyze)
        graph.add_node("generate_fixes", self.generate_fixes)
        graph.add_node("notify", self.notify)
        graph.add_node("save_results", self.save_results)

        graph.set_entry_point("detect")
        graph.add_edge("detect", "load_memory")
        graph.add_edge("load_memory", "run_scanners")
        graph.add_edge("run_scanners", "analyze")
        graph.add_edge("analyze", "generate_fixes")
        graph.add_edge("generate_fixes", "notify")
        graph.add_edge("notify", "save_results")
        graph.add_edge("save_results", END)

        return graph.compile()
```

### AgentState

```python
# app/agent/state.py

from dataclasses import dataclass, field
from app.models.scan import ScannerResult, ScanIssue, Fix

@dataclass
class AgentState:
    # --- Input ---
    store_id: str
    merchant_id: str
    scan_id: str
    modules: list[str]                                   # ["health", "listings", "agentic"]
    trigger: str                                          # "manual" | "cron" | "webhook"

    # --- Memory (loaded from Mem0) ---
    historical_context: list[dict] = field(default_factory=list)
    merchant_preferences: dict = field(default_factory=dict)
    cross_store_signals: list[dict] = field(default_factory=list)

    # --- Scanner results (populated by run_scanners) ---
    scanner_results: dict[str, ScannerResult] = field(default_factory=dict)

    # --- Analysis (populated by analyze + generate_fixes) ---
    analysis_text: str = ""
    issues: list[ScanIssue] = field(default_factory=list)
    fixes: list[Fix] = field(default_factory=list)
    score: int = 0
    mobile_score: int = 0
    desktop_score: int = 0

    # --- Output ---
    notifications_sent: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
```

---

## SCAN PIPELINE — SÉQUENCEMENT

Les scanners s'exécutent en groupes parallèles, puis séquentiels pour les opérations lourdes :

```
Trigger (cron / webhook / manual)
    │
    ▼
┌──────────────────────────────────────────────────┐
│ GROUPE 1 — Shopify API (parallel, rate limit     │
│            partagé via semaphore)                 │
│                                                   │
│ ├── health_scorer      (theme, apps, pages)      │
│ ├── app_impact         (script tags, assets)     │
│ ├── residue_detector   (theme files vs apps)     │
│ ├── ghost_billing      (charges vs apps)         │
│ ├── code_weight        (JS/CSS par source)       │
│ ├── security_monitor   (headers, scopes)         │
│ ├── pixel_health       (scripts analysis)        │
│ ├── listing_analyzer   (products, si module)     │
│ ├── agentic_readiness  (metafields, si module)   │
│ └── hs_code_validator  (hs_code field, si module)│
└────────────────────┬─────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────┐
│ GROUPE 2 — External checks (parallel, pas de    │
│            rate limit Shopify)                    │
│                                                   │
│ ├── broken_links       (HTTP HEAD sur chaque lien)│
│ ├── email_health       (DNS lookups SPF/DKIM)    │
│ ├── bot_traffic        (log analysis)            │
│ └── accessibility      (WCAG check statique HTML)│
└────────────────────┬─────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────┐
│ GROUPE 3 — Browser automation (séquentiel,       │
│            Pro only, Playwright lourd)            │
│                                                   │
│ 1. visual_store_test        (screenshots + diff) │
│ 2. real_user_simulation     (parcours complet)   │
│ 3. accessibility_live       (WCAG rendu réel)    │
└────────────────────┬─────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────┐
│ CLAUDE API ANALYSIS                              │
│                                                   │
│ Tous les résultats agrégés + contexte Mem0       │
│ → Score composite + issues priorisées + fixes    │
└────────────────────┬─────────────────────────────┘
                     │
                     ▼
            Notifications + Save DB
```

### Shopify API Rate Limiting

Shopify autorise ~40 requests/second (REST) ou un bucket de cost points (GraphQL). TOUS les scanners du Groupe 1 partagent le même client avec :

```python
# app/services/shopify.py

class ShopifyClient:
    def __init__(self, shop_domain: str, access_token: str):
        self.client = httpx.AsyncClient(...)
        self.semaphore = asyncio.Semaphore(4)  # max 4 requêtes simultanées
        self.retry_config = RetryConfig(
            max_retries=3,
            backoff_base=2.0,        # 2s, 4s, 8s
            retry_on_status=[429, 500, 502, 503],
        )

    async def graphql(self, query: str, variables: dict | None = None) -> dict:
        async with self.semaphore:
            for attempt in range(self.retry_config.max_retries + 1):
                response = await self.client.post(
                    f"https://{self.shop_domain}/admin/api/{API_VERSION}/graphql.json",
                    json={"query": query, "variables": variables or {}},
                    headers={"X-Shopify-Access-Token": self.access_token},
                )
                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", 2))
                    logger.warning("shopify_rate_limit", retry_after=retry_after)
                    await asyncio.sleep(retry_after)
                    continue
                response.raise_for_status()
                data = response.json()
                if "errors" in data:
                    raise ShopifyError(
                        code=ErrorCode.SHOPIFY_GRAPHQL_ERROR,
                        message=str(data["errors"]),
                        status_code=502,
                    )
                return data["data"]
            raise ShopifyError(
                code=ErrorCode.SHOPIFY_RATE_LIMIT,
                message="Rate limit exceeded after retries",
                status_code=429,
            )
```

### BaseScanner

Tous les analyzers héritent de `BaseScanner` :

```python
# app/agent/analyzers/base.py

from abc import ABC, abstractmethod
from app.models.scan import ScannerResult

class BaseScanner(ABC):
    """Base class pour tous les scanners StoreMD."""

    name: str                    # "health_scorer", "app_impact", etc.
    module: str                  # "health", "listings", "agentic", "compliance", "browser"
    requires_plan: str           # "free", "starter", "pro"

    @abstractmethod
    async def scan(self, store_id: str, shopify: ShopifyClient,
                   memory_context: list[dict]) -> ScannerResult:
        """Exécute le scan et retourne les résultats."""
        ...

    async def should_run(self, modules: list[str], plan: str) -> bool:
        """Vérifie si ce scanner doit s'exécuter."""
        if self.module not in modules:
            return False
        plan_hierarchy = {"free": 0, "starter": 1, "pro": 2, "agency": 3}
        return plan_hierarchy.get(plan, 0) >= plan_hierarchy.get(self.requires_plan, 0)
```

---

## MEM0 — MÉMOIRE PERSISTANTE

### Types de mémoire

| Type | Scope | Exemples | TTL |
|---|---|---|---|
| **Merchant Memory** | 1 merchant | Préférences (refuse uninstalls, préfère CSS fixes), patterns saisonniers | Infini (tant qu'actif) |
| **Store Memory** | 1 store | Apps installées, baseline score, thème, historique scans | Infini |
| **Cross-Store Intelligence** | Tous les stores | "App X cause des problèmes sur 47 stores" | 90 jours rolling |
| **Agent Memory** | L'agent global | Taux d'acceptation par type de fix, recommandations efficaces | Infini |

### Client wrapper

```python
# app/agent/memory.py

from mem0 import Memory

class StoreMemory:
    def __init__(self):
        self.memory = Memory()  # ou MemoryClient si hosted

    async def recall(self, merchant_id: str, query: str) -> list[dict]:
        """Récupère les mémoires pertinentes pour l'analyse Claude."""
        return self.memory.search(
            query=query,
            user_id=f"storemd:{merchant_id}",
            limit=10,
        )

    async def remember(self, merchant_id: str, context: str):
        """Stocke un fait / préférence / pattern détecté."""
        self.memory.add(
            messages=[{"role": "system", "content": context}],
            user_id=f"storemd:{merchant_id}",
            metadata={"saas": "storemd"},
        )

    async def learn_from_feedback(
        self, merchant_id: str, recommendation_id: str,
        accepted: bool, reason: str | None = None,
    ):
        """Ouroboros — feedback loop couche LEARN."""
        context = f"Recommendation {recommendation_id}: "
        context += "ACCEPTED" if accepted else f"REJECTED (reason: {reason})"
        await self.remember(merchant_id, context)

    async def cross_store_signal(self, signal: str):
        """Intelligence cross-store (ex: app X problématique)."""
        self.memory.add(
            messages=[{"role": "system", "content": signal}],
            agent_id="storemd:global",
            metadata={"type": "cross_store"},
        )
```

### Ce que l'agent retient (StoreMD)

- Apps installées/désinstallées et leur impact mesuré
- Fixes acceptés vs refusés (et pourquoi)
- Baseline performance du store (score normal vs dégradé)
- Patterns temporels (dégradation le week-end = promos)
- Thème utilisé et ses limites connues
- Cross-store : quelles apps causent des problèmes globalement

---

## OUROBOROS — BOUCLE D'AUTO-AMÉLIORATION

Pas un agent autonome qui réécrit son code. Un pattern de feedback loop appliqué à la couche LEARN.

```
DETECT ──→ ANALYZE ──→ ACT ──→ FEEDBACK du merchant
  ▲                                    │
  │          ┌──────────┐              │
  └──────────│  LEARN   │◄─────────────┘
             │  Mem0    │
             │  stocke  │
             │  le      │
             │  feedback│
             └──────────┘
         Prochain cycle = MEILLEUR
```

```python
# app/agent/learner.py

class OuroborosLearner:
    """Couche 4 — APPRENDRE."""

    def __init__(self, memory: StoreMemory):
        self.memory = memory

    async def process_feedback(
        self, merchant_id: str, recommendation_id: str,
        accepted: bool, reason: str | None = None,
    ):
        # 1. Stocker le feedback dans Mem0
        await self.memory.learn_from_feedback(
            merchant_id, recommendation_id, accepted, reason
        )

        # 2. Mettre à jour le taux d'acceptation par type en DB
        rec_type = await self.get_recommendation_type(recommendation_id)
        await self.update_acceptance_rate(rec_type, accepted)

        # 3. Si pattern détecté → ajuster les futures recommandations
        if await self.has_enough_data(merchant_id):
            await self.adapt_strategy(merchant_id)

    async def adapt_strategy(self, merchant_id: str):
        """Adapte la priorisation des recommandations.

        Ex: si le merchant refuse systématiquement les uninstalls →
        prioriser les CSS fixes. Si le merchant accepte toujours
        les alt text fixes → proposer en bulk.
        """
        memories = await self.memory.recall(
            merchant_id,
            "recommendation preferences accepted rejected patterns"
        )
        # Claude API analyse les patterns et génère une stratégie adaptée
        # Stockée dans Mem0 pour les prochains scans
        ...
```

**Objectif :** Après 50 feedbacks, le taux d'acceptation des recommandations dépasse 80% (l'agent connaît le merchant).

---

## CELERY — BACKGROUND PROCESSING

### Services Railway

| Service | Start command | Rôle |
|---------|-------------|------|
| `storemd-api` | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` | FastAPI, routes, webhooks |
| `storemd-worker` | `celery -A tasks.celery_app worker --beat --loglevel=info` | Celery worker + beat scheduler |

Les deux services partagent le même code (même repo), mais des Dockerfiles différents.

### Task structure

```python
# tasks/scan_tasks.py

@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def run_scan(self, scan_id: str, store_id: str, modules: list[str]):
    """Task principal : exécute un scan complet."""
    try:
        # 1. Marquer le scan comme "running"
        update_scan_status(scan_id, "running")

        # 2. Construire et exécuter le graph LangGraph
        orchestrator = ScanOrchestrator(
            memory=StoreMemory(),
            shopify=get_shopify_client(store_id),
            supabase=get_supabase_service(),
        )
        graph = orchestrator.build_graph()
        result = graph.invoke(AgentState(
            store_id=store_id,
            merchant_id=get_merchant_id(store_id),
            scan_id=scan_id,
            modules=modules,
            trigger="celery",
        ))

        # 3. Sauvegarder les résultats
        save_scan_result(scan_id, result)

    except ShopifyError as exc:
        if exc.code == ErrorCode.SHOPIFY_RATE_LIMIT:
            self.retry(countdown=120)  # Retry dans 2 min
        else:
            mark_scan_failed(scan_id, str(exc))
            raise

    except Exception as exc:
        logger.error("scan_failed", scan_id=scan_id, error=str(exc))
        mark_scan_failed(scan_id, str(exc))
        raise
```

### Beat schedule (tâches planifiées)

```python
# tasks/celery_app.py

celery.conf.beat_schedule = {
    # Scans planifiés
    "daily-scans-pro": {
        "task": "tasks.scan_tasks.run_scheduled_scans",
        "schedule": crontab(hour=3, minute=0),       # 3 AM UTC
        "args": ["pro"],
    },
    "weekly-scans-starter": {
        "task": "tasks.scan_tasks.run_scheduled_scans",
        "schedule": crontab(hour=4, minute=0, day_of_week=1),  # Lundi 4 AM
        "args": ["starter"],
    },

    # Reports
    "weekly-reports": {
        "task": "tasks.report_tasks.send_weekly_reports",
        "schedule": crontab(hour=9, minute=0, day_of_week=1),  # Lundi 9 AM
    },

    # Background intelligence
    "cross-store-analysis": {
        "task": "tasks.scan_tasks.run_cross_store_analysis",
        "schedule": crontab(hour=5, minute=0),       # Daily 5 AM
    },
}
```

---

## FEATURES EXCLUSIVES ACTIVÉES PAR L'ARCHITECTURE

Ces features sont IMPOSSIBLES sans Mem0 + Ouroboros + Playwright. Aucun concurrent ne peut les copier sans reconstruire toute son architecture.

| Feature | Requiert | Ce que ça fait |
|---|---|---|
| **Adaptive Health Score** | Mem0 merchant memory | Le score s'adapte à la baseline DU store. Un store à 65 normalement est alerté à 60, pas à 50. |
| **App Risk Prediction** | Mem0 cross-store | "App X a causé des régressions sur 47 stores après sa mise à jour." |
| **Smart Fix Prioritization** | Mem0 feedback history | Fixes priorisés par probabilité d'acceptation par CE merchant. |
| **Weekend Degradation Detector** | Mem0 temporal patterns | "Votre store ralentit chaque vendredi soir. Corrélation : promos activent un popup de 500KB." |
| **Visual Store Test** | Playwright + Mem0 | Diff visuel screenshots entre scans. "Hero banner décalé de 120px après update Reviews+." |
| **Real User Simulation** | Playwright + Celery | Parcours achat réel. "14.2s total. Bottleneck : page produit (6.1s). Cause : popup Privy 340KB." |
| **Accessibility Live Test** | Playwright + WCAG | WCAG vérifié en rendu réel. Boutons cliquables ? Contraste OK ? Navigation clavier ? |

---

## DEPLOY — RAILWAY + VERCEL

### Railway (Backend)

2 services, même repo, Dockerfiles différents :

```dockerfile
# Dockerfile (API)
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Dockerfile.worker (Celery)
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Playwright pour browser automation
RUN pip install playwright && playwright install chromium --with-deps
COPY . .
CMD ["celery", "-A", "tasks.celery_app", "worker", "--beat", "--loglevel=info"]
```

Redis : Railway managed add-on (même project, accessible via `REDIS_URL`).

### Vercel (Frontend)

Next.js auto-deploy depuis GitHub.

```javascript
// next.config.js
module.exports = {
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1/:path*`,
      },
    ];
  },
};
```

### Supabase

Projet Supabase séparé. Connection string dans env vars Railway. Migrations manuelles (`database/migrations/`).

---

## INJECTION DE DÉPENDANCES

Toutes les dépendances sont injectées via FastAPI `Depends()`. Pas de singletons globaux, pas d'import direct de clients.

```python
# app/dependencies.py

from functools import lru_cache
from app.config import Settings
from app.services.shopify import ShopifyClient
from app.services.supabase import get_supabase_client

@lru_cache
def get_settings() -> Settings:
    return Settings()

async def get_supabase() -> SupabaseClient:
    settings = get_settings()
    return get_supabase_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

async def get_shopify_client(store: Store = Depends(get_current_store)) -> ShopifyClient:
    token = decrypt_token(store.shopify_access_token_encrypted)
    return ShopifyClient(store.shopify_shop_domain, token)

async def get_scan_service(
    supabase: SupabaseClient = Depends(get_supabase),
    shopify: ShopifyClient = Depends(get_shopify_client),
) -> ScanService:
    return ScanService(supabase, shopify)
```

---

## SCALING

| Étape | Merchants | Actions |
|-------|----------|---------|
| MVP | 0-100 | 1 API instance, 1 worker, Redis Railway add-on, Supabase Free/Pro |
| Growth | 100-1000 | Scale workers horizontalement (Railway), Redis dédié, Supabase Pro |
| Scale | 1000-5000 | Workers Playwright séparés, Supabase Team, CDN pour screenshots |
| Enterprise | 5000+ | Kubernetes, multi-region, Supabase Enterprise, workers par zone |

**Règle :** ne pas optimiser prématurément. L'architecture supporte 100 merchants avec 1 worker. Scaler quand les métriques le montrent, pas avant.
