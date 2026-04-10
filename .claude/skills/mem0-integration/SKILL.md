# Skill: Mem0 Integration

> **Utilise ce skill quand tu travailles sur la mémoire de l'agent :**
> **StoreMemory client, types de mémoire, recall, store, learn,
> Ouroboros feedback loop, cross-store intelligence.**

---

## QUAND UTILISER

- Modifier `app/agent/memory.py` (StoreMemory)
- Ajouter un nouveau type de mémoire
- Injecter du contexte Mem0 dans le prompt Claude API
- Implémenter le feedback loop (couche LEARN)
- Travailler sur la cross-store intelligence
- Configurer Mem0 (hosted vs self-hosted pgvector)

---

## POURQUOI MEM0

La DB stocke des **FAITS** (scan results, scores, issues).
Mem0 stocke de l'**INTELLIGENCE** (préférences, patterns, contexte relationnel).

| Sans Mem0 | Avec Mem0 |
|-----------|----------|
| Chaque scan repart de zéro | L'agent connaît l'historique du merchant |
| Recommandations génériques | "Ce merchant refuse les uninstalls → proposer CSS fixes" |
| Score drop = alerte fixe | Score drop vs baseline PERSONNALISÉE du store |
| App update = info neutre | "Cette app a causé des régressions sur 47 stores" |

---

## 4 TYPES DE MÉMOIRE

| Type | Scope | user_id Mem0 | Exemples | TTL |
|------|-------|-------------|----------|-----|
| **Merchant Memory** | 1 merchant | `storemd:{merchant_id}` | Préférences, fixes acceptés/refusés, patterns saisonniers | Infini |
| **Store Memory** | 1 store | `storemd:store:{store_id}` | Baseline score, apps connues, thème, historique scans | Infini |
| **Cross-Store** | Global | agent_id `storemd:global` | "App X problème sur 47 stores", "pattern fraude émergent" | 90 jours |
| **Agent Memory** | L'agent | agent_id `storemd:agent` | Taux d'acceptation par type de fix, templates efficaces | Infini |

---

## CLIENT WRAPPER — StoreMemory

```python
# app/agent/memory.py

from mem0 import Memory, MemoryClient
from app.config import settings

class StoreMemory:
    """Client wrapper Mem0 pour StoreMD.
    
    Utilise MemoryClient (hosted) si MEM0_API_KEY est configuré,
    sinon Memory() (self-hosted, pgvector dans Supabase).
    """

    def __init__(self):
        if settings.MEM0_API_KEY:
            self.memory = MemoryClient(api_key=settings.MEM0_API_KEY)
        else:
            self.memory = Memory(config={
                "vector_store": {
                    "provider": "pgvector",
                    "config": {
                        "connection_string": settings.SUPABASE_DB_URL,
                        "collection_name": "storemd_memories",
                    },
                },
            })

    # ─── MERCHANT MEMORY ───

    async def remember_merchant(self, merchant_id: str, context: str):
        """Stocke un fait/préférence/pattern pour un merchant."""
        self.memory.add(
            messages=[{"role": "system", "content": context}],
            user_id=f"storemd:{merchant_id}",
            metadata={"saas": "storemd", "type": "merchant"},
        )

    async def recall_merchant(self, merchant_id: str, query: str,
                               limit: int = 10) -> list[dict]:
        """Récupère les mémoires pertinentes pour un merchant."""
        results = self.memory.search(
            query=query,
            user_id=f"storemd:{merchant_id}",
            limit=limit,
        )
        return results if isinstance(results, list) else results.get("results", [])

    # ─── STORE MEMORY ───

    async def remember_store(self, store_id: str, context: str):
        """Stocke un fait spécifique au store (baseline, thème, apps)."""
        self.memory.add(
            messages=[{"role": "system", "content": context}],
            user_id=f"storemd:store:{store_id}",
            metadata={"saas": "storemd", "type": "store"},
        )

    async def recall_store(self, store_id: str, query: str,
                            limit: int = 10) -> list[dict]:
        """Récupère les mémoires du store."""
        results = self.memory.search(
            query=query,
            user_id=f"storemd:store:{store_id}",
            limit=limit,
        )
        return results if isinstance(results, list) else results.get("results", [])

    # ─── CROSS-STORE INTELLIGENCE ───

    async def signal_cross_store(self, signal: str):
        """Intelligence cross-store (ex: app X problématique globalement)."""
        self.memory.add(
            messages=[{"role": "system", "content": signal}],
            agent_id="storemd:global",
            metadata={"saas": "storemd", "type": "cross_store"},
        )

    async def recall_cross_store(self, query: str, limit: int = 5) -> list[dict]:
        """Récupère les signaux cross-store pertinents."""
        results = self.memory.search(
            query=query,
            agent_id="storemd:global",
            limit=limit,
        )
        return results if isinstance(results, list) else results.get("results", [])

    # ─── AGENT MEMORY ───

    async def remember_agent(self, context: str):
        """Stocke un apprentissage de l'agent (meta-level)."""
        self.memory.add(
            messages=[{"role": "system", "content": context}],
            agent_id="storemd:agent",
            metadata={"saas": "storemd", "type": "agent"},
        )

    async def recall_agent(self, query: str, limit: int = 5) -> list[dict]:
        """Récupère les apprentissages de l'agent."""
        results = self.memory.search(
            query=query,
            agent_id="storemd:agent",
            limit=limit,
        )
        return results if isinstance(results, list) else results.get("results", [])

    # ─── FEEDBACK LOOP (OUROBOROS) ───

    async def learn_from_feedback(
        self, merchant_id: str, issue_title: str, scanner: str,
        severity: str, accepted: bool, reason: str | None = None,
    ):
        """Couche LEARN — le merchant accepte ou refuse une recommandation.
        
        Stocke le feedback dans la mémoire merchant pour que le prochain
        scan adapte ses recommandations.
        """
        context = f"Recommendation '{issue_title}' (scanner: {scanner}, severity: {severity}): "
        if accepted:
            context += "ACCEPTED by merchant."
        else:
            context += f"REJECTED by merchant. Reason: {reason or 'not specified'}."

        await self.remember_merchant(merchant_id, context)

    # ─── CONVENIENCE — RECALL COMPLET POUR UN SCAN ───

    async def recall_for_scan(self, merchant_id: str, store_id: str,
                               modules: list[str]) -> dict:
        """Charge tout le contexte nécessaire pour un scan.
        
        Appelé par le node load_memory de l'orchestrateur.
        Retourne un dict avec les 3 types de mémoire pertinents.
        """
        query = f"store health scan {' '.join(modules)}"

        merchant_ctx = await self.recall_merchant(merchant_id, query)
        store_ctx = await self.recall_store(store_id, query)
        cross_store_ctx = await self.recall_cross_store(
            "app risks alerts global patterns"
        )

        return {
            "merchant": merchant_ctx,
            "store": store_ctx,
            "cross_store": cross_store_ctx,
        }

    # ─── CLEANUP ───

    async def forget_merchant(self, merchant_id: str):
        """Supprime toute la mémoire d'un merchant (GDPR, uninstall)."""
        self.memory.delete_all(user_id=f"storemd:{merchant_id}")

    async def forget_store(self, store_id: str):
        """Supprime toute la mémoire d'un store."""
        self.memory.delete_all(user_id=f"storemd:store:{store_id}")
```

---

## UTILISATION DANS L'ORCHESTRATEUR

### Node load_memory

```python
async def load_memory(self, state: AgentState) -> AgentState:
    try:
        context = await self.memory.recall_for_scan(
            state.merchant_id, state.store_id, state.modules
        )
        state.historical_context = context.get("merchant", []) + context.get("store", [])
        state.merchant_preferences = context.get("merchant", [])
        state.cross_store_signals = context.get("cross_store", [])
    except Exception as exc:
        logger.warning("mem0_load_failed", error=str(exc))
        state.errors.append(f"Mem0 unavailable: {exc}")
        # Continuer sans mémoire — graceful degradation
    return state
```

### Node save_results (mise à jour baseline)

```python
async def save_results(self, state: AgentState) -> AgentState:
    # ... sauvegarder en DB ...

    # Mettre à jour la mémoire store (baseline)
    await self.memory.remember_store(
        state.store_id,
        f"Scan {state.scan_id} completed. Score: {state.score} "
        f"(mobile: {state.mobile_score}, desktop: {state.desktop_score}). "
        f"Issues: {len(state.issues)} ({sum(1 for i in state.issues if i.severity == 'critical')} critical). "
        f"Modules: {', '.join(state.modules)}. "
        f"Date: {datetime.now(UTC).isoformat()}.",
    )

    # Cross-store intelligence : si une app a causé des issues
    for issue in state.issues:
        if issue.scanner == "app_impact" and issue.severity == "critical":
            app_name = issue.context.get("app_name", "unknown")
            await self.memory.signal_cross_store(
                f"App '{app_name}' caused critical issue on store {state.store_id}: "
                f"{issue.title}. Impact: {issue.impact}.",
            )

    return state
```

---

## INJECTION DANS LE PROMPT CLAUDE

```python
def build_analysis_prompt(self, state: AgentState) -> str:
    # Formater le contexte Mem0 pour le prompt
    memory_text = ""

    if state.historical_context:
        memory_text += "MERCHANT HISTORY (from previous scans):\n"
        for mem in state.historical_context[:10]:  # Max 10 mémoires
            content = mem.get("memory", mem.get("content", str(mem)))
            memory_text += f"- {content}\n"

    if state.merchant_preferences:
        memory_text += "\nMERCHANT PREFERENCES (learned from feedback):\n"
        for mem in state.merchant_preferences[:5]:
            content = mem.get("memory", mem.get("content", str(mem)))
            memory_text += f"- {content}\n"

    if state.cross_store_signals:
        memory_text += "\nCROSS-STORE INTELLIGENCE:\n"
        for mem in state.cross_store_signals[:5]:
            content = mem.get("memory", mem.get("content", str(mem)))
            memory_text += f"- {content}\n"

    return f"""You are StoreMD, an AI agent.

SCAN RESULTS:
{json.dumps(state.scanner_results, indent=2, default=str)}

{memory_text}

Based on the scan results AND the merchant's history/preferences,
provide personalized recommendations.
If the merchant has rejected similar recommendations before,
suggest alternatives.
"""
```

---

## CE QUE L'AGENT RETIENT

### Après chaque scan

```python
# Baseline score
"Scan completed. Score: 67 (mobile: 52, desktop: 81). Issues: 5 (1 critical)."

# Apps détectées
"Store has 14 apps. Top impact: Privy (1.8s), Klaviyo (0.9s), Reviews+ (0.5s)."

# Thème
"Store uses Dawn 15.0 theme."
```

### Après chaque feedback

```python
# Accepted
"Recommendation 'Remove Privy residual code' (scanner: residue_detector): ACCEPTED."

# Rejected
"Recommendation 'Uninstall Privy' (scanner: app_impact): REJECTED. Reason: need it for popups."
```

### Cross-store (automatique)

```python
# App risk
"App 'Reviews+' caused critical issue on 3 stores after v3.2 update: CLS increased."
```

---

## CONFIGURATION

### Hosted (recommandé pour démarrer)

```bash
# .env
MEM0_API_KEY=m0-xxx
```

Avantages : pas d'infra à gérer, search optimisé, scaling automatique.

### Self-hosted (pgvector dans Supabase)

```bash
# .env
MEM0_API_KEY=          # laisser vide → self-hosted mode
SUPABASE_DB_URL=postgresql://postgres:xxx@db.xxx.supabase.co:5432/postgres
```

Nécessite l'extension `vector` activée dans Supabase (déjà dans DATABASE.md).
Avantages : données restent dans Supabase, pas de coût Mem0.

---

## GRACEFUL DEGRADATION

Mem0 peut être down ou lent. L'agent DOIT continuer sans mémoire.

```python
# Pattern dans chaque appel Mem0
try:
    memories = await self.memory.recall_merchant(merchant_id, query)
except Exception as exc:
    logger.warning("mem0_error", operation="recall", error=str(exc))
    memories = []  # Continuer sans mémoire
```

| Mem0 status | Comportement agent |
|-------------|-------------------|
| Healthy | Recommandations personnalisées, baseline adaptative |
| Down | Recommandations génériques, seuils par défaut, scan continue |
| Slow (>5s) | Timeout, même comportement que "down" |
| Partial (recall OK, store fail) | Recommandations personnalisées, pas de mise à jour mémoire |

---

## GDPR — CLEANUP

Quand un merchant désinstalle l'app :

```python
async def handle_merchant_uninstall(merchant_id: str, store_id: str):
    memory = StoreMemory()
    await memory.forget_merchant(merchant_id)
    await memory.forget_store(store_id)
    logger.info("mem0_cleanup", merchant_id=merchant_id, store_id=store_id)
```

Appelé par le webhook handler `app/uninstalled` (voir SECURITY.md section 8).

---

## INTERDICTIONS

- ❌ Stocker des PII dans Mem0 (email, nom, adresse) → ✅ Uniquement patterns et préférences
- ❌ Stocker des tokens/secrets → ✅ Tokens dans la DB (Fernet), jamais dans Mem0
- ❌ Appeler Mem0 de manière synchrone → ✅ Toujours async avec timeout
- ❌ Ignorer les erreurs Mem0 (raise) → ✅ Try/except, graceful degradation
- ❌ Charger toutes les mémoires d'un merchant (unbounded) → ✅ `limit=10` max par recall
- ❌ Oublier le cleanup GDPR à l'uninstall → ✅ `forget_merchant()` dans le webhook handler
