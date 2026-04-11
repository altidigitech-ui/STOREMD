# Skill: OWASP Security

> **Utilise ce skill pour le code review sécurité.**
> **OWASP Top 10 2025 appliqué au stack StoreMD (FastAPI + Next.js + Supabase).**
> **Pour les détails d'implémentation sécurité StoreMD, voir `docs/SECURITY.md`.**

---

## QUAND UTILISER

- Code review avant merge (vérifier les failles sécurité)
- Écrire un nouvel endpoint API
- Manipuler des données sensibles (tokens, PII, credentials)
- Implémenter l'auth, les webhooks, ou les intégrations externes
- Audit sécurité périodique du codebase

---

## OWASP TOP 10 — APPLIQUÉ À STOREMD

### A01 — Broken Access Control

**Risque :** un merchant accède aux données d'un autre merchant.

**Protections StoreMD :**

```python
# 1. RLS Supabase — dernière ligne de défense
# Chaque table a : USING (merchant_id = auth.uid())
# Même si le code applicatif a un bug, RLS bloque

# 2. Middleware auth — vérifie le JWT + merchant ownership
store: Store = Depends(get_current_store)
# get_current_store vérifie : JWT valide + store.merchant_id == auth.uid()

# 3. JAMAIS d'accès cross-merchant sans service_role
# ❌ supabase.table("scans").select("*").eq("store_id", any_store_id)
# ✅ supabase.table("scans").select("*").eq("store_id", store_id).eq("merchant_id", merchant.id)
```

**Checklist review :**
```
[ ] Chaque endpoint a le middleware auth (Depends(get_current_merchant))
[ ] Les queries filtrent par merchant_id (en plus du RLS)
[ ] Pas d'endpoint qui expose des données cross-merchant
[ ] Les IDs dans les URLs sont validés contre le merchant authentifié
[ ] Le frontend ne stocke pas de données sensibles dans localStorage
```

---

### A02 — Cryptographic Failures

**Risque :** tokens Shopify en clair, secrets exposés.

**Protections StoreMD :**

```python
# Tokens Shopify : Fernet encryption
encrypted = encrypt_token(access_token)  # stocké en DB
decrypted = decrypt_token(encrypted)      # au runtime seulement

# Secrets : env vars, jamais dans le code
settings.SHOPIFY_API_SECRET  # via Pydantic BaseSettings

# HTTPS : Railway + Vercel forcent HTTPS par défaut
# HSTS : configuré dans next.config.js
```

**Checklist review :**
```
[ ] Aucun token/secret en clair dans le code ou les commits
[ ] Fernet encryption pour tous les tokens tiers (Shopify, etc.)
[ ] .env dans .gitignore
[ ] Pas de secret dans les logs (structlog check)
[ ] HTTPS enforced (pas de HTTP en prod)
```

---

### A03 — Injection

**Risque :** SQL injection, XSS, command injection.

**Protections StoreMD :**

```python
# SQL : Supabase client utilise PostgREST → queries paramétrées par défaut
# ❌ JAMAIS de SQL brut avec f-strings
# f"SELECT * FROM scans WHERE store_id = '{store_id}'"  ← INJECTION
# ✅ Supabase client
# supabase.table("scans").select("*").eq("store_id", store_id)

# XSS : Next.js auto-escape par défaut
# ❌ <div dangerouslySetInnerHTML={{__html: userInput}} />
# ✅ <div>{userInput}</div>  ← auto-escaped

# Input validation : Pydantic valide tous les inputs
class ScanRequest(BaseModel):
    modules: list[str] = Field(..., min_length=1, max_length=5)
    # Pydantic rejette les types incorrects, les valeurs hors range, etc.
```

**Checklist review :**
```
[ ] Pas de SQL brut (f-strings, string concatenation)
[ ] Pas de dangerouslySetInnerHTML avec du contenu utilisateur
[ ] Tous les inputs passent par Pydantic
[ ] Pas de eval(), exec(), __import__(), subprocess avec input utilisateur
[ ] Les URL construites sont validées (shop domain regex)
```

---

### A04 — Insecure Design

**Risque :** architecture qui permet des abus by design.

**Protections StoreMD :**

```python
# Rate limiting : empêche le brute force et l'abus
# 30-300 req/min selon le plan

# Plan checking : empêche l'accès aux features payantes
await check_plan_access(merchant_id, feature)

# Usage metering : empêche le dépassement des limites
usage = await billing.increment_usage(merchant_id, store_id, "scan")
if usage["exceeded"]:
    raise AppError(code=ErrorCode.SCAN_LIMIT_REACHED, ...)

# Webhook idempotency : empêche le double-processing
# UNIQUE(source, external_id) dans webhook_events

# Fix approval : empêche les modifications non autorisées
# Le merchant APPROUVE avant chaque One-Click Fix
```

**Checklist review :**
```
[ ] Rate limiting sur chaque endpoint public
[ ] Plan checking avant chaque feature payante
[ ] Usage limits enforced avec compteurs
[ ] Idempotency sur les webhooks
[ ] Pas d'action destructive sans confirmation
```

---

### A05 — Security Misconfiguration

**Risque :** headers manquants, CORS permissif, debug mode en prod.

**Protections StoreMD :**

```python
# CORS : whitelist explicite, pas de wildcard
allow_origins=["https://storemd.com", "https://www.storemd.com"]
# ❌ allow_origins=["*"]

# Debug : désactivé en prod
# APP_ENV=production → pas de /docs, pas de debug logs

# Headers : configurés dans next.config.js
# CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy
```

**Checklist review :**
```
[ ] CORS ne contient pas "*" en prod
[ ] FastAPI /docs et /redoc désactivés en prod
[ ] APP_ENV vérifié au startup
[ ] Security headers présents (CSP, HSTS, X-Frame-Options)
[ ] Pas de stack traces exposées au client (catch-all handler)
```

---

### A06 — Vulnerable Components

**Risque :** dépendances avec des CVE connues.

**Protections StoreMD :**

```bash
# Python : vérifier les vulnérabilités
pip audit

# Node : vérifier les vulnérabilités
npm audit

# Dependabot : activé sur le repo GitHub
# → PR automatiques quand une dépendance a un CVE
```

**Checklist review :**
```
[ ] pip audit clean (pas de CVE high/critical)
[ ] npm audit clean
[ ] Dependabot activé sur le repo
[ ] Versions pinnées dans requirements.txt (pas de >=)
[ ] Playwright version fixée (pas de breaking changes surprise)
```

---

### A07 — Authentication Failures

**Risque :** bypass auth, session hijacking, token leaks.

**Protections StoreMD :**

```python
# JWT Supabase : validation signature + expiration
user = supabase.auth.get_user(token)

# OAuth state : anti-CSRF avec nonce TTL 5 min
state = secrets.token_urlsafe(32)
await redis.setex(f"oauth_state:{state}", 300, shop)

# HMAC webhooks : constant-time comparison
hmac.compare_digest(computed, received)  # anti timing attack

# Session : cookies httpOnly + secure + SameSite
# Géré par @supabase/ssr côté frontend
```

**Checklist review :**
```
[ ] Chaque route protégée a le middleware JWT
[ ] OAuth state validé avec constant-time comparison
[ ] Webhooks validés par HMAC/signature avant traitement
[ ] Pas de token dans les URL (query params)
[ ] Pas de token dans les logs
[ ] Session cookies : httpOnly, secure, SameSite
```

---

### A08 — Data Integrity Failures

**Risque :** désérialisation non sécurisée, pipelines CI/CD compromis.

**Protections StoreMD :**

```python
# Pydantic valide TOUT input avant traitement
# Pas de pickle, pas de yaml.load() unsafe
# JSON uniquement pour la sérialisation

# CI/CD : GitHub Actions avec permissions minimales
# Pas de secrets dans les logs de build
# Branch protection sur main
```

**Checklist review :**
```
[ ] Pas de pickle, marshal, yaml.unsafe_load
[ ] JSON.parse/json.loads uniquement (pas de eval)
[ ] GitHub branch protection activée sur main
[ ] Secrets GitHub Actions dans les secrets, pas dans le workflow
```

---

### A09 — Logging & Monitoring Failures

**Risque :** pas de logs, pas d'alertes, attaques non détectées.

**Protections StoreMD :**

```python
# structlog : logs structurés avec contexte
logger.info("scan_completed", store_id=store_id, score=72)
logger.warning("hmac_validation_failed", shop=shop_domain)
logger.error("app_error", code=exc.code, message=exc.message)

# Sentry : capture automatique des exceptions non gérées
# LangSmith : traçage des appels Claude API (coûts, latence)

# Alertes : Sentry notifications sur nouvelles exceptions
```

**Checklist review :**
```
[ ] Chaque endpoint/service a des logs structurés
[ ] Les erreurs de sécurité sont loggées (HMAC fail, JWT invalid, rate limit)
[ ] Sentry configuré et testé
[ ] Pas de données sensibles dans les logs
[ ] Les logs incluent le contexte (store_id, merchant_id, scan_id)
```

---

### A10 — Server-Side Request Forgery (SSRF)

**Risque :** le backend fait des requêtes vers des URLs contrôlées par l'attaquant.

**Protections StoreMD :**

```python
# Shop domain : validé par regex AVANT toute requête
SHOP_DOMAIN_REGEX = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9\-]*\.myshopify\.com$")

# Pas de requête vers des URLs fournies par l'utilisateur
# (sauf broken_links scanner qui fait des HEAD requests — pas de body)

# Playwright : navigue uniquement sur le storefront public du merchant
# Pas de navigation vers des URLs arbitraires
```

**Checklist review :**
```
[ ] Les URLs Shopify sont construites à partir du shop domain validé
[ ] Pas de fetch/requests vers des URLs fournies par l'utilisateur
[ ] Playwright ne navigue que vers le domaine du store
[ ] Les redirects sont validés (pas d'open redirect)
```

---

## CODE REVIEW CHECKLIST — RÉSUMÉ

À vérifier sur CHAQUE PR :

```
ACCESS CONTROL
[ ] Middleware auth sur les routes protégées
[ ] Queries filtrent par merchant_id
[ ] Pas d'accès cross-merchant

CRYPTO
[ ] Tokens chiffrés (Fernet)
[ ] Pas de secrets dans le code/logs

INJECTION
[ ] Pas de SQL brut
[ ] Pas de dangerouslySetInnerHTML
[ ] Inputs validés (Pydantic)

AUTH
[ ] JWT validé
[ ] HMAC vérifié (webhooks)
[ ] Rate limiting actif

DATA
[ ] JSON uniquement (pas de pickle)
[ ] Pas d'eval/exec

LOGGING
[ ] Logs structurés avec contexte
[ ] Pas de PII/secrets dans les logs

INFRA
[ ] CORS whitelist
[ ] Headers sécurité
[ ] Dependencies à jour
```
