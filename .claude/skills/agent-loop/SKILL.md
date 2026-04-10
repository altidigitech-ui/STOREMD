# Skill: Scan Pipeline

> **Utilise ce skill quand tu travailles sur l'orchestration des scans :**
> **Séquencement des scanners, parallélisme, groupes d'exécution,
> error handling scan, Celery tasks, résultats partiels.**

---

## QUAND UTILISER

- Modifier l'ordre d'exécution des scanners
- Ajouter un scanner au pipeline (voir aussi `/add-scanner` command)
- Débugger un scan qui timeout ou échoue partiellement
- Comprendre le séquencement parallel vs séquentiel
- Modifier les Celery tasks de scan

---

## ARCHITECTURE DU PIPELINE

3 groupes d'exécution, dans l'ordre :

```
TRIGGER (manual / cron / webhook)
    │
    ▼
┌──────────────────────────────────────────────┐
│ GROUPE 1 — Shopify API                       │
│ Exécution : PARALLÈLE (asyncio.gather)       │
│ Contrainte : semaphore 4 requêtes simultanées │
│ Timeout : 120s par scanner                   │
│                                               │
│ health_scorer        ─┐                       │
│ app_impact           ─┤                       │
│ residue_detector     ─┤  Tous partagent       │
│ ghost_billing        ─┤  le même              │
│ code_weight          ─┤  ShopifyClient        │
│ security_monitor     ─┤  (même token,         │
│ pixel_health         ─┤   même semaphore)     │
│ listing_analyzer     ─┤  (si module listings) │
│ agentic_readiness    ─┤  (si module agentic)  │
│ hs_code_validator    ─┘  (si module agentic)  │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│ GROUPE 2 — External checks                  │
│ Exécution : PARALLÈLE (asyncio.gather)       │
│ Contrainte : aucune (pas de rate limit)      │
│ Timeout : 60s par scanner                    │
│                                               │
│ broken_links         ─┐  HTTP HEAD requests   │
│ email_health         ─┤  DNS lookups          │
│ bot_traffic          ─┤  Log analysis         │
│ accessibility        ─┘  HTML parse statique  │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│ GROUPE 3 — Browser automation (Pro only)     │
│ Exécution : SÉQUENTIEL (un à la fois)        │
│ Contrainte : Playwright lourd, 1 browser     │
│ Timeout : 90s par scanner                    │
│                                               │
│ 1. visual_store_test     (screenshots + diff)│
│ 2. real_user_simulation  (parcours complet)  │
│ 3. accessibility_live    (WCAG rendu réel)   │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
              RÉSULTATS AGRÉGÉS
```

---

## IMPLÉMENTATION — EXÉCUTION PAR GROUPE

```python
# app/agent/orchestrator.py (node run_scanners)

import asyncio
from app.agent.analyzers.base import BaseScanner, ScannerResult

async def run_scanners(self, state: AgentState) -> AgentState:
    """Exécute les scanners par groupe : parallel API, parallel external, sequential browser."""
    plan = await self.get_merchant_plan(state.merchant_id)
    all_scanners = self.scanners.get_for_modules(state.modules)
    eligible = [s for s in all_scanners if await s.should_run(state.modules, plan)]

    # Séparer par groupe
    group_api = [s for s in eligible if s.group == "shopify_api"]
    group_ext = [s for s in eligible if s.group == "external"]
    group_browser = [s for s in eligible if s.group == "browser"]

    # Groupe 1 — Shopify API (parallèle)
    await self._run_parallel(group_api, state, timeout=120)

    # Groupe 2 — External (parallèle)
    await self._run_parallel(group_ext, state, timeout=60)

    # Groupe 3 — Browser (séquentiel, Pro only)
    await self._run_sequential(group_browser, state, timeout=90)

    return state


async def _run_parallel(
    self, scanners: list[BaseScanner], state: AgentState, timeout: int
) -> None:
    """Exécute des scanners en parallèle avec timeout individuel."""
    if not scanners:
        return

    async def run_one(scanner: BaseScanner) -> tuple[str, ScannerResult | None]:
        try:
            result = await asyncio.wait_for(
                scanner.scan(state.store_id, self.shopify, state.historical_context),
                timeout=timeout,
            )
            logger.info("scanner_completed", scanner=scanner.name,
                        issues=len(result.issues))
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
    """Exécute des scanners séquentiellement (browser automation)."""
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
```

---

## BASESCANNER — CONTRAT

Tous les scanners héritent de `BaseScanner` et implémentent `scan()` :

```python
# app/agent/analyzers/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from app.models.scan import ScanIssue

@dataclass
class ScannerResult:
    """Résultat d'un scanner individuel."""
    scanner_name: str
    issues: list[ScanIssue] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)    # données brutes (scores, counts, etc.)
    metadata: dict = field(default_factory=dict)   # debug info


class BaseScanner(ABC):
    """Classe de base pour tous les scanners StoreMD."""

    name: str          # "health_scorer", "app_impact", etc.
    module: str        # "health", "listings", "agentic", "compliance", "browser"
    group: str         # "shopify_api", "external", "browser"
    requires_plan: str # "free", "starter", "pro"

    @abstractmethod
    async def scan(
        self,
        store_id: str,
        shopify: ShopifyClient,
        memory_context: list[dict],
    ) -> ScannerResult:
        """Exécute le scan. Retourne les issues et métriques.

        RÈGLES :
        - Ne JAMAIS raise une exception qui bloque les autres scanners
        - Ne JAMAIS appeler Claude API (c'est le job du node analyze)
        - Ne JAMAIS écrire en DB (c'est le job du node save_results)
        - Ne JAMAIS envoyer de notification (c'est le job du node notify)
        - Toujours retourner un ScannerResult, même vide
        """
        ...

    async def should_run(self, modules: list[str], plan: str) -> bool:
        """Vérifie si ce scanner doit s'exécuter."""
        if self.module not in modules:
            return False
        plan_hierarchy = {"free": 0, "starter": 1, "pro": 2, "agency": 3}
        return plan_hierarchy.get(plan, 0) >= plan_hierarchy.get(self.requires_plan, 0)
```

### Exemple : implémenter un scanner

```python
# app/agent/analyzers/ghost_billing.py

class GhostBillingDetector(BaseScanner):
    name = "ghost_billing"
    module = "health"
    group = "shopify_api"
    requires_plan = "starter"

    async def scan(
        self, store_id: str, shopify: ShopifyClient, memory_context: list[dict]
    ) -> ScannerResult:
        # 1. Récupérer les charges actifs
        charges = await shopify.rest_get("recurring_application_charges")
        active_charges = [
            c for c in charges.get("recurring_application_charges", [])
            if c["status"] == "active"
        ]

        # 2. Récupérer les apps installées
        apps_data = await shopify.graphql(FETCH_APPS_QUERY)
        installed_app_names = {
            edge["node"]["app"]["title"]
            for edge in apps_data["appInstallations"]["edges"]
        }

        # 3. Comparer : charges sans app correspondante = ghost
        issues = []
        for charge in active_charges:
            if charge["name"] not in installed_app_names:
                issues.append(ScanIssue(
                    module="health",
                    scanner="ghost_billing",
                    severity="major",
                    title=f"Ghost billing: {charge['name']} (${charge['price']}/month)",
                    description=(
                        f"App '{charge['name']}' is no longer installed but still "
                        f"charging ${charge['price']}/month since {charge['created_at'][:10]}."
                    ),
                    impact=f"${charge['price']}/month lost",
                    fix_type="manual",
                    fix_description="Cancel this charge in Shopify Admin → Settings → Billing",
                    auto_fixable=False,
                    context={
                        "charge_id": charge["id"],
                        "charge_name": charge["name"],
                        "charge_amount": charge["price"],
                        "charge_since": charge["created_at"],
                    },
                ))

        return ScannerResult(
            scanner_name=self.name,
            issues=issues,
            metrics={
                "active_charges": len(active_charges),
                "ghost_charges": len(issues),
                "total_ghost_monthly": sum(
                    float(i.context["charge_amount"]) for i in issues
                ),
            },
        )
```

---

## SCAN ISSUE — FORMAT

```python
# app/models/scan.py

@dataclass
class ScanIssue:
    module: str                    # "health", "listings", etc.
    scanner: str                   # "ghost_billing", "app_impact", etc.
    severity: str                  # "critical", "major", "minor", "info"
    title: str                     # Court, descriptif
    description: str               # Détail complet
    impact: str | None = None      # "+1.8s load time", "$9.99/month lost"
    impact_value: float | None = None   # 1.8, 9.99 (pour tri)
    impact_unit: str | None = None      # "seconds", "dollars"
    fix_type: str | None = None    # "one_click", "manual", "developer"
    fix_description: str | None = None
    auto_fixable: bool = False
    context: dict = field(default_factory=dict)  # données spécifiques
```

### Severity guidelines

| Severity | Quand l'utiliser | Exemples |
|----------|-----------------|----------|
| `critical` | Impact direct sur le revenue ou la sécurité | App injecte >500KB JS, SSL expiré, ghost billing >$50/mois |
| `major` | Impact significatif sur les performances ou le SEO | Code résiduel >20KB, 10+ broken links, alt text manquant sur 50+ images |
| `minor` | Impact faible, amélioration recommandée | Headers sécurité manquants, pixel dupliqué, description produit courte |
| `info` | Information, pas un problème | AI crawler détecté, app mise à jour (pas de régression) |

---

## CELERY TASKS

```python
# tasks/scan_tasks.py

@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def run_scan(self, scan_id: str, store_id: str, modules: list[str]):
    """Task Celery principale. Appelée par le service scan."""
    try:
        # Marquer running
        update_scan_status(scan_id, "running", started_at=datetime.now(UTC))

        # Construire et exécuter le graph
        orchestrator = ScanOrchestrator(
            memory=StoreMemory(),
            shopify=get_shopify_client_for_store(store_id),
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

        # Marquer completed
        update_scan_status(
            scan_id, "completed",
            score=result.score,
            mobile_score=result.mobile_score,
            desktop_score=result.desktop_score,
            issues_count=len(result.issues),
            critical_count=sum(1 for i in result.issues if i.severity == "critical"),
            partial_scan=bool(result.errors),
            completed_at=datetime.now(UTC),
        )

    except ShopifyError as exc:
        if exc.code == ErrorCode.SHOPIFY_RATE_LIMIT:
            logger.warning("scan_retry_rate_limit", scan_id=scan_id)
            self.retry(countdown=120)
        else:
            mark_scan_failed(scan_id, str(exc), exc.code)
            raise

    except Exception as exc:
        logger.error("scan_failed", scan_id=scan_id, error=str(exc))
        mark_scan_failed(scan_id, str(exc), ErrorCode.SCAN_FAILED)
        raise


@celery.task
def run_scheduled_scans(plan: str):
    """Celery beat : déclenche les scans planifiés pour un plan donné."""
    stores = get_stores_by_plan(plan)
    for store in stores:
        modules = get_default_modules_for_plan(plan)
        scan_id = create_scan_record(store.id, store.merchant_id, modules, trigger="cron")
        run_scan.delay(scan_id, store.id, modules)
        logger.info("scheduled_scan_dispatched", store_id=store.id, plan=plan)
```

---

## RÉSULTATS PARTIELS

Si un ou plusieurs scanners échouent, le scan NE FAIL PAS. Il continue et retourne un résultat partiel.

```python
# Dans save_results
partial_scan = bool(state.errors)

# Le score est calculé uniquement sur les scanners qui ont réussi
# Les scanners manquants sont exclus du calcul (pas de pénalité)
# Le frontend affiche un warning : "Some checks could not be completed"
```

La colonne `partial_scan` (BOOLEAN) dans la table `scans` + `state.errors` (list) permettent au frontend d'afficher les scanners manquants.

---

## TIMEOUTS

| Groupe | Timeout par scanner | Timeout total estimé | Justification |
|--------|-------------------|---------------------|---------------|
| Shopify API | 120s | ~120s (parallèle) | API Shopify parfois lente sur les gros catalogues |
| External | 60s | ~60s (parallèle) | HTTP HEAD + DNS lookups |
| Browser | 90s | ~270s (séquentiel, 3 scanners) | Playwright render + navigation |
| **Total max** | | **~450s (~7.5 min)** | Worst case avec browser automation |
| **Total sans browser** | | **~180s (~3 min)** | Free/Starter plan |

Le Celery task a un hard timeout de 10 min (`task_time_limit=600`).

---

## INTERDICTIONS

- ❌ Scanner qui bloque les autres (raise non-catchée) → ✅ Try/except dans le runner
- ❌ Scanner qui appelle Claude API → ✅ Claude dans le node `analyze` uniquement
- ❌ Scanner qui écrit en DB → ✅ Retourner ScannerResult, le node `save_results` persiste
- ❌ Scanner qui envoie des notifications → ✅ Node `notify` s'en charge
- ❌ Scanner sans timeout → ✅ `asyncio.wait_for()` avec timeout par groupe
- ❌ Nouveau scanner sans l'enregistrer → ✅ Ajouter dans `ScannerRegistry.__init__`
- ❌ Scanner qui ignore `should_run()` → ✅ Toujours vérifier module + plan
