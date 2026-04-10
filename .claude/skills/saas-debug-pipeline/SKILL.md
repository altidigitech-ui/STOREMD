# Skill: SaaS Debug Pipeline

> **Utilise ce skill pour débugger StoreMD en production ou staging.**
> **Couvre tout le stack : Next.js → FastAPI → Celery → Supabase → Redis → Railway → Vercel.**

---

## QUAND UTILISER

- Un scan échoue et tu ne sais pas pourquoi
- Le frontend affiche une erreur 500 / 502 / 504
- Un webhook Shopify/Stripe n'est pas traité
- Le worker Celery ne traite pas les tasks
- Le dashboard affiche des données stale ou vides
- Un deploy Railway/Vercel échoue ou l'app ne répond plus
- Incohérence entre les données affichées et la DB

---

## MÉTHODE — 5 ÉTAPES

```
1. REPRODUIRE   → Confirmer le bug, identifier le scope
2. LOCALISER    → Quelle couche du stack est en cause ?
3. DIAGNOSTIQUER → Logs, DB, Redis — trouver la cause racine
4. FIXER        → Corriger avec le bon pattern
5. VÉRIFIER     → Confirmer le fix, pas de régression
```

---

## ÉTAPE 1 — REPRODUIRE

### Questions à se poser

- Le bug est-il reproductible ? (toujours / intermittent / une seule fois)
- Quel est le trigger ? (action utilisateur / cron / webhook)
- Quel environnement ? (dev localhost / staging / production)
- Quel merchant / store ? (spécifique ou tous)
- Depuis quand ? (après un deploy / toujours / depuis X heures)

### Healthcheck rapide

```bash
# Backend API alive ?
curl https://api.storemd.com/api/v1/health

# Réponse attendue :
# {"status": "healthy", "db": "connected", "redis": "connected"}

# Si 503 → le backend est down ou ne peut pas atteindre DB/Redis
```

---

## ÉTAPE 2 — LOCALISER LA COUCHE

```
Frontend (Vercel)
    │ Erreur affichée dans le browser ?
    │ Console JS errors ? Network tab ?
    ▼
Backend API (Railway - storemd-api)
    │ L'endpoint retourne une erreur ?
    │ Quel status code ? Quel ErrorCode ?
    ▼
Worker Celery (Railway - storemd-worker)
    │ La task est-elle dans la queue ?
    │ La task a-t-elle échoué ?
    ▼
Shopify API
    │ Rate limit ? Token expiré ? App désinstallée ?
    ▼
Supabase (DB)
    │ Query échoue ? RLS bloque ? Données manquantes ?
    ▼
Redis
    │ Connexion perdue ? Queue pleine ? Rate limit cache stale ?
    ▼
External (Claude API / Mem0 / Playwright)
    │ Timeout ? Rate limit ? Service down ?
```

### Identifier par le status code

| Status | Couche probable | Action |
|--------|----------------|--------|
| 401 | Auth middleware | Vérifier JWT, token expiré, merchant existe |
| 403 | Plan checking ou RLS | Vérifier le plan du merchant, RLS policy |
| 404 | Route ou DB | L'entité existe-t-elle en DB ? |
| 422 | Pydantic validation | Input invalide, vérifier le request body |
| 429 | Rate limit (notre ou Shopify) | Vérifier Redis rate limit keys, Shopify headers |
| 500 | Backend (AppError non catchée) | Logs Railway, Sentry |
| 502 | Shopify API ou upstream | Shopify down ? Token révoqué ? |
| 503 | Service unavailable | Backend restart en cours, DB/Redis inaccessible |
| 504 | Timeout | Scan trop long, Celery task timeout, Playwright timeout |

---

## ÉTAPE 3 — DIAGNOSTIQUER

### 3.1 Logs Railway

```bash
# Via Railway CLI
railway logs --service storemd-api
railway logs --service storemd-worker

# Filtrer par scan_id
railway logs --service storemd-worker | grep "scan_id=xxx"

# Filtrer par erreur
railway logs --service storemd-api | grep "app_error"
```

Les logs sont structurés (structlog JSON). Chercher les champs :
- `event` : nom de l'événement ("scan_started", "scanner_failed", "app_error")
- `store_id`, `merchant_id`, `scan_id` : contexte
- `error`, `code` : détail erreur

### 3.2 Sentry

Sentry capture automatiquement les exceptions non-gérées. Vérifier :
- Dashboard Sentry → Issues → filtrer par "storemd"
- Le stacktrace montre la ligne exacte
- Les breadcrumbs montrent les étapes avant l'erreur

### 3.3 DB (Supabase SQL Editor)

```sql
-- Dernier scan d'un store
SELECT id, status, score, error_message, modules, partial_scan,
       started_at, completed_at, duration_ms
FROM scans
WHERE store_id = 'xxx'
ORDER BY created_at DESC
LIMIT 5;

-- Issues d'un scan
SELECT severity, scanner, title, fix_applied
FROM scan_issues
WHERE scan_id = 'xxx'
ORDER BY severity;

-- Webhooks non traités
SELECT id, source, topic, shop_domain, processed, processing_error, created_at
FROM webhook_events
WHERE processed = false
ORDER BY created_at DESC;

-- Merchant et son plan
SELECT id, email, plan, shopify_shop_domain, onboarding_completed
FROM merchants
WHERE id = 'xxx';

-- Usage du merchant ce mois
SELECT usage_type, count, limit_count
FROM usage_records
WHERE merchant_id = 'xxx'
AND period_start <= CURRENT_DATE
AND period_end >= CURRENT_DATE;
```

### 3.4 Redis

```bash
# Via Railway CLI (si Redis CLI accessible)
# Ou via le code Python

# Vérifier une task Celery
redis-cli LLEN celery  # Queue length

# Vérifier un rate limit
redis-cli GET "ratelimit:{merchant_id}:/api/v1/stores/{store_id}/scans"

# Vérifier un OAuth state
redis-cli GET "oauth_state:{state_nonce}"
redis-cli TTL "oauth_state:{state_nonce}"
```

### 3.5 Celery tasks

```bash
# Worker alive ?
celery -A tasks.celery_app inspect ping

# Tasks actives
celery -A tasks.celery_app inspect active

# Tasks réservées (en attente)
celery -A tasks.celery_app inspect reserved

# Tasks récemment échouées
celery -A tasks.celery_app inspect stats
```

---

## ÉTAPE 4 — FIXER

### Bugs courants et fixes

#### Scan bloqué en "running"

```sql
-- Le scan est stuck, le worker a crashé ou timeout
UPDATE scans
SET status = 'failed',
    error_message = 'Worker crashed — manual reset',
    completed_at = NOW()
WHERE id = 'xxx' AND status = 'running';
```

Puis investiguer pourquoi le worker a crashé (logs Railway).

#### Webhook non traité

```sql
-- Vérifier le webhook
SELECT * FROM webhook_events WHERE id = 'xxx';

-- Re-process manuellement
UPDATE webhook_events
SET processed = false, processing_error = NULL, retry_count = 0
WHERE id = 'xxx';
```

Puis trigger le reprocessing via le code ou Celery task.

#### Token Shopify invalide

```python
# Le merchant a réinstallé l'app ou révoqué les permissions
# → Le token en DB est obsolète
# Fix : forcer la réinstallation
# Côté DB : marquer le store

UPDATE stores SET status = 'needs_reinstall' WHERE id = 'xxx';
```

Le frontend détecte `needs_reinstall` et affiche un prompt de réinstallation.

#### RLS bloque une query

```sql
-- Tester en tant que le merchant
SET request.jwt.claims = '{"sub": "merchant-uuid"}';
SET role = 'authenticated';

-- La query retourne-t-elle des résultats ?
SELECT * FROM scans WHERE store_id = 'xxx';

-- Si 0 résultat → le merchant_id ne matche pas auth.uid()
-- Vérifier que merchant_id est bien rempli dans la table
SELECT merchant_id FROM scans WHERE id = 'scan-uuid';
```

#### Celery task ne s'exécute pas

Vérifier dans l'ordre :
1. Redis connecté ? (`REDIS_URL` correct dans Railway ?)
2. Worker running ? (service `storemd-worker` healthy ?)
3. Task dans la queue ? (`redis-cli LLEN celery`)
4. Task échoue silencieusement ? (logs worker)
5. Beat scheduler running ? (il tourne dans le même process que le worker avec `--beat`)

#### Vercel deploy échoue

```bash
# Vérifier le build log dans Vercel dashboard
# Erreurs courantes :
# - TypeScript error (type mismatch, missing import)
# - next.config.js syntax error
# - Missing env var NEXT_PUBLIC_*
# - node_modules corruption → redeploy with "Clear Cache"
```

#### Railway deploy échoue

```bash
# Vérifier le build log dans Railway dashboard
# Erreurs courantes :
# - pip install échoue (package introuvable, version conflict)
# - Dockerfile syntax error
# - Port mismatch ($PORT vs hardcoded)
# - Env var manquante (crash au startup dans config.py)
```

---

## ÉTAPE 5 — VÉRIFIER

Après le fix :

```
[ ] Le bug est résolu (tester le même scénario)
[ ] Pas de régression (tests passent)
[ ] Logs propres (pas d'erreurs récurrentes)
[ ] Sentry clear (pas de nouvelles exceptions)
[ ] Si fix DB : NOTIFY pgrst exécuté
[ ] Si fix code : commit + PR + deploy
[ ] Si le bug était causé par un pattern récurrent : ajouter un test pour l'empêcher
```

---

## SMOKE TEST POST-DEPLOY

Après chaque deploy, exécuter ces vérifications :

```bash
# 1. Backend alive
curl -s https://api.storemd.com/api/v1/health | jq .

# 2. Auth flow (ne pas tester en prod — uniquement staging)
# Vérifier que /auth/install redirige correctement

# 3. Trigger un scan test (staging)
curl -s -X POST https://api.storemd.com/api/v1/stores/{test_store}/scans \
  -H "Authorization: Bearer {jwt}" \
  -H "Content-Type: application/json" \
  -d '{"modules": ["health"]}' | jq .

# 4. Vérifier que le worker traite la task
# → Logs Railway storemd-worker : "scan_started" dans les 10s

# 5. Frontend loads
curl -s -o /dev/null -w "%{http_code}" https://storemd.com
# → 200
```

---

## ALERTES CONNUES (faux positifs)

| Log | Cause | Action |
|-----|-------|--------|
| `shopify_rate_limit retry_after=2.0` | Normal sous charge, le retry gère | Ignorer sauf si fréquent |
| `mem0_unavailable` | Mem0 temporairement down | Ignorer, graceful degradation actif |
| `scanner_timeout scanner=broken_links` | Store avec beaucoup de pages (>200) | Augmenter le timeout ou paginer |
| `push_delivery_failed` | Subscription push expirée | Normal, fallback email actif |
