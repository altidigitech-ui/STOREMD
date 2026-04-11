# /scan-debug — Debug un scan qui échoue

> **Commande slash pour diagnostiquer pourquoi un scan a échoué ou retourne des résultats incorrects.**
> **Usage : `/scan-debug` ou `/scan-debug {scan_id}`**

---

## USAGE

```
/scan-debug                    → Debug le dernier scan échoué
/scan-debug {scan_id}          → Debug un scan spécifique
/scan-debug store {store_id}   → Debug les scans d'un store
```

---

## PROCÉDURE

### Étape 1 — Identifier le scan

```sql
-- Dernier scan échoué
SELECT id, store_id, merchant_id, status, error_message, error_code,
       modules, partial_scan, duration_ms, started_at, completed_at,
       metadata
FROM scans
WHERE status = 'failed'
ORDER BY created_at DESC
LIMIT 1;

-- Ou un scan spécifique
SELECT * FROM scans WHERE id = '{scan_id}';

-- Derniers scans d'un store
SELECT id, status, score, error_message, modules, duration_ms,
       partial_scan, created_at
FROM scans
WHERE store_id = '{store_id}'
ORDER BY created_at DESC
LIMIT 10;
```

### Étape 2 — Classifier le problème

| Status | Signification | Prochaine étape |
|--------|--------------|-----------------|
| `failed` + `error_code` | Le scan a crashé avec une erreur identifiée | Vérifier le code d'erreur → Étape 3 |
| `failed` + `error_message` seul | Erreur non-catégorisée | Chercher dans les logs → Étape 4 |
| `running` (depuis >10 min) | Le scan est bloqué (worker crash ?) | Vérifier le worker → Étape 5 |
| `completed` + `partial_scan=true` | Scan partiel — certains scanners ont échoué | Vérifier `metadata` et `state.errors` → Étape 6 |
| `completed` + `score=0` | Score incorrect | Vérifier les scanner_results → Étape 7 |
| `completed` + `issues_count=0` | Pas d'issues alors qu'il devrait y en avoir | Vérifier les scanners individuels → Étape 7 |
| `pending` (depuis >5 min) | La task Celery n'a pas été prise | Vérifier Redis + worker → Étape 5 |

### Étape 3 — Diagnostic par error_code

```sql
-- Récupérer l'erreur
SELECT error_code, error_message, metadata FROM scans WHERE id = '{scan_id}';
```

| error_code | Cause probable | Fix |
|------------|---------------|-----|
| `SHOPIFY_RATE_LIMIT` | Trop de requêtes Shopify en peu de temps | Le retry automatique aurait dû gérer. Vérifier si le store a beaucoup d'apps/produits. Augmenter les delays entre les groupes de scanners. |
| `SHOPIFY_TOKEN_EXPIRED` | Token Shopify révoqué ou expiré | Le merchant a réinstallé l'app ? Vérifier `merchants.shopify_access_token_encrypted` — si NULL, le merchant doit réinstaller. |
| `SHOPIFY_GRAPHQL_ERROR` | Query GraphQL incorrecte ou données Shopify corrompues | Vérifier le message d'erreur exact. Tester la query manuellement. |
| `SCAN_TIMEOUT` | Scan a dépassé le timeout (10 min) | Store avec beaucoup de données (>5000 produits). Envisager le bulk operations API. |
| `AGENT_CLAUDE_API_ERROR` | Claude API down ou erreur | Vérifier le status Anthropic. Le fallback rules-based aurait dû prendre le relais. |
| `AGENT_CLAUDE_API_RATE_LIMIT` | Rate limit Claude API | Vérifier le nombre de scans en parallèle. Réduire la concurrency. |
| `BROWSER_PLAYWRIGHT_TIMEOUT` | Page du store ne charge pas en <60s | Le store est très lent ou down. Vérifier manuellement. |
| `TOKEN_DECRYPT_FAILED` | Fernet key a changé | Vérifier FERNET_KEY dans Railway. Si changée, tous les tokens doivent être re-chiffrés. |

### Étape 4 — Chercher dans les logs Railway

```bash
# Logs du worker (c'est là que les scans s'exécutent)
railway logs --service storemd-worker | grep "scan_id={scan_id}"

# Chercher les erreurs
railway logs --service storemd-worker | grep "scan_failed\|scanner_failed\|error"

# Logs des 30 dernières minutes
railway logs --service storemd-worker --since 30m

# Si le scan a été lancé via l'API (pas via cron)
railway logs --service storemd-api | grep "scan_id={scan_id}"
```

Ce qu'on cherche dans les logs :
```
scan_started        → Le scan a bien démarré ?
scanner_completed   → Quels scanners ont réussi ?
scanner_failed      → Quels scanners ont échoué ? Avec quelle erreur ?
scanner_timeout     → Quels scanners ont timeout ?
scan_completed      → Le scan s'est-il terminé ?
scan_failed         → Erreur finale ?
mem0_unavailable    → Mem0 était-il down ? (graceful degradation)
claude_api_call     → Claude API a-t-il été appelé ? Latence ? Coût ?
shopify_rate_limit  → Rate limit Shopify ?
```

### Étape 5 — Vérifier le worker Celery

```bash
# Worker alive ?
celery -A tasks.celery_app inspect ping
# Attendu : {"celery@xxx": {"ok": "pong"}}

# Tasks actives (en cours d'exécution)
celery -A tasks.celery_app inspect active
# Si le scan est listé → il est en cours
# Si vide → le scan n'a pas été pris par le worker

# Tasks réservées (en attente dans la queue)
celery -A tasks.celery_app inspect reserved

# Queue Redis
redis-cli LLEN celery
# Si > 50 → queue trop longue, worker ne suit pas

# Worker stats
celery -A tasks.celery_app inspect stats
```

Si le worker est down :
```bash
# Vérifier le status dans Railway dashboard
# Service storemd-worker → status "Active" ou "Crashed"

# Si crashed → vérifier les logs de démarrage
railway logs --service storemd-worker | head -50
# Erreur courante : env var manquante, Redis inaccessible, OOM
```

### Étape 6 — Scan partiel

```sql
-- Vérifier quels scanners ont échoué
SELECT metadata->>'errors' as errors,
       scanner_results
FROM scans
WHERE id = '{scan_id}';
```

```python
# Le champ metadata.errors contient la liste des erreurs :
# ["Scanner broken_links: Timeout after 60s",
#  "Scanner email_health: DNS lookup failed"]

# Le champ scanner_results contient les résultats par scanner :
# {"health_scorer": {...}, "app_impact": {...}, "broken_links": null}
# null = le scanner a échoué
```

Actions :
- Si un scanner timeout fréquemment → augmenter son timeout ou paginer ses requêtes
- Si un scanner échoue sur des données spécifiques → ajouter un edge case
- Si le scan est partial mais le score est correct → acceptable (warning au merchant)

### Étape 7 — Résultats incorrects

```sql
-- Vérifier les issues du scan
SELECT module, scanner, severity, title, impact, fix_type
FROM scan_issues
WHERE scan_id = '{scan_id}'
ORDER BY severity, scanner;

-- Comparer avec le scan précédent
SELECT s.id, s.score, s.issues_count, s.created_at
FROM scans s
WHERE s.store_id = (SELECT store_id FROM scans WHERE id = '{scan_id}')
ORDER BY s.created_at DESC
LIMIT 5;
```

Si score = 0 ou pas d'issues :
```sql
-- Vérifier le merchant et son plan
SELECT m.plan, m.shopify_shop_domain, m.shopify_access_token_encrypted IS NOT NULL as has_token
FROM merchants m
JOIN stores st ON st.merchant_id = m.id
JOIN scans sc ON sc.store_id = st.id
WHERE sc.id = '{scan_id}';

-- Si plan = '' ou NULL → bug dans le trigger on_auth_user_created
-- Si has_token = false → le merchant doit réinstaller
-- Si plan = 'free' et modules contient 'browser' → should_run a filtré correctement
```

### Étape 8 — Retry le scan

```sql
-- Remettre le scan en pending pour retry
UPDATE scans
SET status = 'pending',
    error_message = NULL,
    error_code = NULL,
    started_at = NULL,
    completed_at = NULL,
    metadata = metadata || '{"retry": true}'
WHERE id = '{scan_id}';
```

```python
# Ou trigger un nouveau scan via l'API
# POST /api/v1/stores/{store_id}/scans
# {"modules": ["health"]}

# Ou via Celery directement
from tasks.scan_tasks import run_scan
run_scan.delay(scan_id, store_id, ["health"])
```

---

## CHECKLIST RÉSOLUTION

```
[ ] Cause identifiée (error_code, logs, ou inspection DB)
[ ] Fix appliqué (code, config, ou data)
[ ] Scan relancé et réussi
[ ] Si bug récurrent → test ajouté pour empêcher la régression
[ ] Si timeout fréquent → timeout ou pagination ajusté
[ ] Si erreur externe (Shopify, Claude) → vérifier que le graceful degradation fonctionne
```
