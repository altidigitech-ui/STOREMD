# SECURITY.md — Sécurité StoreMD

> **Toutes les règles de sécurité du projet.**
> **Chaque pattern a du code. Pas de théorie sans implémentation.**

---

## 1. TOKENS SHOPIFY — FERNET ENCRYPTION

Les access tokens Shopify sont la clé d'accès au store du merchant. Compromis = accès total au store. Chiffrés Fernet AVANT insertion en DB, déchiffrés au runtime uniquement en mémoire.

```python
# app/core/security.py

from cryptography.fernet import Fernet, InvalidToken
from app.config import settings

_fernet = Fernet(settings.FERNET_KEY.encode())

def encrypt_token(token: str) -> str:
    """Chiffre un token Shopify pour stockage DB."""
    return _fernet.encrypt(token.encode()).decode()

def decrypt_token(encrypted: str) -> str:
    """Déchiffre un token Shopify depuis la DB."""
    try:
        return _fernet.decrypt(encrypted.encode()).decode()
    except InvalidToken:
        raise AuthError(
            code=ErrorCode.TOKEN_DECRYPT_FAILED,
            message="Failed to decrypt Shopify token — key rotation needed?",
            status_code=500,
        )
```

**Règles :**
- JAMAIS de token en clair dans la DB, les logs, les réponses API, ou les messages d'erreur
- `FERNET_KEY` dans les env vars Railway, JAMAIS dans le code, JAMAIS commité
- Rotation de clé : générer une nouvelle clé, re-chiffrer tous les tokens avec la nouvelle, supprimer l'ancienne
- En cas de compromission suspectée : révoquer tous les tokens via Shopify API + re-chiffrer

```python
# Génération d'une clé Fernet (à faire UNE fois, stocker dans env vars)
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(key.decode())  # → mettre dans FERNET_KEY
```

---

## 2. HMAC VALIDATION — WEBHOOKS SHOPIFY

Chaque webhook Shopify contient un header `X-Shopify-Hmac-Sha256`. Le backend DOIT valider ce HMAC AVANT de traiter le payload. Un webhook sans HMAC valide = rejeté silencieusement.

```python
# app/api/middleware/hmac.py

import hmac
import hashlib
import base64
from fastapi import Request
from app.config import settings
from app.core.exceptions import AuthError, ErrorCode

async def validate_shopify_hmac(request: Request) -> bool:
    """Valide le HMAC d'un webhook Shopify.
    
    DOIT être appelé AVANT tout traitement du payload.
    Utilise hmac.compare_digest() pour la comparaison constant-time
    (anti timing attack).
    """
    body = await request.body()
    received_hmac = request.headers.get("X-Shopify-Hmac-Sha256", "")

    if not received_hmac:
        raise AuthError(
            code=ErrorCode.HMAC_MISSING,
            message="Missing HMAC header",
            status_code=401,
        )

    computed = hmac.new(
        settings.SHOPIFY_API_SECRET.encode(),
        body,
        hashlib.sha256,
    ).digest()

    computed_b64 = base64.b64encode(computed).decode()

    if not hmac.compare_digest(computed_b64, received_hmac):
        logger.warning(
            "hmac_validation_failed",
            shop=request.headers.get("X-Shopify-Shop-Domain", "unknown"),
            topic=request.headers.get("X-Shopify-Topic", "unknown"),
        )
        raise AuthError(
            code=ErrorCode.HMAC_INVALID,
            message="Invalid HMAC",
            status_code=401,
        )

    return True
```

**Règles :**
- `hmac.compare_digest()` OBLIGATOIRE (constant-time, anti timing attack) — jamais `==`
- Logger le shop + topic en cas d'échec (pour détecter des attaques), mais JAMAIS le payload
- Vérifier aussi `X-Shopify-Shop-Domain` et `X-Shopify-Topic` pour le routing
- Idempotency : stocker le webhook ID dans `webhook_events` avant traitement, skip si déjà vu

```python
# app/api/routes/webhooks_shopify.py

@router.post("/webhooks/shopify")
async def handle_shopify_webhook(
    request: Request,
    supabase: SupabaseClient = Depends(get_supabase_service),
):
    # 1. Valider HMAC
    await validate_shopify_hmac(request)

    # 2. Parser le payload
    body = await request.body()
    payload = json.loads(body)
    webhook_id = request.headers.get("X-Shopify-Webhook-Id", "")
    topic = request.headers.get("X-Shopify-Topic", "")
    shop = request.headers.get("X-Shopify-Shop-Domain", "")

    # 3. Idempotency check
    existing = await supabase.table("webhook_events").select("id").eq(
        "source", "shopify"
    ).eq("external_id", webhook_id).maybe_single().execute()

    if existing.data:
        return {"status": "already_processed"}

    # 4. Stocker le webhook
    await supabase.table("webhook_events").insert({
        "source": "shopify",
        "external_id": webhook_id,
        "topic": topic,
        "shop_domain": shop,
        "payload": payload,
    }).execute()

    # 5. Dispatch le traitement en background
    process_shopify_webhook.delay(webhook_id)

    return {"status": "accepted"}
```

---

## 3. STRIPE WEBHOOK VALIDATION

Même principe que Shopify, mais avec la librairie Stripe native.

```python
# app/api/routes/webhooks_stripe.py

import stripe
from app.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

@router.post("/webhooks/stripe")
async def handle_stripe_webhook(request: Request):
    body = await request.body()
    sig_header = request.headers.get("Stripe-Signature", "")

    try:
        event = stripe.Webhook.construct_event(
            body, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        logger.warning("stripe_webhook_invalid_signature")
        raise AuthError(
            code=ErrorCode.STRIPE_SIGNATURE_INVALID,
            message="Invalid Stripe signature",
            status_code=401,
        )
    except ValueError:
        raise AuthError(
            code=ErrorCode.STRIPE_PAYLOAD_INVALID,
            message="Invalid Stripe payload",
            status_code=400,
        )

    # Idempotency
    existing = await supabase.table("webhook_events").select("id").eq(
        "source", "stripe"
    ).eq("external_id", event["id"]).maybe_single().execute()

    if existing.data:
        return {"status": "already_processed"}

    # Stocker + dispatch
    await supabase.table("webhook_events").insert({
        "source": "stripe",
        "external_id": event["id"],
        "topic": event["type"],
        "payload": event["data"],
    }).execute()

    process_stripe_webhook.delay(event["id"])

    return {"status": "accepted"}
```

---

## 4. JWT SUPABASE — AUTH MIDDLEWARE

Chaque requête API protégée passe par le middleware JWT. Le token est émis par Supabase Auth lors du login (Shopify OAuth → Supabase session).

```python
# app/api/middleware/auth.py

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.supabase import get_supabase_client
from app.core.exceptions import AuthError, ErrorCode

security = HTTPBearer()

async def get_current_merchant(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Merchant:
    """Extrait et valide le merchant depuis le JWT Supabase."""
    token = credentials.credentials

    supabase = get_supabase_client()

    try:
        user_response = supabase.auth.get_user(token)
        user = user_response.user
    except Exception as exc:
        raise AuthError(
            code=ErrorCode.JWT_INVALID,
            message="Invalid or expired token",
            status_code=401,
        )

    if not user:
        raise AuthError(
            code=ErrorCode.JWT_INVALID,
            message="User not found",
            status_code=401,
        )

    # Charger le profil merchant depuis la DB
    result = await supabase.table("merchants").select("*").eq(
        "id", user.id
    ).single().execute()

    if not result.data:
        raise AuthError(
            code=ErrorCode.MERCHANT_NOT_FOUND,
            message="Merchant profile not found",
            status_code=401,
        )

    return Merchant(**result.data)


async def get_current_store(
    store_id: str,
    merchant: Merchant = Depends(get_current_merchant),
) -> Store:
    """Vérifie que le merchant a accès au store demandé."""
    result = await supabase.table("stores").select("*").eq(
        "id", store_id
    ).eq("merchant_id", merchant.id).single().execute()

    if not result.data:
        raise AuthError(
            code=ErrorCode.STORE_NOT_FOUND,
            message="Store not found or access denied",
            status_code=404,
        )

    return Store(**result.data)
```

**Règles :**
- Token dans le header `Authorization: Bearer <jwt>`
- Supabase valide la signature + expiration automatiquement
- Le middleware injecte le `Merchant` (et optionnellement le `Store`) dans chaque route protégée
- Double vérification : JWT valide + merchant existe en DB + store appartient au merchant (RLS en backup)

---

## 5. ROW LEVEL SECURITY (RLS)

Chaque table a RLS activé. Chaque merchant ne voit que SES données. C'est la dernière ligne de défense — même si le code applicatif a un bug, le RLS empêche l'accès aux données d'un autre merchant.

```sql
-- Pattern standard
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;

CREATE POLICY "merchants_own_{table}" ON {table}
    FOR ALL USING (merchant_id = auth.uid());
```

**Exception :**
- `webhook_events` : accès `service_role` uniquement (le backend traite les webhooks pour tous les merchants)

**Tester le RLS :**

```sql
-- Se connecter en tant qu'un merchant (via Supabase SQL editor)
SET request.jwt.claims = '{"sub": "merchant-uuid-1"}';
SET role = 'authenticated';

-- Vérifier qu'on ne voit que ses données
SELECT * FROM scans;  -- Ne doit retourner que les scans de merchant-uuid-1

-- Vérifier qu'on ne peut pas voir les données d'un autre merchant
SELECT * FROM scans WHERE merchant_id = 'merchant-uuid-2';  -- Doit retourner 0 rows
```

---

## 6. RATE LIMITING

Redis-based, par merchant, par endpoint. Protège contre l'abus et les bots.

```python
# app/api/middleware/rate_limit.py

from app.services.redis import get_redis

async def rate_limit(
    merchant_id: str,
    endpoint: str,
    limit: int,
    window_seconds: int = 60,
) -> None:
    """Rate limit par merchant par endpoint.
    
    Raises AppError(429) si la limite est dépassée.
    """
    redis = get_redis()
    key = f"ratelimit:{merchant_id}:{endpoint}"

    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, window_seconds)

    if current > limit:
        ttl = await redis.ttl(key)
        raise AppError(
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message="Rate limit exceeded",
            status_code=429,
            context={"retry_after": ttl, "limit": limit, "window": window_seconds},
        )
```

**Limites par plan :**

| Ressource | Free | Starter | Pro | Agency |
|-----------|------|---------|-----|--------|
| API calls / minute | 30 | 60 | 120 | 300 |
| Scan triggers / jour | 0 (2/mois) | 1 | 1 | 10 |
| Browser tests / jour | 0 | 0 | 1 | 10 |
| Fix applies / jour | 0 | 5 | 20 | 100 |

**Webhooks :** pas de rate limit sur les webhooks entrants (Shopify/Stripe contrôlent le débit).

---

## 7. SHOPIFY OAUTH FLOW

### Flow sécurisé (10 étapes)

```
1. Merchant clique "Add app" sur le Shopify App Store
2. Shopify redirige vers GET /api/v1/auth/install?shop=mystore.myshopify.com
3. Backend valide le shop domain (regex, pas d'injection)
4. Backend génère un state parameter (nonce) et le stocke en Redis (TTL 5 min)
5. Backend redirige vers Shopify OAuth consent screen avec state + scopes
6. Merchant accepte les permissions
7. Shopify redirige vers GET /api/v1/auth/callback?code=xxx&state=yyy&shop=zzz
8. Backend valide le state parameter (anti-CSRF, compare avec Redis)
9. Backend échange le code pour un access token (POST Shopify /admin/oauth/access_token)
10. Backend chiffre le token (Fernet) → stocke en DB → crée la session Supabase
```

```python
# app/api/routes/auth.py

import secrets
from app.core.security import encrypt_token

@router.get("/auth/install")
async def install(shop: str, redis: Redis = Depends(get_redis)):
    # Valider le shop domain
    if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9\-]*\.myshopify\.com$", shop):
        raise AuthError(
            code=ErrorCode.INVALID_SHOP_DOMAIN,
            message="Invalid shop domain",
            status_code=400,
        )

    # Générer le state (anti-CSRF)
    state = secrets.token_urlsafe(32)
    await redis.setex(f"oauth_state:{state}", 300, shop)  # TTL 5 min

    # Rediriger vers Shopify
    redirect_url = (
        f"https://{shop}/admin/oauth/authorize"
        f"?client_id={settings.SHOPIFY_API_KEY}"
        f"&scope={settings.SHOPIFY_SCOPES}"
        f"&redirect_uri={settings.BACKEND_URL}/api/v1/auth/callback"
        f"&state={state}"
    )
    return RedirectResponse(redirect_url)


@router.get("/auth/callback")
async def callback(
    code: str, state: str, shop: str,
    redis: Redis = Depends(get_redis),
):
    # 1. Valider le state (anti-CSRF)
    stored_shop = await redis.get(f"oauth_state:{state}")
    if not stored_shop or stored_shop.decode() != shop:
        raise AuthError(
            code=ErrorCode.OAUTH_STATE_INVALID,
            message="Invalid OAuth state — possible CSRF",
            status_code=403,
        )
    await redis.delete(f"oauth_state:{state}")

    # 2. Échanger le code pour un token
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://{shop}/admin/oauth/access_token",
            json={
                "client_id": settings.SHOPIFY_API_KEY,
                "client_secret": settings.SHOPIFY_API_SECRET,
                "code": code,
            },
        )
        response.raise_for_status()
        data = response.json()

    access_token = data["access_token"]
    scopes = data["scope"].split(",")

    # 3. Chiffrer et stocker
    encrypted_token = encrypt_token(access_token)

    # 4. Créer/mettre à jour le merchant + store dans Supabase
    # ... (via service_role, le merchant n'est pas encore authentifié)

    # 5. Créer la session Supabase et rediriger vers le dashboard
    # ...
```

### Validation du shop domain

```python
SHOP_DOMAIN_REGEX = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9\-]*\.myshopify\.com$")

def validate_shop_domain(shop: str) -> bool:
    """Valide qu'un shop domain est un domaine Shopify légitime.
    
    Empêche :
    - Open redirect attacks (redirection vers un site malveillant)
    - SSRF (server-side request forgery)
    - SQL injection via le shop parameter
    """
    return bool(SHOP_DOMAIN_REGEX.match(shop))
```

---

## 8. APP UNINSTALL — CLEANUP

Quand un merchant désinstalle l'app, le cleanup est IMMÉDIAT et COMPLET.

```python
# Webhook handler pour app/uninstalled

async def handle_app_uninstalled(shop_domain: str, payload: dict):
    """Cleanup complet après désinstallation."""

    # 1. Révoquer le billing Stripe IMMÉDIATEMENT
    merchant = await get_merchant_by_shop(shop_domain)
    if merchant and merchant.stripe_subscription_id:
        stripe.Subscription.cancel(merchant.stripe_subscription_id)
        logger.info("subscription_canceled", merchant_id=merchant.id)

    # 2. Marquer le store comme uninstalled
    await supabase.table("stores").update({
        "status": "uninstalled",
        "uninstalled_at": datetime.now(UTC).isoformat(),
    }).eq("shopify_shop_domain", shop_domain).execute()

    # 3. Supprimer le token Shopify (plus besoin)
    await supabase.table("merchants").update({
        "shopify_access_token_encrypted": None,
    }).eq("shopify_shop_domain", shop_domain).execute()

    # 4. Email de confirmation
    await send_uninstall_confirmation_email(merchant)

    # 5. Planifier la suppression des données dans 30 jours (GDPR)
    schedule_data_deletion.apply_async(
        args=[merchant.id],
        countdown=30 * 24 * 3600,  # 30 jours
    )

    logger.info("app_uninstalled", shop=shop_domain, merchant_id=merchant.id)
```

### Mandatory Shopify Webhooks

Shopify exige que ces webhooks soient implémentés pour la certification :

| Webhook | Ce qu'on fait |
|---------|-------------|
| `app/uninstalled` | Cleanup complet (ci-dessus) |
| `customers/data_request` | Exporter toutes les données du merchant en JSON, envoyer par email |
| `customers/redact` | Supprimer toutes les données d'un client spécifique du merchant |
| `shop/redact` | Supprimer TOUTES les données du store (appelé 48h après uninstall) |

---

## 9. INPUT VALIDATION

```python
# Pydantic v2 valide TOUS les inputs API

from pydantic import BaseModel, Field, field_validator

class ScanRequest(BaseModel):
    modules: list[str] = Field(..., min_length=1, max_length=5)

    @field_validator("modules")
    @classmethod
    def validate_modules(cls, v: list[str]) -> list[str]:
        allowed = {"health", "listings", "agentic", "compliance", "browser"}
        invalid = set(v) - allowed
        if invalid:
            raise ValueError(f"Invalid modules: {invalid}")
        return v

class FeedbackRequest(BaseModel):
    issue_id: str = Field(..., min_length=1)
    accepted: bool
    reason: str | None = Field(None, max_length=500)
    reason_category: str | None = None

    @field_validator("reason_category")
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        if v is None:
            return v
        allowed = {"not_relevant", "too_risky", "will_do_later",
                    "disagree", "already_fixed", "other"}
        if v not in allowed:
            raise ValueError(f"Invalid category: {v}")
        return v
```

**Règles :**
- TOUT input utilisateur passe par Pydantic — routes, query params, body
- SQL toujours paramétrisé (Supabase client le fait par défaut via PostgREST)
- Pas de `eval()`, pas de `exec()`, pas de `__import__()`
- XSS : Next.js auto-escape par défaut, pas de `dangerouslySetInnerHTML`
- URLs : valider les shop domains, ne jamais construire d'URL à partir d'input non validé

---

## 10. CORS

```python
# app/main.py

from fastapi.middleware.cors import CORSMiddleware

ALLOWED_ORIGINS = [
    "https://storemd.com",
    "https://www.storemd.com",
    "https://storemd.vercel.app",
]

if settings.APP_ENV == "development":
    ALLOWED_ORIGINS.append("http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,  # Cache preflight 10 min
)
```

**Règles :**
- JAMAIS de wildcard `*` en production
- Whitelist explicite des domaines autorisés
- `allow_credentials=True` nécessaire pour les cookies de session

---

## 11. SECRETS MANAGEMENT

| Secret | Stocké dans | Accédé par |
|--------|------------|-----------|
| `SHOPIFY_API_SECRET` | Railway env vars | Backend only |
| `SUPABASE_SERVICE_ROLE_KEY` | Railway env vars | Backend only |
| `STRIPE_SECRET_KEY` | Railway env vars | Backend only |
| `STRIPE_WEBHOOK_SECRET` | Railway env vars | Backend only |
| `ANTHROPIC_API_KEY` | Railway env vars | Backend only |
| `FERNET_KEY` | Railway env vars | Backend only |
| `MEM0_API_KEY` | Railway env vars | Backend only |
| `RESEND_API_KEY` | Railway env vars | Backend only |
| `SUPABASE_ANON_KEY` | Vercel env vars | Frontend (public, safe) |
| `NEXT_PUBLIC_SUPABASE_URL` | Vercel env vars | Frontend (public, safe) |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | Vercel env vars | Frontend (public, safe) |

**Règles :**
- `NEXT_PUBLIC_` = seules vars exposées au frontend (publishable keys uniquement)
- `.env` dans `.gitignore` TOUJOURS
- JAMAIS de secret dans les commits, les logs, les messages d'erreur, les réponses API
- Rotation régulière des clés (Fernet, API keys) : documenter la procédure

---

## 12. LOGGING SÉCURISÉ

```python
import structlog

logger = structlog.get_logger()

# ✅ BON — logger le contexte métier sans données sensibles
logger.info("scan_completed", store_id=store_id, score=72, duration_ms=4200)
logger.info("merchant_created", shop_domain="mystore.myshopify.com")
logger.warning("shopify_rate_limit", shop_domain=shop_domain, retry_after=2.0)

# ❌ INTERDIT — JAMAIS de secrets dans les logs
logger.info("auth", token=access_token)                    # ❌
logger.info("webhook", payload=webhook_payload)            # ❌ (peut contenir des PII)
logger.info("merchant", email="john@example.com")          # ❌
logger.info("billing", stripe_key=settings.STRIPE_SECRET)  # ❌

# ✅ Masquer les données sensibles si nécessaire
def mask_email(email: str) -> str:
    local, domain = email.split("@")
    return f"{local[:2]}***@{domain}"

logger.info("merchant_created", email=mask_email(merchant.email))
# → "merchant_created email=jo***@example.com"
```

---

## 13. HEADERS DE SÉCURITÉ

Configurés dans Next.js (`next.config.js`) et/ou le reverse proxy :

```javascript
// next.config.js
const securityHeaders = [
    { key: 'X-Content-Type-Options', value: 'nosniff' },
    { key: 'X-Frame-Options', value: 'DENY' },
    { key: 'X-XSS-Protection', value: '1; mode=block' },
    { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
    { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
    {
        key: 'Content-Security-Policy',
        value: "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.shopify.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' https://api.storemd.com https://*.supabase.co https://*.stripe.com;",
    },
    { key: 'Strict-Transport-Security', value: 'max-age=63072000; includeSubDomains; preload' },
];

module.exports = {
    async headers() {
        return [{ source: '/(.*)', headers: securityHeaders }];
    },
};
```

---

## CHECKLIST SÉCURITÉ PRE-LAUNCH

```
Authentication & Authorization
[ ] Fernet encryption sur tous les tokens Shopify
[ ] HMAC validation sur tous les webhooks Shopify
[ ] Stripe signature validation sur tous les webhooks Stripe
[ ] JWT validation Supabase sur chaque route protégée
[ ] RLS activé et TESTÉ sur chaque table (14 tables)
[ ] Rate limiting fonctionnel sur tous les endpoints
[ ] Plan checking avant chaque feature payante

Data Protection
[ ] .env dans .gitignore
[ ] Aucun secret dans le code, les commits, ou les logs
[ ] Tokens Shopify jamais en clair nulle part
[ ] PII (emails) masqués dans les logs
[ ] GDPR : données supprimées 30 jours après uninstall

Network
[ ] CORS configuré (whitelist, pas de wildcard)
[ ] HTTPS everywhere (Railway + Vercel par défaut)
[ ] Security headers configurés (CSP, HSTS, X-Frame-Options)

Shopify Compliance
[ ] Mandatory webhooks implémentés (app/uninstalled, customers/data_request, customers/redact, shop/redact)
[ ] Shop domain validé par regex sur chaque entrée
[ ] OAuth state parameter (anti-CSRF) avec TTL 5 min
[ ] Scopes minimales demandées (mais incluant write pour One-Click Fix)

Input Validation
[ ] Pydantic validation sur chaque endpoint
[ ] SQL paramétrisé (Supabase client)
[ ] Pas de eval(), exec(), __import__()
[ ] Pas de dangerouslySetInnerHTML dans React

Monitoring
[ ] Sentry configuré pour capturer les erreurs non-gérées
[ ] Alertes sur les échecs HMAC répétés (possible attaque)
[ ] Alertes sur les rate limits dépassés fréquemment
```
