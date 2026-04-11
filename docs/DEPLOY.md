# DEPLOY.md — Guide Déploiement StoreMD

> **Railway (backend API + Celery worker) + Vercel (frontend Next.js) + Supabase (DB).**
> **Chaque service, ses env vars, ses Dockerfiles, sa config.**

---

## ARCHITECTURE DEPLOY

```
GitHub (altidigitech-ui)
    │
    │ Push on main → auto-deploy
    │
    ├──────────────────────────────┐
    │                              │
    ▼                              ▼
Railway Project                 Vercel Project
    │                              │
    ├── storemd-api               frontend/
    │   (FastAPI, port 8000)       (Next.js 14, SSR)
    │   Dockerfile                 Auto-build npm run build
    │                              │
    ├── storemd-worker             CDN + Edge
    │   (Celery + beat + PW)       https://storemd.com
    │   Dockerfile.worker          https://storemd.vercel.app
    │
    ├── Redis (managed add-on)
    │   redis://...
    │
    └── https://api.storemd.com

Supabase (séparé)
    │
    ├── PostgreSQL + RLS
    ├── Auth (JWT)
    ├── Storage (screenshots, reports, backups)
    └── https://xxx.supabase.co
```

---

## RAILWAY — BACKEND

### Projet Railway

Un seul Railway project avec 3 services :

| Service | Type | Source | Dockerfile | Port |
|---------|------|--------|-----------|------|
| `storemd-api` | Web | GitHub `altidigitech-ui` | `backend/Dockerfile` | 8000 |
| `storemd-worker` | Worker | GitHub `altidigitech-ui` | `backend/Dockerfile.worker` | N/A |
| Redis | Add-on | Railway managed | N/A | 6379 |

### Dockerfile — API

```dockerfile
# backend/Dockerfile

FROM python:3.12-slim

WORKDIR /app

# Deps système minimales
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code
COPY . .

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Port dynamique Railway
EXPOSE 8000

# Uvicorn avec le port Railway
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--loop", "uvloop"]
```

### Dockerfile — Worker

```dockerfile
# backend/Dockerfile.worker

FROM python:3.12-slim

WORKDIR /app

# Deps système pour Playwright Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxrandr2 libgbm1 libpango-1.0-0 libcairo2 \
    libasound2 libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

# Installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installer Playwright + Chromium
RUN pip install playwright && playwright install chromium

# Copier le code
COPY . .

# Celery worker + beat scheduler dans le même process
CMD ["celery", "-A", "tasks.celery_app", "worker", "--beat", "--loglevel=info", "--concurrency=2"]
```

### Root directory Railway

Les deux services pointent vers le même repo mais des Dockerfiles différents :

```
storemd-api :
  Root Directory  : backend
  Dockerfile Path : Dockerfile
  
storemd-worker :
  Root Directory  : backend
  Dockerfile Path : Dockerfile.worker
```

### Custom domain

```
storemd-api → api.storemd.com
  Railway Settings → Networking → Custom Domain → api.storemd.com
  DNS : CNAME api.storemd.com → xxx.up.railway.app
  SSL : automatique (Railway gère Let's Encrypt)
```

---

## RAILWAY — ENV VARS

Configurées dans Railway Dashboard → Service → Variables. Partagées entre api et worker (même project).

```bash
# === Supabase ===
SUPABASE_URL=https://ilqjqbwiljrdfsqrenwo.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_DB_URL=postgresql://postgres:xxx@db.ilqjqbwiljrdfsqrenwo.supabase.co:5432/postgres

# === Shopify ===
SHOPIFY_API_KEY=xxx
SHOPIFY_API_SECRET=xxx
SHOPIFY_API_VERSION=2025-04
SHOPIFY_SCOPES=read_products,write_products,read_themes,write_themes,read_orders,read_online_store

# === Stripe ===
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_PRICE_STARTER=price_xxx
STRIPE_PRICE_PRO=price_xxx
STRIPE_PRICE_AGENCY=price_xxx

# === Claude API ===
ANTHROPIC_API_KEY=sk-ant-xxx

# === Mem0 ===
MEM0_API_KEY=m0-xxx                    # Ou vide si self-hosted pgvector

# === Redis ===
REDIS_URL=${{Redis.REDIS_URL}}         # Référence Railway managed Redis

# === Resend ===
RESEND_API_KEY=re_xxx

# === Sentry ===
SENTRY_DSN=https://xxx@sentry.io/xxx

# === LangSmith ===
LANGCHAIN_API_KEY=ls_xxx
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=storemd

# === VAPID (Push notifications) ===
VAPID_PRIVATE_KEY=xxx
VAPID_CONTACT_EMAIL=contact@storemd.com

# === App ===
APP_ENV=production
APP_URL=https://storemd.com
BACKEND_URL=https://api.storemd.com
FERNET_KEY=xxx
```

### Variables partagées Railway

Utiliser les "Shared Variables" de Railway pour partager entre api et worker :

```
Railway Dashboard → Project → Settings → Shared Variables
→ Toutes les vars ci-dessus en shared
→ Les deux services y accèdent automatiquement
```

### Variables spécifiques

```
storemd-api :
  PORT=8000              # Railway peut override avec $PORT
  WORKERS=2              # Uvicorn workers

storemd-worker :
  CELERY_CONCURRENCY=2   # Max 2 tasks simultanées (Playwright = RAM)
```

---

## VERCEL — FRONTEND

### Configuration

```
Vercel Dashboard → Import Git Repository → altidigitech-ui
  Framework Preset : Next.js
  Root Directory   : frontend
  Build Command    : npm run build
  Output Directory : .next
  Install Command  : npm install
```

### Custom domain

```
Vercel Dashboard → Settings → Domains → storemd.com
DNS :
  A     storemd.com     76.76.21.21
  CNAME www.storemd.com cname.vercel-dns.com
SSL : automatique (Vercel gère)
```

### Env vars Vercel

```bash
# Uniquement les vars NEXT_PUBLIC_ (exposées au browser)
NEXT_PUBLIC_SUPABASE_URL=https://ilqjqbwiljrdfsqrenwo.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_xxx
NEXT_PUBLIC_BACKEND_URL=https://api.storemd.com
NEXT_PUBLIC_SHOPIFY_API_KEY=xxx
NEXT_PUBLIC_VAPID_PUBLIC_KEY=BNx...
NEXT_PUBLIC_APP_URL=https://storemd.com
```

**JAMAIS** de secret key (Stripe secret, Supabase service role, Fernet, etc.) dans Vercel.

### next.config.js — API proxy

```javascript
// frontend/next.config.js

/** @type {import('next').NextConfig} */
module.exports = {
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1/:path*`,
      },
    ];
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-XSS-Protection", value: "1; mode=block" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" },
        ],
      },
    ];
  },
};
```

---

## SUPABASE — DATABASE

### Projet

```
Project Ref   : ilqjqbwiljrdfsqrenwo
Region        : eu-west (ou us-east selon la cible marché)
Plan          : Free (MVP) → Pro (quand >500 merchants)
```

### Migrations

```bash
# Appliquer une migration
# Option 1 : Supabase SQL Editor (dashboard)
# → Coller le contenu de database/migrations/XXX.sql
# → Exécuter

# Option 2 : Via MCP Supabase dans Claude Code
# → "Exécute le SQL de migration complet via MCP Supabase"

# TOUJOURS terminer par :
NOTIFY pgrst, 'reload schema';
```

### Storage buckets

Créer les buckets dans Supabase Dashboard → Storage :

```
screenshots  → Private → Policies : merchant access via store_id path
reports      → Private → Policies : merchant access via store_id path
backups      → Private → Policies : merchant access via store_id path
```

### Auth

```
Supabase Dashboard → Authentication → Providers :
  Email : enabled (pour le fallback)
  
  Note : L'auth principale est via Shopify OAuth.
  Supabase Auth crée le user, le trigger on_auth_user_created
  crée le profil merchant. Le JWT Supabase est utilisé pour
  authentifier les requêtes API.
```

---

## PROCÉDURE DE DEPLOY

### Premier deploy (setup initial)

```
ÉTAPE 1 — Supabase
  [ ] Créer le projet Supabase
  [ ] Appliquer database/migrations/001_initial.sql
  [ ] NOTIFY pgrst, 'reload schema'
  [ ] Activer l'extension vector (si Mem0 self-hosted)
  [ ] Créer les buckets Storage (screenshots, reports, backups)
  [ ] Configurer les Storage policies
  [ ] Récupérer SUPABASE_URL, ANON_KEY, SERVICE_ROLE_KEY

ÉTAPE 2 — Stripe
  [ ] Créer les 3 produits (Starter, Pro, Agency)
  [ ] Créer les Price IDs
  [ ] Configurer le Customer Portal (Stripe Dashboard)
  [ ] Créer le webhook endpoint → https://api.storemd.com/api/v1/webhooks/stripe
  [ ] Activer les events : checkout.session.completed, invoice.paid,
      invoice.payment_failed, customer.subscription.updated,
      customer.subscription.deleted
  [ ] Récupérer STRIPE_SECRET, PUBLISHABLE, WEBHOOK_SECRET, PRICE_IDs

ÉTAPE 3 — Shopify Partner
  [ ] Créer l'app dans le Shopify Partner Dashboard
  [ ] Configurer App URL → https://storemd.com
  [ ] Configurer Allowed redirection URL → https://api.storemd.com/api/v1/auth/callback
  [ ] Récupérer SHOPIFY_API_KEY, SHOPIFY_API_SECRET

ÉTAPE 4 — Clés et secrets
  [ ] Générer FERNET_KEY : python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  [ ] Générer VAPID keys : python -c "from py_vapid import Vapid; v=Vapid(); v.generate_keys(); print(v.public_key, v.private_key)"
  [ ] Récupérer ANTHROPIC_API_KEY depuis console.anthropic.com
  [ ] Récupérer MEM0_API_KEY (si hosted) ou laisser vide
  [ ] Récupérer RESEND_API_KEY
  [ ] Récupérer SENTRY_DSN
  [ ] Récupérer LANGCHAIN_API_KEY

ÉTAPE 5 — Railway
  [ ] Créer le projet Railway
  [ ] Ajouter le Redis add-on
  [ ] Créer le service storemd-api (Dockerfile, root: backend)
  [ ] Créer le service storemd-worker (Dockerfile.worker, root: backend)
  [ ] Configurer toutes les env vars (section ci-dessus)
  [ ] Configurer le custom domain api.storemd.com
  [ ] Vérifier le healthcheck : curl https://api.storemd.com/api/v1/health

ÉTAPE 6 — Vercel
  [ ] Importer le repo GitHub
  [ ] Root directory : frontend
  [ ] Configurer les env vars NEXT_PUBLIC_*
  [ ] Configurer le custom domain storemd.com
  [ ] Vérifier : curl https://storemd.com → 200

ÉTAPE 7 — Vérifications post-deploy
  [ ] Healthcheck API : {"status": "healthy", "db": "connected", "redis": "connected"}
  [ ] Frontend loads : page d'accueil visible
  [ ] OAuth flow : installer l'app sur un store de test
  [ ] Premier scan : déclencher et vérifier completion
  [ ] Webhook Shopify : vérifier réception (Shopify Partner → Webhooks → Logs)
  [ ] Webhook Stripe : vérifier réception (Stripe Dashboard → Webhooks → Logs)
  [ ] Push notification : envoyer un test
```

### Deploy courant (mise à jour code)

```bash
# 1. Merge la PR dans main
git checkout main
git pull

# 2. Railway auto-deploy (détecte le push sur main)
# → Build + deploy storemd-api
# → Build + deploy storemd-worker
# Temps : ~2-4 min

# 3. Vercel auto-deploy (détecte le push sur main)
# → Build frontend
# → Deploy sur CDN
# Temps : ~1-2 min

# 4. Smoke test post-deploy
curl -s https://api.storemd.com/api/v1/health | jq .
curl -s -o /dev/null -w "%{http_code}" https://storemd.com

# 5. Vérifier Sentry (pas de nouvelles erreurs dans les 5 min)
```

### Deploy avec migration DB

```bash
# 1. Appliquer la migration AVANT de deploy le code
#    (le nouveau code peut dépendre de la nouvelle colonne/table)

# Supabase SQL Editor :
# → Coller database/migrations/XXX.sql
# → Exécuter
# → NOTIFY pgrst, 'reload schema'

# 2. Vérifier que la migration est appliquée
#    → Query de test dans SQL Editor

# 3. Merge la PR (code qui utilise la nouvelle migration)
# → Railway + Vercel auto-deploy

# 4. Smoke test
```

### Rollback

```bash
# Railway :
# Dashboard → Service → Deployments → cliquer sur le deploy précédent → Rollback

# Vercel :
# Dashboard → Deployments → cliquer sur le deploy précédent → Promote to Production

# DB (si migration a cassé quelque chose) :
# → Écrire et appliquer la migration inverse
# → database/migrations/XXX_rollback_description.sql
# → NOTIFY pgrst, 'reload schema'
```

---

## ENVIRONNEMENTS

### Dev (local)

```bash
# Backend
cd backend
cp .env.example .env      # Remplir avec les clés dev/staging
uvicorn app.main:app --reload --port 8000

# Worker (dans un autre terminal)
celery -A tasks.celery_app worker --beat --loglevel=info

# Redis (Docker local)
docker run -d -p 6379:6379 redis:7

# Frontend
cd frontend
cp .env.local.example .env.local
npm run dev                 # http://localhost:3000
```

### Staging

```
Railway : projet séparé "storemd-staging"
Vercel  : preview deploys automatiques sur chaque PR
Supabase: projet séparé (ou même projet, DB séparée)

Env vars staging :
  APP_ENV=staging
  APP_URL=https://storemd-staging.vercel.app
  BACKEND_URL=https://api-staging.storemd.com (ou URL Railway staging)
  STRIPE_SECRET_KEY=sk_test_xxx   # Clés TEST Stripe
  SHOPIFY_API_KEY=xxx             # App de test Shopify Partner
```

### Production

```
Railway : projet "storemd-production"
Vercel  : deploy sur main → production
Supabase: projet production

Env vars production :
  APP_ENV=production
  APP_URL=https://storemd.com
  BACKEND_URL=https://api.storemd.com
  STRIPE_SECRET_KEY=sk_live_xxx   # Clés LIVE Stripe
```

---

## MONITORING DEPLOY

### Healthcheck

```python
# app/api/routes/health.py

@router.get("/health")
async def healthcheck():
    """Vérifie que le backend, la DB, et Redis fonctionnent."""
    health = {"status": "healthy", "version": settings.APP_VERSION}

    # DB
    try:
        supabase = get_supabase_service()
        result = await supabase.table("merchants").select("id").limit(1).execute()
        health["db"] = "connected"
    except Exception as exc:
        health["db"] = f"error: {str(exc)[:100]}"
        health["status"] = "unhealthy"

    # Redis
    try:
        redis = get_redis()
        await redis.ping()
        health["redis"] = "connected"
    except Exception as exc:
        health["redis"] = f"error: {str(exc)[:100]}"
        health["status"] = "unhealthy"

    status_code = 200 if health["status"] == "healthy" else 503
    return JSONResponse(content=health, status_code=status_code)
```

### Railway healthcheck config

```
Service storemd-api :
  Health Check Path : /api/v1/health
  Health Check Timeout : 10s
  Health Check Interval : 30s
```

Si le healthcheck échoue 3 fois → Railway restart le service automatiquement.

### Alertes post-deploy

```
[ ] Sentry : pas de nouvelles erreurs dans les 5 min post-deploy
[ ] Healthcheck : retourne 200 (pas 503)
[ ] Railway : les deux services sont "Active" (pas "Crashed")
[ ] Vercel : le deploy est "Ready" (pas "Error")
[ ] Logs : pas de crash loop dans les logs Railway
```

---

## SCALING RAILWAY

### Quand scaler

| Signal | Action |
|--------|--------|
| API response time > 500ms (p95) | Augmenter les uvicorn workers (2 → 4) |
| Worker queue length > 50 tasks | Ajouter un 2ème worker service |
| Redis memory > 80% | Upgrader le plan Redis |
| Celery tasks timeout fréquents | Séparer browser tasks dans un worker dédié |

### Comment scaler

```
# Plus de workers API
# Railway → storemd-api → Settings → Dockerfile
# Changer --workers 2 → --workers 4
# Ou : Railway → storemd-api → Settings → Instances → 2 (horizontal)

# Plus de Celery workers
# Créer un nouveau service : storemd-worker-2
# Même Dockerfile.worker
# Ou séparer : storemd-worker-scan (scans) + storemd-worker-browser (Playwright)

# Redis plus gros
# Railway → Redis add-on → Upgrade plan
```

### Coûts estimés Railway

| Phase | Services | RAM estimée | Coût/mois |
|-------|----------|------------|-----------|
| MVP (0-100 merchants) | api (512MB) + worker (1GB) + Redis (256MB) | ~1.8GB | ~$15-25 |
| Growth (100-500) | api (1GB) + worker (2GB) + Redis (512MB) | ~3.5GB | ~$30-50 |
| Scale (500-2000) | api ×2 + worker ×2 + browser-worker + Redis (1GB) | ~8GB | ~$60-100 |

---

## CHECKLIST DEPLOY

### Avant chaque deploy

```
[ ] Tests passent (pytest + vitest)
[ ] Lint clean (ruff + eslint)
[ ] Pas de secrets dans le code (grep -r "sk_live\|sk_test\|password" .)
[ ] PR reviewée (pas de commit direct sur main)
[ ] Migration DB appliquée SI nécessaire (AVANT le deploy code)
[ ] CHANGELOG.md mis à jour
```

### Après chaque deploy

```
[ ] Healthcheck 200 : curl https://api.storemd.com/api/v1/health
[ ] Frontend 200 : curl -o /dev/null -w "%{http_code}" https://storemd.com
[ ] Sentry clean : pas de nouvelles exceptions
[ ] Railway services : status "Active"
[ ] Vercel deploy : status "Ready"
[ ] Si migration : vérifier avec une query SQL
```

---

## INTERDICTIONS

- ❌ Deploy sans tests qui passent → ✅ CI vérifie avant merge
- ❌ Commit sur main directement → ✅ Branch + PR + review
- ❌ Migration DB après le deploy code → ✅ Migration AVANT le code (le code peut dépendre de la migration)
- ❌ Secrets dans le code ou les Dockerfiles → ✅ Env vars Railway/Vercel
- ❌ `SUPABASE_SERVICE_ROLE_KEY` dans Vercel → ✅ Backend only (Railway)
- ❌ Stripe live keys en staging → ✅ `sk_test_` en staging, `sk_live_` en prod uniquement
- ❌ Deploy le vendredi soir → ✅ Deploy en semaine, avant 16h, quand l'équipe est dispo
- ❌ Ignorer les alertes Sentry post-deploy → ✅ 5 min de monitoring post-deploy minimum
