# AGENT.md — Architecture Agent IA StoreMD

> **Le cerveau de StoreMD. Comment l'agent DÉTECTE, ANALYSE, AGIT et APPREND.**
> **Pour l'orchestrateur LangGraph, voir `.claude/skills/agent-loop/SKILL.md`.**
> **Pour le pipeline de scans, voir `.claude/skills/scan-pipeline/SKILL.md`.**
> **Pour Mem0, voir `.claude/skills/mem0-integration/SKILL.md`.**

---

## POURQUOI UN AGENT, PAS UN OUTIL

La différence entre StoreMD et tous les concurrents :

| Outil passif (StoreScan, TinyIMG) | Agent IA (StoreMD) |
|-----------------------------------|--------------------|
| Le merchant lance un scan manuellement | L'agent scanne automatiquement (crons, webhooks) |
| Rapport PDF statique | Recommandations personnalisées qui s'adaptent au merchant |
| Même résultat pour tous les stores | Contexte historique (Mem0) → diagnostic personnalisé |
| Le merchant agit seul | L'agent propose des fixes 1-clic et les applique |
| Pas d'apprentissage | Ouroboros : chaque cycle améliore le suivant |
| Pas de corrélation | Cross-store intelligence ("app X pose problème sur 47 stores") |

---

## LES 4 COUCHES

```
┌────────────────────────────────────────────────────────────────┐
│                                                                 │
│   COUCHE 1 — DÉTECTER                                          │
│                                                                 │
│   Qu'est-ce qui déclenche l'agent ?                            │
│                                                                 │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐    │
│   │  Webhooks     │  │  Cron jobs   │  │  Action manuelle  │    │
│   │  Shopify      │  │  (Celery     │  │  (merchant clique │    │
│   │  (product     │  │   beat)      │  │   "Scan now")     │    │
│   │  create,      │  │              │  │                    │    │
│   │  theme update,│  │  Daily: Pro  │  │                    │    │
│   │  app change)  │  │  Weekly:     │  │                    │    │
│   │               │  │  Starter     │  │                    │    │
│   └──────┬───────┘  └──────┬───────┘  └────────┬───────────┘    │
│          │                 │                    │                │
│          └─────────────────┼────────────────────┘                │
│                            │                                     │
│                            ▼                                     │
│                   Celery task: run_scan()                        │
│                                                                 │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                                                                 │
│   COUCHE 2 — ANALYSER                                          │
│                                                                 │
│   Comprendre ce qui se passe avec intelligence.                │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │  2a. Charger la mémoire (Mem0)                          │  │
│   │      - Historique du merchant (préférences, feedback)    │  │
│   │      - Historique du store (baseline score, apps connues)│  │
│   │      - Intelligence cross-store (app X problématique)   │  │
│   └──────────────────────┬──────────────────────────────────┘  │
│                          │                                      │
│   ┌──────────────────────▼──────────────────────────────────┐  │
│   │  2b. Exécuter les scanners (18 scanners, 3 groupes)     │  │
│   │      - Groupe 1: Shopify API (parallèle, semaphore 4)   │  │
│   │      - Groupe 2: External checks (parallèle)            │  │
│   │      - Groupe 3: Browser automation (séquentiel, Pro)    │  │
│   └──────────────────────┬──────────────────────────────────┘  │
│                          │                                      │
│   ┌──────────────────────▼──────────────────────────────────┐  │
│   │  2c. Interpréter (Claude API)                            │  │
│   │      - Résultats scanners + contexte Mem0                │  │
│   │      - Score composite pondéré                           │  │
│   │      - Issues priorisées par impact                      │  │
│   │      - Analyse personnalisée basée sur l'historique      │  │
│   └──────────────────────┬──────────────────────────────────┘  │
│                          │                                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                                                                 │
│   COUCHE 3 — AGIR                                              │
│                                                                 │
│   L'agent ne se contente pas de diagnostiquer. Il AGIT.        │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │  3a. Générer les recommandations (Claude API)            │  │
│   │      - Langage simple, pas technique                     │  │
│   │      - 3 niveaux: one_click, manual, developer           │  │
│   │      - Adaptées aux préférences merchant (Mem0)          │  │
│   └──────────────────────┬──────────────────────────────────┘  │
│                          │                                      │
│   ┌──────────────────────▼──────────────────────────────────┐  │
│   │  3b. Notifier (si nécessaire)                            │  │
│   │      - Push PWA (urgent: score drop, critical issue)     │  │
│   │      - Email (hebdo: weekly report)                      │  │
│   │      - In-app banner (quand le merchant ouvre le dash)   │  │
│   │      - Max 3 push/semaine (anti-spam)                    │  │
│   └──────────────────────┬──────────────────────────────────┘  │
│                          │                                      │
│   ┌──────────────────────▼──────────────────────────────────┐  │
│   │  3c. One-Click Fix (si auto_fixable)                     │  │
│   │      - Preview avant/après                               │  │
│   │      - Merchant approuve                                 │  │
│   │      - Agent applique via Shopify API write              │  │
│   │      - Snapshot before_state pour revert                 │  │
│   └──────────────────────┬──────────────────────────────────┘  │
│                          │                                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                                                                 │
│   COUCHE 4 — APPRENDRE (Ouroboros)                             │
│                                                                 │
│   Chaque interaction rend l'agent MEILLEUR.                    │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │  4a. Feedback merchant                                   │  │
│   │      - Accept: "Applied the fix" → Mem0 stocke           │  │
│   │      - Reject: "Not relevant" / "Too risky" → Mem0       │  │
│   └──────────────────────┬──────────────────────────────────┘  │
│                          │                                      │
│   ┌──────────────────────▼──────────────────────────────────┐  │
│   │  4b. Pattern detection (tous les 10 feedbacks)           │  │
│   │      - Taux d'acceptation par type de recommandation     │  │
│   │      - "Ce merchant refuse les uninstalls (80% reject)"  │  │
│   │      - "Ce merchant accepte les alt text fixes (95%)"    │  │
│   └──────────────────────┬──────────────────────────────────┘  │
│                          │                                      │
│   ┌──────────────────────▼──────────────────────────────────┐  │
│   │  4c. Adaptation                                          │  │
│   │      - Prioriser les types acceptés                      │  │
│   │      - Dé-prioriser les types refusés                    │  │
│   │      - Ajuster le ton des recommandations                │  │
│   │      - Objectif: >80% acceptance rate après 50 feedbacks │  │
│   └──────────────────────┬──────────────────────────────────┘  │
│                          │                                      │
│   ┌──────────────────────▼──────────────────────────────────┐  │
│   │  4d. Cross-store intelligence                            │  │
│   │      - "App X caused regression on 47 stores"            │  │
│   │      - Alerte proactive aux stores qui ont app X         │  │
│   │      - L'agent global apprend des patterns               │  │
│   └─────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## TRIGGERS — CE QUI DÉCLENCHE L'AGENT

### Webhooks Shopify → scan ciblé

| Webhook | Action agent |
|---------|-------------|
| `products/create` | Analyse listing + agentic check du nouveau produit (Starter+) |
| `products/update` | Re-check agentic readiness si metafields changés (Pro+) |
| `themes/update` | Backup collections + rescan health rapide (Pro+) |
| `app_subscriptions/update` | Vérifier ghost billing |

Les webhooks déclenchent des scans **ciblés** (pas un scan complet) :

```python
# Webhook products/create → scan ciblé sur 1 produit
async def handle_product_created(shop: str, payload: dict):
    # Pas un full scan — juste ce produit
    analyze_new_product.delay(store_id, payload["admin_graphql_api_id"])
```

### Cron (Celery beat) → scan complet planifié

| Schedule | Plan | Modules |
|----------|------|---------|
| Lundi 4 AM UTC | Starter | health |
| Daily 3 AM UTC | Pro | health, listings, agentic, compliance, browser |
| Daily 3 AM UTC × 10 stores | Agency | idem Pro, pour chaque store |

### Manuel → scan complet à la demande

Le merchant clique "Scan now" dans le dashboard → `POST /api/v1/stores/{store_id}/scans`.

---

## CLAUDE API — UTILISATION

### Quand Claude API est appelé

Claude API est appelé à **2 moments** dans le pipeline, jamais dans les scanners :

| Moment | Node LangGraph | Objectif | Input |
|--------|---------------|----------|-------|
| **Analyse** | `analyze` | Interpréter les résultats avec le contexte | Scanner results + Mem0 context |
| **Génération de fixes** | `generate_fixes` | Recommandations en langage simple | Issues + merchant preferences |

### Prompt — Analyse

```python
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

MERCHANT HISTORY (from memory — what you know about this merchant):
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
```

### Prompt — Fix Generation

```python
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
```

### Configuration Claude API

```python
# app/services/claude.py

import anthropic

client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

async def claude_analyze(prompt: str) -> str:
    """Appelle Claude API pour l'analyse du scan."""
    try:
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            temperature=0.3,       # Low temperature pour l'analyse (factuel)
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    except anthropic.RateLimitError:
        raise AgentError(
            code=ErrorCode.CLAUDE_API_RATE_LIMIT,
            message="Claude API rate limited",
            status_code=429,
        )
    except anthropic.APITimeoutError:
        raise AgentError(
            code=ErrorCode.CLAUDE_API_TIMEOUT,
            message="Claude API timeout",
            status_code=504,
        )
    except anthropic.APIError as exc:
        raise AgentError(
            code=ErrorCode.CLAUDE_API_ERROR,
            message=f"Claude API error: {str(exc)}",
            status_code=502,
        )


async def claude_generate_fix(prompt: str) -> str:
    """Appelle Claude API pour la génération de fix."""
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        temperature=0.5,       # Un peu plus créatif pour les recommandations
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
```

### Coûts estimés

| Opération | Tokens input | Tokens output | Coût estimé |
|-----------|-------------|---------------|-------------|
| Analyse scan (health only) | ~3,000 | ~1,000 | ~$0.012 |
| Analyse scan (tous modules) | ~8,000 | ~2,000 | ~$0.030 |
| Fix generation (par issue) | ~500 | ~200 | ~$0.002 |
| Scan complet (analyse + 5 fixes) | ~10,000 | ~3,000 | ~$0.040 |

**Coût moyen par scan : ~$0.02-$0.04.** À $99/mois (Pro), avec 30 scans/mois = $0.60-$1.20 de coûts Claude API. Marge >98%.

### Fallback sans Claude API

Si Claude API est down ou timeout :

```python
async def analyze_fallback(scanner_results: dict) -> AnalysisResult:
    """Analyse rules-based quand Claude API est indisponible.
    
    Moins précis mais fonctionnel : le merchant a quand même son score et ses issues.
    Pas de recommandations en langage naturel, juste les données brutes.
    """
    score = calculate_score_rules_based(scanner_results)
    issues = extract_issues_from_results(scanner_results)

    # Trier par impact_value décroissant
    issues.sort(key=lambda i: i.impact_value or 0, reverse=True)

    return AnalysisResult(
        score=score,
        issues=issues,
        summary="Automated analysis (AI temporarily unavailable)",
        trend=calculate_trend_from_history(store_id),
    )
```

---

## SCORE COMPOSITE — CALCUL

### Pondération

```python
SCORE_WEIGHTS = {
    "mobile_speed": 0.30,      # PageSpeed + Playwright timing
    "desktop_speed": 0.20,     # PageSpeed
    "app_impact": 0.20,        # Total app impact en ms
    "code_quality": 0.15,      # Résidus, code weight, ghost billing
    "seo_basics": 0.15,        # Pixel health, alt text, meta tags
}
```

### Calcul rules-based (fallback)

```python
def calculate_score_rules_based(results: dict) -> int:
    """Score /100 basé sur les résultats des scanners, sans Claude API."""
    scores = {}

    # Mobile speed (0-100 basé sur les timing Playwright ou PageSpeed)
    if "real_user_simulation" in results:
        total_ms = results["real_user_simulation"].metrics.get("total_time_ms", 0)
        # <5s = 100, 5-10s = 50-100, 10-20s = 0-50, >20s = 0
        scores["mobile_speed"] = max(0, min(100, int(100 - (total_ms - 5000) / 150)))
    elif "health_scorer" in results:
        scores["mobile_speed"] = results["health_scorer"].metrics.get("mobile_score", 50)

    # Desktop speed
    if "health_scorer" in results:
        scores["desktop_speed"] = results["health_scorer"].metrics.get("desktop_score", 50)

    # App impact
    if "app_impact" in results:
        total_impact_ms = results["app_impact"].metrics.get("total_impact_ms", 0)
        # 0ms = 100, 1000ms = 70, 2000ms = 40, 3000ms+ = 10
        scores["app_impact"] = max(10, min(100, int(100 - total_impact_ms / 30)))

    # Code quality
    code_issues = 0
    if "residue_detector" in results:
        code_issues += len(results["residue_detector"].issues)
    if "ghost_billing" in results:
        code_issues += len(results["ghost_billing"].issues)
    if "code_weight" in results:
        total_kb = results["code_weight"].metrics.get("total_js_kb", 0)
        if total_kb > 1000:
            code_issues += 2
    scores["code_quality"] = max(0, 100 - code_issues * 15)

    # SEO basics
    seo_issues = 0
    if "pixel_health" in results:
        seo_issues += sum(1 for i in results["pixel_health"].issues
                          if i.severity in ("critical", "major"))
    if "listing_analyzer" in results:
        avg_score = results["listing_analyzer"].metrics.get("avg_score", 50)
        scores["seo_basics"] = avg_score
    else:
        scores["seo_basics"] = max(0, 100 - seo_issues * 20)

    # Composite
    total = 0
    for key, weight in SCORE_WEIGHTS.items():
        total += scores.get(key, 50) * weight

    return round(total)
```

### Baseline adaptative (Mem0)

Le score est comparé à la baseline PERSONNALISÉE du store :

```python
async def detect_score_drop(state: AgentState) -> bool:
    """Détecte un score drop par rapport à la baseline du store."""
    # Chercher la baseline dans les mémoires store
    for mem in state.historical_context:
        content = str(mem.get("memory", mem.get("content", "")))
        if "Score:" in content:
            # Extraire le score précédent
            # Ex: "Scan completed. Score: 67 (mobile: 52, desktop: 81)."
            match = re.search(r"Score:\s*(\d+)", content)
            if match:
                previous_score = int(match.group(1))
                drop = previous_score - state.score
                # Seuil par défaut : -5 points (configurable par le merchant)
                threshold = state.merchant_preferences.get("alert_threshold", 5)
                return drop >= threshold
    return False
```

---

## NOTIFICATIONS — LA VOIX DE L'AGENT

### Canaux

| Canal | Quand | Exemples |
|-------|-------|---------|
| **Push PWA** | Urgent : score drop, critical issue, app update | "Your mobile score dropped 5 points. Reviews+ updated 2h ago." |
| **Email** | Hebdomadaire : weekly report, digest | "Weekly Health Report: Score 67 (+9). 2 issues resolved." |
| **In-app banner** | Quand le merchant ouvre le dashboard | "New: Your store is 34% ready for ChatGPT Shopping." |

### Règles anti-spam

```python
MAX_PUSH_PER_WEEK = 3  # Configurable par le merchant (default 3)

async def can_notify(merchant_id: str, channel: str = "push") -> bool:
    """Vérifie que le merchant n'a pas atteint sa limite de notifications."""
    if channel != "push":
        return True  # Pas de limite sur email et in-app

    week_start = datetime.now(UTC) - timedelta(days=7)
    result = await supabase.table("notifications").select("id", count="exact").eq(
        "merchant_id", merchant_id
    ).eq("channel", "push").gte(
        "sent_at", week_start.isoformat()
    ).execute()

    max_per_week = await get_merchant_notification_limit(merchant_id)
    return result.count < max_per_week
```

### Contenu des notifications

```python
def format_score_drop_notification(
    previous_score: int, current_score: int, probable_cause: str
) -> dict:
    return {
        "title": f"Score dropped {previous_score - current_score} points",
        "body": (
            f"Your health score went from {previous_score} to {current_score}. "
            f"Probable cause: {probable_cause}."
        ),
        "action_url": "/dashboard/health",
        "category": "score_drop",
    }

def format_weekly_report_notification(
    score: int, delta: int, resolved: int, new_issues: int
) -> dict:
    trend = f"+{delta}" if delta > 0 else str(delta)
    return {
        "title": f"Weekly Report: Score {score} ({trend})",
        "body": (
            f"{resolved} issues resolved, {new_issues} new. "
            f"Open your dashboard for details."
        ),
        "action_url": "/dashboard/health",
        "category": "weekly_report",
    }
```

Chaque notification inclut TOUJOURS :
- Le problème (quoi)
- Le diagnostic (pourquoi)
- L'action à prendre (comment)
- Un lien direct vers le dashboard (où)

JAMAIS de notification pour demander une review ou un upgrade.

---

## BACKGROUND PROCESSING — ENTRE LES SCANS

### Trend analysis (Celery periodic task)

```python
@celery.task
async def run_cross_store_analysis():
    """Daily 5 AM — analyse les tendances cross-store."""
    # 1. Identifier les apps qui ont causé des régressions
    #    sur plusieurs stores dans les dernières 24h
    recent_scans = await get_scans_last_24h()

    app_regressions: dict[str, int] = {}
    for scan in recent_scans:
        for issue in scan.issues:
            if issue.scanner == "app_impact" and issue.severity == "critical":
                app_name = issue.context.get("app_name", "unknown")
                app_regressions[app_name] = app_regressions.get(app_name, 0) + 1

    # 2. Si une app cause des problèmes sur 5+ stores → signal cross-store
    memory = StoreMemory()
    for app_name, count in app_regressions.items():
        if count >= 5:
            await memory.signal_cross_store(
                f"App '{app_name}' caused critical issues on {count} stores "
                f"in the last 24h. Likely related to a recent update."
            )
            logger.info("cross_store_signal", app=app_name, affected_stores=count)

    # 3. Identifier les patterns temporels
    #    (ex: dégradation récurrente le week-end)
    # ... (analyse plus complexe, itération future)
```

### Proactive alerts (background consciousness)

```python
@celery.task
async def check_proactive_alerts():
    """Toutes les 6h — vérifier s'il faut alerter proactivement."""
    pro_stores = await get_stores_by_plan(["pro", "agency"])

    for store in pro_stores:
        # Comparer les derniers scans pour détecter une tendance
        scores = await get_recent_scores(store["id"], days=7)

        if len(scores) >= 3:
            # Tendance négative sur 3 scans consécutifs
            if all(scores[i] > scores[i+1] for i in range(min(3, len(scores)-1))):
                total_drop = scores[0] - scores[-1]
                if total_drop >= 5:
                    await send_proactive_alert(
                        store["merchant_id"],
                        store["id"],
                        f"Your score has been declining for {len(scores)} days "
                        f"(from {scores[0]} to {scores[-1]}). "
                        f"Check your recent app changes.",
                    )
```

---

## FEATURES EXCLUSIVES — IMPOSSIBLES SANS L'ARCHITECTURE

| Feature | Couche requise | Pourquoi aucun concurrent ne peut copier |
|---------|---------------|----------------------------------------|
| **Adaptive Health Score** | Mem0 merchant memory | Le score s'adapte à la baseline du store. Seuils personnalisés. |
| **Smart Fix Prioritization** | Mem0 feedback + Ouroboros | Fixes priorisés par probabilité d'acceptation par CE merchant. |
| **App Risk Prediction** | Mem0 cross-store + trend analysis | "App X a causé des régressions sur 47 stores après sa mise à jour." |
| **Weekend Degradation Detector** | Mem0 temporal patterns | "Votre store ralentit chaque vendredi soir. Corrélation : promos." |
| **Visual Store Test** | Playwright + Mem0 | Diff visuel entre scans, corrélation avec app updates. |
| **Real User Simulation** | Playwright + Celery | Parcours achat réel, bottleneck identifié avec cause. |
| **Self-improving recommendations** | Ouroboros | Taux d'acceptation >80% après 50 feedbacks. |

### Temps pour un concurrent de rattraper

| Composant | Temps estimé |
|-----------|-------------|
| Reconstruire Mem0 + LangGraph | 3-6 mois |
| Accumuler des données merchant (calibrer les baselines) | 6 mois incompressible |
| Construire la cross-store intelligence (masse critique) | 12 mois |
| Implémenter et calibrer Ouroboros | 2-3 mois + données |
| Obtenir "Built for Shopify" | 1-3 mois |
| **Total** | **12-18 mois de retard** |

---

## FICHIERS DU MODULE AGENT

```
backend/app/agent/
├── orchestrator.py              # LangGraph state machine (7 nodes)
├── state.py                     # AgentState dataclass
├── memory.py                    # StoreMemory — Mem0 client wrapper
├── learner.py                   # OuroborosLearner — couche LEARN
│
├── detectors/
│   ├── webhook_handler.py       # Shopify events → trigger scan ciblé
│   ├── cron_scanner.py          # Scans planifiés (Celery beat)
│   └── realtime_monitor.py      # App updates, permission changes
│
├── analyzers/
│   ├── base.py                  # BaseScanner ABC
│   ├── health_scorer.py         # Score /100 composite
│   ├── app_impact.py            # Impact chaque app
│   ├── bot_traffic.py           # Bot filter + AI crawlers
│   ├── residue_detector.py      # Code mort apps désinstallées
│   ├── ghost_billing.py         # Facturation fantôme
│   ├── code_weight.py           # Poids JS/CSS par source
│   ├── security_monitor.py      # SSL, headers, permissions
│   ├── pixel_health.py          # GA4, Meta, TikTok Pixel
│   ├── email_health.py          # SPF, DKIM, DMARC
│   ├── broken_links.py          # Liens cassés
│   ├── listing_analyzer.py      # Score /100 par listing
│   ├── agentic_readiness.py     # Compatibilité ChatGPT/Copilot
│   ├── hs_code_validator.py     # Validation HS codes
│   ├── accessibility.py         # WCAG 2.1 statique
│   ├── benchmark.py             # Benchmark vs stores similaires
│   ├── content_theft.py         # Copie contenu (Phase 2)
│   └── trend_analyzer.py        # Tendances inter-scans
│
├── actors/
│   ├── notification.py          # Push + email + in-app
│   ├── fix_generator.py         # Claude API → recommandations
│   ├── one_click_fixer.py       # Appliquer fixes via Shopify API
│   └── report_generator.py      # Weekly report HTML + PDF
│
└── browser/
    ├── base.py                  # BaseBrowserScanner (Playwright lifecycle)
    ├── visual_store_test.py     # Screenshots + diff
    ├── real_user_simulation.py  # Parcours achat complet
    └── accessibility_live.py    # WCAG rendu réel

backend/tasks/
├── celery_app.py                # Config + beat schedule
├── scan_tasks.py                # run_scan, run_scheduled_scans
├── browser_tasks.py             # Tasks Playwright spécifiques
└── report_tasks.py              # send_weekly_reports

backend/app/services/
└── claude.py                    # Claude API client (analyze + generate_fix)
```

---

## INTERDICTIONS

- ❌ Appeler Claude API dans un scanner → ✅ Claude dans les nodes `analyze` et `generate_fixes` uniquement
- ❌ Stocker le prompt Claude en DB → ✅ Stocker le résultat (score, issues), pas le prompt
- ❌ Scanner qui écrit en DB → ✅ Retourner ScannerResult, le node `save_results` persiste
- ❌ Notification sans vérifier la limite hebdo → ✅ `can_notify()` avant chaque push
- ❌ Notification pour demander une review/upgrade → ✅ Notifications = problèmes + diagnostics + actions
- ❌ Fix appliqué sans approbation merchant → ✅ Preview + approve TOUJOURS
- ❌ Agent qui modifie son propre code (Ouroboros ≠ auto-modification) → ✅ Ouroboros = feedback loop dans Mem0
- ❌ Ignorer les erreurs Claude API (scan fail) → ✅ Fallback rules-based, scan continue
- ❌ Envoyer le token Shopify à Claude API → ✅ JAMAIS de secrets dans les prompts
