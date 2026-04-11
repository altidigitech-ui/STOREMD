# /deploy — Deploy StoreMD

> **Commande slash pour déployer backend + frontend + vérifications post-deploy.**
> **Usage : `/deploy` ou `/deploy backend` ou `/deploy frontend`**

---

## USAGE

```
/deploy              → Deploy complet (backend + frontend)
/deploy backend      → Deploy backend seulement (Railway)
/deploy frontend     → Deploy frontend seulement (Vercel)
/deploy check        → Vérifications post-deploy uniquement (pas de deploy)
```

---

## PROCÉDURE COMPLÈTE

### Étape 1 — Pré-deploy checks

Avant de deploy, vérifier :

```bash
# 1. Tests passent
cd backend && pytest -m "unit or integration" -x --tb=short
cd frontend && npm test -- --run

# 2. Lint clean
cd backend && ruff check app/ tasks/
cd frontend && npm run lint

# 3. Pas de secrets dans le code
grep -rn "sk_live\|sk_test_\|whsec_\|sk-ant-\|eyJhbG" backend/app/ frontend/src/ --include="*.py" --include="*.ts" --include="*.tsx" || echo "✅ No secrets found"

# 4. Pas de print() ou console.log en prod
grep -rn "print(" backend/app/ --include="*.py" | grep -v "# noqa" || echo "✅ No print()"
grep -rn "console.log" frontend/src/ --include="*.ts" --include="*.tsx" | grep -v "// debug" || echo "✅ No console.log"

# 5. Vérifier s'il y a une migration DB à appliquer
ls -la database/migrations/ | tail -5
echo "⚠️  Si nouvelle migration : l'appliquer AVANT de deploy le code"
```

Si une migration DB est en attente :

```
1. Ouvrir Supabase SQL Editor
2. Coller le contenu de la nouvelle migration
3. Exécuter
4. Exécuter : NOTIFY pgrst, 'reload schema';
5. Vérifier avec une query de test
6. PUIS continuer le deploy code
```

### Étape 2 — Deploy backend (Railway)

```bash
# Railway auto-deploy depuis GitHub main
# Option 1 : push sur main (auto-deploy)
git push origin main

# Option 2 : deploy manuel via Railway CLI
railway up --service storemd-api
railway up --service storemd-worker

# Attendre le build (~2-4 min)
# Railway Dashboard → Services → storemd-api → Deployments → status "Active"
# Railway Dashboard → Services → storemd-worker → Deployments → status "Active"
```

### Étape 3 — Deploy frontend (Vercel)

```bash
# Vercel auto-deploy depuis GitHub main (même push que Railway)
# Attendre le build (~1-2 min)
# Vercel Dashboard → Deployments → status "Ready"

# Ou deploy manuel
cd frontend && vercel --prod
```

### Étape 4 — Post-deploy checks

```bash
# 1. Healthcheck backend
echo "=== Healthcheck ==="
curl -s https://api.storemd.com/api/v1/health | python3 -m json.tool
# Attendu : {"status": "healthy", "db": "connected", "redis": "connected"}

# 2. Frontend accessible
echo "=== Frontend ==="
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://storemd.com)
echo "Frontend status: $HTTP_CODE"
# Attendu : 200

# 3. API répond (endpoint public)
echo "=== API ==="
curl -s https://api.storemd.com/api/v1/health | python3 -c "import sys,json; d=json.load(sys.stdin); print('API OK' if d.get('status')=='healthy' else 'API FAILED')"

# 4. Worker alive (vérifier les logs)
echo "=== Worker logs (dernières 10 lignes) ==="
railway logs --service storemd-worker --tail 10

# 5. Sentry — vérifier pas de nouvelles exceptions
echo "⚠️  Vérifier Sentry dans les 5 prochaines minutes"
echo "    https://sentry.io → Projects → storemd → Issues"

# 6. Railway services status
echo "=== Railway services ==="
echo "Vérifier que les 2 services sont 'Active' dans le dashboard Railway"
```

### Étape 5 — Mettre à jour CHANGELOG

```bash
# Ajouter l'entrée dans docs/CHANGELOG.md
# Format :
# ## [1.0.X] — YYYY-MM-DD
# ### Added/Changed/Fixed
# - Description du changement
```

---

## ROLLBACK

Si le deploy a cassé quelque chose :

```bash
# Backend (Railway)
# Dashboard → Service → Deployments → cliquer le deploy précédent → Rollback
echo "Railway : Rollback via dashboard → Deployments → deploy précédent → Rollback"

# Frontend (Vercel)
# Dashboard → Deployments → cliquer le deploy précédent → Promote to Production
echo "Vercel : Rollback via dashboard → Deployments → deploy précédent → Promote"

# DB (si migration a causé le problème)
# 1. Écrire la migration inverse dans database/migrations/XXX_rollback.sql
# 2. Appliquer dans Supabase SQL Editor
# 3. NOTIFY pgrst, 'reload schema'
# 4. Rollback le code (étape ci-dessus)
```

---

## ERREURS COURANTES DEPLOY

| Erreur | Cause | Fix |
|--------|-------|-----|
| Railway build fail : pip install error | Package introuvable ou version conflict | Vérifier requirements.txt, pin les versions |
| Railway build fail : Dockerfile error | Syntax ou base image issue | Vérifier le Dockerfile, tester en local `docker build .` |
| Railway service crash loop | Env var manquante → crash au startup | Vérifier toutes les env vars dans Railway dashboard |
| Vercel build fail : TypeScript error | Type error dans le code | `cd frontend && npm run build` en local pour reproduire |
| Vercel build fail : missing env var | `NEXT_PUBLIC_*` manquante | Ajouter dans Vercel → Settings → Environment Variables |
| Healthcheck 503 après deploy | DB ou Redis inaccessible | Vérifier Supabase status, Redis status dans Railway |
| API retourne 502 | Le backend n'a pas fini de démarrer | Attendre 30s, Railway healthcheck va retry |
| Worker ne traite pas les tasks | Celery n'arrive pas à se connecter à Redis | Vérifier `REDIS_URL` dans les shared variables Railway |

---

## RÈGLES

- ❌ Deploy sans tests qui passent
- ❌ Deploy sans lint clean
- ❌ Deploy avec des secrets dans le code
- ❌ Deploy une migration DB APRÈS le code (toujours AVANT)
- ❌ Deploy le vendredi après 16h
- ❌ Deploy sans vérifier les post-deploy checks
- ❌ Deploy sans mettre à jour CHANGELOG.md
- ✅ Toujours 5 min de monitoring Sentry post-deploy
