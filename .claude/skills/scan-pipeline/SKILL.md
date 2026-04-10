# Skill: Agent Loop

> **Utilise ce skill quand tu travailles sur l'agent IA :**
> **Ajouter/modifier un scanner, comprendre le pipeline DETECT→ANALYZE→ACT→LEARN,
> modifier l'orchestrateur LangGraph, toucher au feedback loop Ouroboros.**

---

## QUAND UTILISER

- Ajouter un nouveau node dans le graph LangGraph
- Modifier le flow de l'orchestrateur
- Comprendre comment un scan s'exécute de bout en bout
- Implémenter la couche LEARN (feedback)
- Débugger un scan qui échoue dans le pipeline
- Intégrer un nouveau scanner dans le flow

---

## LES 4 COUCHES

```
1. DETECT   → Quelque chose se passe (webhook, cron, action manuelle)
2. ANALYZE  → L'agent comprend ce qui se passe (scanners + Claude API + Mem0)
3. ACT      → L'agent fait quelque chose (notifications, fixes, reports)
4. LEARN    → L'agent s'améliore (feedback merchant → Mem0 → Ouroboros)
```

Ce n'est PAS un flow linéaire simple. C'est un graph LangGraph avec des nodes et des edges conditionnels.

---

## GRAPH LANGGRAPH — FLOW COMPLET

```
START
  │
  ▼
[detect]          Identifier le trigger, charger les données de base du store
  │
  ▼
[load_memory]     Récupérer le contexte Mem0 (prefs merchant, historique, cross-store)
  │
  ▼
[run_scanners]    Exécuter les analyzers selon les modules demandés (parallel groups)
  │
  ▼
[analyze]         Claude API interprète les résultats avec le contexte Mem0
  │
  ▼
[generate_fixes]  Claude API génère les recommandations en langage simple
  │
  ▼
[should_notify]   Conditionnel : y a-t-il des issues critiques ou un score drop ?
  │                     │
  ├─ OUI ──────► [notify]     Envoyer push/email/in-app
  │                     │
  ├─ NON ──────────────►│
  │                     │
  ▼                     ▼
[save_results]    Persister scan + issues + score en DB
  │
  ▼
END
```

### Implémentation

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
        self.scanners = ScannerRegistry()

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

        # Conditionnel : notifier seulement si nécessaire
        graph.add_conditional_edges(
            "generate_fixes",
            self.should_notify,
            {"notify": "notify", "skip": "save_results"},
        )
        graph.add_edge("notify", "save_results")
        graph.add_edge("save_results", END)

        return graph.compile()

    # --- NODES ---

    async def detect(self, state: AgentState) -> AgentState:
        """Couche 1 — DETECT. Charger les données de base du store."""
        store = await self.supabase.table("stores").select("*").eq(
            "id", state.store_id
        ).single().execute()
        state.store_data = store.data
        logger.info("detect", store_id=state.store_id, trigger=state.trigger,
                     modules=state.modules)
        return state

    async def load_memory(self, state: AgentState) -> AgentState:
        """Charger le contexte Mem0 avant l'analyse."""
        try:
            state.historical_context = await self.memory.recall(
                state.merchant_id,
                f"store health scan {' '.join(state.modules)}",
            )
            state.merchant_preferences = await self.memory.recall(
                state.merchant_id,
                "preferences accepted rejected recommendation patterns",
            )
            state.cross_store_signals = await self.memory.recall_cross_store(
                "app risks alerts global patterns",
            )
        except Exception as exc:
            # Mem0 down → continuer sans mémoire (graceful degradation)
            logger.warning("mem0_unavailable", error=str(exc))
            state.errors.append(f"Mem0 unavailable: {exc}")
        return state

    async def run_scanners(self, state: AgentState) -> AgentState:
        """Couche 2a — Exécuter les scanners par groupe."""
        plan = await self.get_merchant_plan(state.merchant_id)

        for scanner in self.scanners.get_for_modules(state.modules):
            if not await scanner.should_run(state.modules, plan):
                continue
            try:
                result = await scanner.scan(
                    state.store_id, self.shopify, state.historical_context
                )
                state.scanner_results[scanner.name] = result
            except Exception as exc:
                logger.warning("scanner_failed", scanner=scanner.name, error=str(exc))
                state.errors.append(f"Scanner {scanner.name}: {exc}")
                # Continuer — un scanner qui échoue ne bloque pas les autres
        return state

    async def analyze(self, state: AgentState) -> AgentState:
        """Couche 2b — Claude API interprète les résultats."""
        prompt = self.build_analysis_prompt(state)
        try:
            response = await claude_analyze(prompt)
            state.analysis_text = response
            state.score = self.calculate_composite_score(state.scanner_results)
            state.mobile_score = self.extract_mobile_score(state.scanner_results)
            state.desktop_score = self.extract_desktop_score(state.scanner_results)
            state.issues = self.extract_issues(state.scanner_results)
        except AgentError as exc:
            logger.error("claude_analysis_failed", error=str(exc))
            # Fallback : score rules-based sans Claude
            state.score = self.calculate_score_fallback(state.scanner_results)
            state.issues = self.extract_issues(state.scanner_results)
            state.errors.append(f"Claude API: {exc}")
        return state

    async def generate_fixes(self, state: AgentState) -> AgentState:
        """Couche 3a — Générer les recommandations."""
        for issue in state.issues:
            try:
                fix = await self.generate_fix_for_issue(issue, state)
                state.fixes.append(fix)
            except Exception as exc:
                logger.warning("fix_generation_failed", issue=issue.title, error=str(exc))
        return state

    def should_notify(self, state: AgentState) -> str:
        """Conditionnel : notifier si issues critiques ou score drop."""
        has_critical = any(i.severity == "critical" for i in state.issues)
        # Score drop détecté via la baseline Mem0
        score_dropped = self.detect_score_drop(state)
        if has_critical or score_dropped:
            return "notify"
        return "skip"

    async def notify(self, state: AgentState) -> AgentState:
        """Couche 3b — Envoyer les notifications."""
        # Respecter la limite de notifications par semaine
        if await self.can_notify(state.merchant_id):
            await self.send_notifications(state)
            state.notifications_sent.append("push")
        return state

    async def save_results(self, state: AgentState) -> AgentState:
        """Persister les résultats en DB."""
        await self.update_scan_record(state)
        await self.insert_issues(state)
        await self.insert_fixes(state)
        # Mettre à jour la baseline dans Mem0
        await self.memory.remember(
            state.merchant_id,
            f"Scan completed. Score: {state.score}. "
            f"Issues: {len(state.issues)} ({state.issues_critical_count} critical). "
            f"Modules: {state.modules}.",
        )
        return state
```

---

## SCANNER REGISTRY

Le registre centralise tous les scanners et les organise par module :

```python
# app/agent/analyzers/__init__.py

from app.agent.analyzers.base import BaseScanner
from app.agent.analyzers.health_scorer import HealthScorer
from app.agent.analyzers.app_impact import AppImpactScanner
from app.agent.analyzers.bot_traffic import BotTrafficScanner
# ... tous les scanners

class ScannerRegistry:
    """Registre de tous les scanners disponibles."""

    def __init__(self):
        self._scanners: list[BaseScanner] = [
            # Module Health
            HealthScorer(),
            AppImpactScanner(),
            BotTrafficScanner(),
            ResidueDetector(),
            GhostBillingDetector(),
            CodeWeightScanner(),
            SecurityMonitor(),
            PixelHealthScanner(),
            EmailHealthScanner(),
            TrendAnalyzer(),

            # Module Listings
            ListingAnalyzer(),

            # Module Agentic
            AgenticReadinessScanner(),
            HSCodeValidator(),

            # Module Compliance
            AccessibilityScanner(),
            BrokenLinksScanner(),

            # Module Browser (Pro only, séquentiel)
            VisualStoreTest(),
            RealUserSimulation(),
            AccessibilityLiveTest(),
        ]

    def get_for_modules(self, modules: list[str]) -> list[BaseScanner]:
        """Retourne les scanners pour les modules demandés, triés par groupe."""
        return [s for s in self._scanners if s.module in modules]

    def get_by_name(self, name: str) -> BaseScanner | None:
        return next((s for s in self._scanners if s.name == name), None)
```

---

## CLAUDE API ANALYSIS — PROMPT PATTERN

```python
def build_analysis_prompt(self, state: AgentState) -> str:
    return f"""You are StoreMD, an AI agent that diagnoses Shopify store health.

STORE: {state.store_data.get('name')} ({state.store_data.get('shopify_shop_domain')})
THEME: {state.store_data.get('theme_name')}
APPS: {state.store_data.get('apps_count')} installed
PRODUCTS: {state.store_data.get('products_count')}

SCAN RESULTS:
{json.dumps(state.scanner_results, indent=2, default=str)}

MERCHANT HISTORY (from memory):
{json.dumps(state.historical_context, indent=2, default=str)}

MERCHANT PREFERENCES:
{json.dumps(state.merchant_preferences, indent=2, default=str)}

INSTRUCTIONS:
1. Analyze the scan results in context of the merchant's history and preferences.
2. Identify the top 3 most impactful issues.
3. For each issue, provide a clear recommendation in simple language.
4. If the merchant has previously rejected similar recommendations, suggest alternatives.
5. Note any trends (improving, degrading, stable) based on historical data.
6. Keep recommendations actionable — what to do, not what to learn.

Respond in JSON format:
{{
  "summary": "One paragraph overall health assessment",
  "trend": "up|down|stable",
  "top_issues": [
    {{
      "title": "...",
      "severity": "critical|major|minor",
      "impact": "...",
      "recommendation": "...",
      "fix_type": "one_click|manual|developer"
    }}
  ]
}}"""
```

---

## COUCHE LEARN — OUROBOROS

Le feedback est déclenché par le merchant dans le frontend (accept/reject sur chaque issue).

```python
# app/agent/learner.py

class OuroborosLearner:
    def __init__(self, memory: StoreMemory):
        self.memory = memory

    async def process_feedback(
        self, merchant_id: str, issue_id: str,
        accepted: bool, reason: str | None = None,
        reason_category: str | None = None,
    ):
        # 1. Stocker en DB (table feedback)
        await self.save_feedback(merchant_id, issue_id, accepted, reason, reason_category)

        # 2. Stocker dans Mem0 (pour le contexte du prochain scan)
        issue = await self.get_issue(issue_id)
        context = (
            f"Recommendation '{issue.title}' (type: {issue.scanner}, "
            f"severity: {issue.severity}): "
        )
        if accepted:
            context += "ACCEPTED by merchant."
        else:
            context += f"REJECTED by merchant. Reason: {reason or reason_category or 'unknown'}."

        await self.memory.remember(merchant_id, context)

        # 3. Vérifier si un pattern émerge
        feedback_count = await self.get_feedback_count(merchant_id)
        if feedback_count >= 10 and feedback_count % 10 == 0:
            await self.analyze_patterns(merchant_id)

    async def analyze_patterns(self, merchant_id: str):
        """Tous les 10 feedbacks, analyser les patterns."""
        feedbacks = await self.get_recent_feedbacks(merchant_id, limit=50)

        # Calculer le taux d'acceptation par type de recommandation
        by_type: dict[str, dict] = {}
        for fb in feedbacks:
            t = fb["recommendation_type"]
            if t not in by_type:
                by_type[t] = {"accepted": 0, "rejected": 0}
            if fb["accepted"]:
                by_type[t]["accepted"] += 1
            else:
                by_type[t]["rejected"] += 1

        # Stocker le pattern dans Mem0
        patterns = []
        for rec_type, counts in by_type.items():
            total = counts["accepted"] + counts["rejected"]
            rate = counts["accepted"] / total if total > 0 else 0
            if rate < 0.3:
                patterns.append(f"Merchant rejects '{rec_type}' recommendations (rate: {rate:.0%})")
            elif rate > 0.8:
                patterns.append(f"Merchant likes '{rec_type}' recommendations (rate: {rate:.0%})")

        if patterns:
            await self.memory.remember(
                merchant_id,
                f"Preference patterns detected: {'; '.join(patterns)}",
            )
```

---

## AJOUTER UN NOUVEAU NODE AU GRAPH

Si tu dois ajouter un node (ex: un step de validation post-scan) :

1. Créer la méthode async dans `ScanOrchestrator`
2. `graph.add_node("new_node", self.new_method)`
3. Ajouter les edges (d'où vient-on, où va-t-on)
4. Mettre à jour `AgentState` si le node produit des données
5. Tester le graph avec un state minimal

```python
# Exemple : ajouter un node de validation
graph.add_node("validate_results", self.validate_results)
graph.add_edge("run_scanners", "validate_results")
graph.add_edge("validate_results", "analyze")
```

---

## INTERDICTIONS

- ❌ Logique métier dans l'orchestrateur → ✅ Logique dans les scanners et services
- ❌ Appeler Claude API dans un scanner → ✅ Claude API dans le node `analyze` uniquement
- ❌ Scanner qui raise et bloque tout → ✅ Try/except dans `run_scanners`, continuer
- ❌ Scanner qui accède à la DB directement → ✅ Scanner reçoit `ShopifyClient`, retourne `ScannerResult`
- ❌ Notification sans vérifier la limite hebdo → ✅ `can_notify()` check avant envoi
- ❌ Sauvegarder sans Mem0 update → ✅ Toujours mettre à jour la baseline dans `save_results`
