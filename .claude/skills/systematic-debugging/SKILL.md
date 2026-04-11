# Skill: Systematic Debugging

> **Utilise ce skill quand tu fais face à un bug et que tu ne sais pas par où commencer.**
> **Méthode en 5 étapes. Pas de shotgun debugging. Pas de changements au hasard.**
> **Pour les bugs spécifiques au stack StoreMD (Railway, Supabase, Celery), voir
> `.claude/skills/saas-debug-pipeline/SKILL.md`.**

---

## QUAND UTILISER

- Un test échoue et la cause n'est pas évidente
- Un comportement inattendu en dev ou staging
- Un crash reporté par Sentry sans contexte clair
- Un bug intermittent (fonctionne parfois, échoue parfois)
- Avant de toucher au code — pour ne pas empirer les choses

---

## MÉTHODE — 5 ÉTAPES

```
1. REPRODUIRE    → Confirmer le bug avec un cas minimal
2. ISOLER        → Réduire le scope (quelle couche, quel module, quelle ligne)
3. DIAGNOSTIQUER → Comprendre la cause racine (pas le symptôme)
4. FIXER         → Corriger avec le bon pattern, pas un workaround
5. VÉRIFIER      → Confirmer le fix + empêcher la régression
```

---

## ÉTAPE 1 — REPRODUIRE

**Objectif :** transformer "ça marche pas" en un scénario reproductible.

### Questions à poser

```
- Quelles sont les étapes EXACTES pour reproduire ?
- Quel est le résultat ATTENDU vs le résultat OBTENU ?
- Le bug est-il TOUJOURS reproductible ou intermittent ?
- Depuis QUAND ? (quel commit, quel deploy, quel changement)
- Sur quel environnement ? (dev / staging / prod)
- Avec quelles données ? (quel merchant, quel store, quel scan)
```

### Cas minimal

Réduire au maximum les variables :

```python
# Au lieu de lancer un scan complet de 43 features
# → isoler le scanner qui échoue
# → l'appeler seul avec des données minimales

async def test_reproduce_bug():
    scanner = GhostBillingDetector()
    mock_shopify = MockShopifyClient(
        charges=[{"name": "Old App", "status": "active", "price": "9.99"}],
        apps=[],  # Pas d'apps installées → devrait détecter un ghost
    )
    result = await scanner.scan("test-store", mock_shopify, [])
    # Le bug : result.issues est vide alors qu'il devrait y avoir 1 issue
```

### Bug intermittent

Si le bug n'est pas toujours reproductible :

```
- Race condition ? (parallélisme, async, Celery concurrency)
- Dépendance à l'état ? (cache Redis, Mem0, session)
- Dépendance au timing ? (rate limit, timeout, cron schedule)
- Dépendance aux données ? (certains stores mais pas d'autres)
- Dépendance à l'environnement ? (Railway container restart, DNS)
```

---

## ÉTAPE 2 — ISOLER

**Objectif :** identifier la couche et le module en cause.

### Méthode par élimination

```
Le bug est dans le FRONTEND ou le BACKEND ?
  → Vérifier le Network tab : la réponse API est-elle correcte ?
  → Si l'API retourne les bonnes données → bug frontend
  → Si l'API retourne des mauvaises données → bug backend

Le bug est dans l'API ou le WORKER ?
  → L'endpoint retourne-t-il une erreur ?
  → La Celery task est-elle dans la queue ? A-t-elle échoué ?

Le bug est dans le SCANNER ou l'ORCHESTRATEUR ?
  → Appeler le scanner directement avec des mocks
  → Si le scanner retourne le bon résultat → bug dans l'orchestrateur
  → Si le scanner retourne un mauvais résultat → bug dans le scanner

Le bug est dans NOTRE CODE ou un SERVICE EXTERNE ?
  → Shopify API retourne-t-elle des données correctes ?
  → Supabase query retourne-t-elle les bons résultats ?
  → Redis est-il accessible ?
```

### Binary search dans le code

Si tu ne sais pas où est le bug dans une fonction longue :

```python
# Ajouter des logs temporaires pour isoler
logger.debug("DEBUG_1: before shopify call", store_id=store_id)
data = await shopify.graphql(query)
logger.debug("DEBUG_2: after shopify call", data_count=len(data))
processed = self.process(data)
logger.debug("DEBUG_3: after process", issues_count=len(processed))
# → Le bug est entre le dernier log qui affiche des données correctes
#   et le premier qui affiche des données incorrectes
```

Supprimer les logs de debug après le fix.

---

## ÉTAPE 3 — DIAGNOSTIQUER

**Objectif :** comprendre la CAUSE RACINE, pas le symptôme.

### Les 5 "Pourquoi"

```
Symptôme : Le scan retourne un score de 0.

Pourquoi le score est 0 ?
→ Parce que scanner_results est vide.

Pourquoi scanner_results est vide ?
→ Parce que tous les scanners ont été skippés.

Pourquoi les scanners ont été skippés ?
→ Parce que should_run() retourne False pour tous.

Pourquoi should_run() retourne False ?
→ Parce que le plan du merchant est "" (string vide) au lieu de "free".

Pourquoi le plan est "" ?
→ Parce que le trigger on_auth_user_created ne set pas le plan par défaut.

CAUSE RACINE : le trigger SQL manque DEFAULT 'free' pour la colonne plan.
```

### Patterns de causes racines

| Catégorie | Exemples |
|-----------|----------|
| **Data** | Donnée manquante en DB, mauvais type, NULL inattendu, encoding |
| **State** | Cache stale, session expirée, Mem0 inconsistant, Redis key manquante |
| **Timing** | Race condition, timeout, retry qui arrive trop tard, cron décalé |
| **Logic** | Condition inversée, off-by-one, edge case non géré, fallthrough |
| **External** | Shopify API change, Stripe webhook format, Playwright version |
| **Config** | Env var manquante, mauvais URL, mauvaise API version, CORS |
| **Types** | Type mismatch Python (str vs int), JSON parsing, None vs "" |

---

## ÉTAPE 4 — FIXER

**Objectif :** corriger la cause racine, pas masquer le symptôme.

### Bon fix vs mauvais fix

```python
# ❌ MAUVAIS — masque le symptôme
async def run_scanners(self, state):
    try:
        # ... scanners ...
    except Exception:
        state.score = 50  # "au moins c'est pas 0"
        return state

# ✅ BON — corrige la cause racine
# Fix dans le trigger SQL :
# ALTER TABLE merchants ALTER COLUMN plan SET DEFAULT 'free';
# + migration pour corriger les merchants existants :
# UPDATE merchants SET plan = 'free' WHERE plan = '' OR plan IS NULL;
```

### Checklist avant de fixer

```
[ ] J'ai identifié la cause racine (pas le symptôme)
[ ] Mon fix corrige la cause racine
[ ] Mon fix ne casse pas autre chose (effets de bord)
[ ] Mon fix suit les patterns du projet (AppError, structlog, etc.)
[ ] Mon fix est minimal (pas de refactor opportuniste dans le même commit)
```

### Types de fix

| Type | Quand | Exemple |
|------|-------|---------|
| **Code fix** | Bug dans la logique | Corriger une condition, ajouter un edge case |
| **Data fix** | Données corrompues en DB | Migration SQL pour corriger les données |
| **Config fix** | Env var manquante ou incorrecte | Ajouter/corriger dans Railway/Vercel |
| **Dependency fix** | Version incompatible | Pin la version dans requirements.txt |
| **Infrastructure fix** | Service down, container config | Railway settings, Supabase config |

---

## ÉTAPE 5 — VÉRIFIER

**Objectif :** confirmer que le fix fonctionne ET ne crée pas de régression.

### Vérification immédiate

```
[ ] Le scénario original ne reproduit plus le bug
[ ] Les tests existants passent toujours (pytest + vitest)
[ ] Le fix fonctionne avec les données qui causaient le bug
```

### Empêcher la régression

```python
# TOUJOURS écrire un test pour le bug fixé

@pytest.mark.asyncio
async def test_scan_with_empty_plan_defaults_to_free():
    """Regression test: empty plan string should default to 'free'.
    
    Bug: merchants created by OAuth trigger had plan='' instead of 'free',
    causing all scanners to be skipped (should_run returned False).
    Fix: DEFAULT 'free' in SQL + migration to fix existing rows.
    """
    merchant = create_test_merchant(plan="")
    plan = await get_effective_plan(merchant.id)
    assert plan == "free"
```

### Post-deploy

```
[ ] Logs propres (pas d'erreurs nouvelles)
[ ] Sentry clear (pas de nouvelles exceptions liées au fix)
[ ] Monitoring OK (healthcheck, scan success rate)
[ ] Le merchant qui a reporté le bug confirme (si applicable)
```

---

## ANTI-PATTERNS

### Ne pas faire

| Anti-pattern | Pourquoi c'est mauvais | Alternative |
|-------------|----------------------|-------------|
| Shotgun debugging (changer plein de choses à la fois) | Impossible de savoir quel changement a fixé le bug | Un changement à la fois, tester après chaque |
| Copier-coller une solution StackOverflow sans comprendre | Le fix peut masquer le symptôme ou créer un nouveau bug | Comprendre la cause racine d'abord |
| Ajouter un `try/except Exception: pass` | Masque le bug, il reviendra plus fort | Catch l'exception spécifique, logger, gérer |
| "Ça marche sur ma machine" | Les environnements diffèrent | Tester dans le même environnement que le bug |
| Fixer dans main directement | Pas de review, pas de tests, risque de régression | Branch + PR + tests + review |
| Refactorer en même temps que fixer | Le fix est noyé dans le refactor, impossible à reviewer | Fix minimal d'abord, refactor dans un autre PR |

### Red flags dans un fix

```
⚠️ Le fix contient un sleep() ou waitForTimeout() → timing hack
⚠️ Le fix catch Exception générique → masque le problème
⚠️ Le fix hardcode une valeur → fragile, cassera avec d'autres données
⚠️ Le fix est plus long que 50 lignes → peut-être trop de scope
⚠️ Le fix n'a pas de test → le bug reviendra
```

---

## OUTILS DE DEBUG — RAPPEL

| Outil | Quand | Comment |
|-------|-------|---------|
| structlog | Ajouter des logs contextuels temporaires | `logger.debug("debug_point", key=value)` |
| pytest -x | Stopper au premier échec | `pytest -x tests/test_scanners.py` |
| pytest --pdb | Debugger interactif au point d'échec | `pytest --pdb tests/test_scanners.py` |
| Sentry | Exceptions en prod/staging | Dashboard Sentry → breadcrumbs + stacktrace |
| Railway logs | Logs backend/worker en temps réel | `railway logs --service storemd-api` |
| Supabase SQL Editor | Inspecter la DB directement | Queries ad-hoc sur les tables |
| Redis CLI | Inspecter les keys Redis | `redis-cli GET "key"`, `LLEN celery` |
| Network tab (browser) | Voir les requêtes API du frontend | DevTools → Network → filtrer par XHR |
