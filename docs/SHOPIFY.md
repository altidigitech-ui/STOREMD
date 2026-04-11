# SHOPIFY.md — Intégration Shopify StoreMD

> **Tout ce qui concerne l'API Shopify : OAuth, GraphQL, webhooks, scopes, rate limits.**
> **Pour les patterns de code, voir `.claude/skills/shopify-api/SKILL.md`.**
> **Pour la sécurité (HMAC, tokens), voir `docs/SECURITY.md`.**

---

## VUE D'ENSEMBLE

StoreMD est une **app Shopify embedded** installée via le Shopify App Store. Le merchant l'installe en 1 clic, accepte les permissions OAuth, et l'app a accès à son store via l'API Admin GraphQL.

```
Shopify App Store
    │
    │ Merchant clique "Add app"
    ▼
OAuth Flow (10 étapes)
    │
    │ Access token obtenu + chiffré Fernet
    ▼
API Admin GraphQL (version 2026-01)
    │
    ├── Données store : thème, apps, produits, pages
    ├── Données commerce : commandes, analytics
    └── Mutations : metafields, redirects, theme files
    │
    ▼
Webhooks (8 topics)
    │
    ├── app/uninstalled → cleanup complet
    ├── products/create → agentic monitoring
    ├── products/update → agentic monitoring
    ├── themes/update → collection backup + rescan
    └── ... (mandatory + billing)
```

---

## OAUTH FLOW — 10 ÉTAPES

### Diagramme

```
MERCHANT                  STOREMD BACKEND              SHOPIFY
   │                           │                          │
   │  1. Clique "Add app"      │                          │
   │──────────────────────────►│                          │
   │                           │                          │
   │  2. GET /auth/install     │                          │
   │     ?shop=x.myshopify.com │                          │
   │──────────────────────────►│                          │
   │                           │                          │
   │                           │  3. Valide shop domain   │
   │                           │     (regex)              │
   │                           │                          │
   │                           │  4. Génère state (nonce) │
   │                           │     Stocke Redis TTL 5m  │
   │                           │                          │
   │  5. Redirect 302          │                          │
   │◄──────────────────────────│                          │
   │                           │                          │
   │  6. Consent screen        │                          │
   │     (scopes affichées)    │                          │
   │──────────────────────────────────────────────────────►│
   │                           │                          │
   │                           │  7. Callback             │
   │                           │     ?code=xxx&state=yyy  │
   │◄──────────────────────────────────────────────────────│
   │                           │                          │
   │  8. GET /auth/callback    │                          │
   │──────────────────────────►│                          │
   │                           │                          │
   │                           │  9. Valide state (Redis) │
   │                           │     Échange code → token │
   │                           │────────────────────────► │
   │                           │◄────────────────────────│
   │                           │                          │
   │                           │ 10. Chiffre token Fernet │
   │                           │     Stocke en DB         │
   │                           │     Crée session Supabase│
   │                           │     Enregistre webhooks  │
   │                           │                          │
   │ 11. Redirect → dashboard  │                          │
   │◄──────────────────────────│                          │
```

### Implémentation détaillée

```python
# app/api/routes/auth.py

import re
import secrets
import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from app.config import settings
from app.core.security import encrypt_token
from app.core.exceptions import AuthError, ErrorCode

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

SHOP_DOMAIN_REGEX = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9\-]*\.myshopify\.com$")


@router.get("/install")
async def install(shop: str, redis: Redis = Depends(get_redis)):
    """Étape 2-5 : valider le shop, générer state, redirect vers Shopify."""

    # Étape 3 — Valider le shop domain
    if not SHOP_DOMAIN_REGEX.match(shop):
        raise AuthError(
            code=ErrorCode.INVALID_SHOP_DOMAIN,
            message=f"Invalid shop domain: {shop}",
            status_code=400,
        )

    # Étape 4 — Générer le state anti-CSRF
    state = secrets.token_urlsafe(32)
    await redis.setex(f"oauth_state:{state}", 300, shop)  # TTL 5 min

    # Étape 5 — Redirect vers Shopify consent
    scopes = settings.SHOPIFY_SCOPES
    redirect_uri = f"{settings.BACKEND_URL}/api/v1/auth/callback"

    auth_url = (
        f"https://{shop}/admin/oauth/authorize"
        f"?client_id={settings.SHOPIFY_API_KEY}"
        f"&scope={scopes}"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
    )

    logger.info("oauth_install_redirect", shop=shop)
    return RedirectResponse(auth_url)


@router.get("/callback")
async def callback(
    code: str, state: str, shop: str, hmac: str,
    redis: Redis = Depends(get_redis),
    supabase: SupabaseClient = Depends(get_supabase_service),
):
    """Étape 8-11 : valider state, échanger code, stocker token, redirect."""

    # Étape 9a — Valider le state (anti-CSRF)
    stored_shop = await redis.get(f"oauth_state:{state}")
    if not stored_shop or stored_shop.decode() != shop:
        raise AuthError(
            code=ErrorCode.OAUTH_STATE_INVALID,
            message="Invalid or expired OAuth state",
            status_code=403,
        )
    await redis.delete(f"oauth_state:{state}")

    # Étape 9b — Valider le shop domain
    if not SHOP_DOMAIN_REGEX.match(shop):
        raise AuthError(
            code=ErrorCode.INVALID_SHOP_DOMAIN,
            message=f"Invalid shop domain: {shop}",
            status_code=400,
        )

    # Étape 9c — Échanger le code pour un access token
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"https://{shop}/admin/oauth/access_token",
            json={
                "client_id": settings.SHOPIFY_API_KEY,
                "client_secret": settings.SHOPIFY_API_SECRET,
                "code": code,
            },
        )

        if response.status_code != 200:
            raise AuthError(
                code=ErrorCode.OAUTH_CODE_EXCHANGE_FAILED,
                message=f"Code exchange failed: {response.status_code}",
                status_code=502,
            )

        data = response.json()

    access_token = data.get("access_token")
    granted_scopes = data.get("scope", "").split(",")

    if not access_token:
        raise AuthError(
            code=ErrorCode.OAUTH_TOKEN_MISSING,
            message="No access token in Shopify response",
            status_code=502,
        )

    # Étape 10a — Chiffrer le token
    encrypted_token = encrypt_token(access_token)

    # Étape 10b — Créer ou mettre à jour le merchant + store
    merchant = await upsert_merchant(supabase, shop, encrypted_token, granted_scopes)
    store = await upsert_store(supabase, merchant["id"], shop, access_token)

    # Étape 10c — Enregistrer les webhooks Shopify
    shopify = ShopifyClient(shop, encrypted_token)
    await register_webhooks(shopify)

    # Étape 10d — Créer la session Supabase Auth
    session = await create_supabase_session(supabase, merchant)

    # Étape 11 — Redirect vers le dashboard (ou onboarding si premier install)
    if merchant.get("onboarding_completed"):
        redirect_url = f"{settings.APP_URL}/dashboard?token={session.access_token}"
    else:
        redirect_url = f"{settings.APP_URL}/onboarding?token={session.access_token}"

    logger.info("oauth_completed", shop=shop, merchant_id=merchant["id"])
    return RedirectResponse(redirect_url)
```

### Helpers OAuth

```python
async def upsert_merchant(
    supabase: SupabaseClient, shop: str,
    encrypted_token: str, scopes: list[str]
) -> dict:
    """Crée ou met à jour le merchant lors de l'OAuth."""
    existing = await supabase.table("merchants").select("*").eq(
        "shopify_shop_domain", shop
    ).maybe_single().execute()

    if existing.data:
        # Merchant existe → update le token et les scopes
        await supabase.table("merchants").update({
            "shopify_access_token_encrypted": encrypted_token,
            "shopify_scopes": scopes,
            "shopify_installed_at": datetime.now(UTC).isoformat(),
        }).eq("id", existing.data["id"]).execute()
        return existing.data
    else:
        # Nouveau merchant → créer via Supabase Auth
        # (le trigger on_auth_user_created crée le profil merchant)
        auth_user = await create_auth_user(supabase, shop)
        await supabase.table("merchants").update({
            "shopify_shop_domain": shop,
            "shopify_access_token_encrypted": encrypted_token,
            "shopify_scopes": scopes,
            "shopify_installed_at": datetime.now(UTC).isoformat(),
        }).eq("id", auth_user.id).execute()

        result = await supabase.table("merchants").select("*").eq(
            "id", auth_user.id
        ).single().execute()
        return result.data


async def upsert_store(
    supabase: SupabaseClient, merchant_id: str,
    shop: str, access_token: str
) -> dict:
    """Crée ou met à jour le store et charge les infos depuis Shopify."""
    # Fetch shop info depuis Shopify API
    shopify = ShopifyClient(shop, encrypt_token(access_token))
    shop_data = await shopify.graphql("""
        query {
            shop {
                name
                primaryDomain { url host }
                plan { displayName }
                currencyCode
                billingAddress { countryCodeV2 }
                productsCount { count }
            }
        }
    """)

    shop_info = shop_data["shop"]

    store_data = {
        "merchant_id": merchant_id,
        "shopify_shop_domain": shop,
        "name": shop_info["name"],
        "primary_domain": shop_info["primaryDomain"]["host"],
        "shopify_plan": shop_info["plan"]["displayName"].lower(),
        "currency": shop_info["currencyCode"],
        "country": shop_info["billingAddress"]["countryCodeV2"],
        "products_count": shop_info["productsCount"]["count"],
        "status": "active",
    }

    # Fetch theme info
    theme_data = await shopify.graphql("""
        query {
            themes(first: 1, roles: MAIN) {
                edges {
                    node { id name role }
                }
            }
        }
    """)
    themes = theme_data["themes"]["edges"]
    if themes:
        store_data["theme_name"] = themes[0]["node"]["name"]
        store_data["theme_id"] = themes[0]["node"]["id"]

    # Fetch apps count
    apps_data = await shopify.graphql("""
        query { appInstallations(first: 1) { totalCount } }
    """)
    store_data["apps_count"] = apps_data["appInstallations"]["totalCount"]

    # Upsert
    existing = await supabase.table("stores").select("id").eq(
        "shopify_shop_domain", shop
    ).eq("merchant_id", merchant_id).maybe_single().execute()

    if existing.data:
        await supabase.table("stores").update(store_data).eq(
            "id", existing.data["id"]
        ).execute()
        store_data["id"] = existing.data["id"]
    else:
        result = await supabase.table("stores").insert(store_data).execute()
        store_data["id"] = result.data[0]["id"]

    return store_data
```

---

## SCOPES

### Scopes demandées

```
read_products       → Catalogue scan, listing analyzer, agentic readiness, product count
write_products      → One-Click Fix (alt text, metafields, descriptions, GTIN)
read_themes         → Theme analysis, residue detection, code weight, schema markup
write_themes        → One-Click Fix (supprimer code résiduel d'apps désinstallées)
read_orders         → Traffic analytics, bot filter, revenue data (listing priorisation)
read_online_store   → Pages, blog posts, navigation (broken links, content)
```

### Scopes à NE PAS demander

| Scope | Pourquoi non |
|-------|-------------|
| `read_apps` | Nécessite Shopify Partner approval. Utiliser `appInstallations` query à la place. |
| `write_orders` | Dangereuse. StoreMD ne modifie jamais les commandes. |
| `write_checkouts` | Dangereuse. StoreMD ne touche jamais le checkout. |
| `read_customers` | Pas nécessaire en V1. Pourrait être ajouté pour le bot filter avancé. |
| `write_script_tags` | StoreMD n'injecte pas de scripts dans le store. |

### Vérification des scopes au runtime

```python
async def verify_scopes(shopify: ShopifyClient, required: list[str]) -> bool:
    """Vérifie que l'app a les scopes nécessaires pour une opération."""
    # Les scopes sont stockées en DB lors de l'OAuth
    merchant = await get_merchant_by_shop(shopify.shop_domain)
    granted = set(merchant.get("shopify_scopes", []))
    missing = set(required) - granted

    if missing:
        raise ShopifyError(
            code=ErrorCode.SHOPIFY_SCOPE_INSUFFICIENT,
            message=f"Missing scopes: {', '.join(missing)}",
            status_code=403,
            context={"missing_scopes": list(missing)},
        )
    return True

# Usage dans One-Click Fix
async def apply_alt_text_fix(shopify: ShopifyClient, product_id: str, alt_text: str):
    await verify_scopes(shopify, ["write_products"])
    # ... appliquer le fix
```

---

## GRAPHQL — API VERSION

```python
SHOPIFY_API_VERSION = "2026-01"  # Depuis settings / env vars
```

Shopify déprécie les versions après 12 mois. Surveiller les annonces et mettre à jour annuellement. L'URL de base :

```
https://{shop_domain}/admin/api/{version}/graphql.json
```

### Queries principales utilisées par StoreMD

| Query | Utilisée par | Données récupérées |
|-------|-------------|-------------------|
| `shop` | OAuth callback, store setup | Nom, domaine, plan, devise, pays |
| `themes(roles: MAIN)` | OAuth, health_scorer, residue_detector | Thème actif, ID, fichiers |
| `theme.files` | residue_detector, code_weight, schema_markup | Fichiers liquid, JS, CSS du thème |
| `products(first: 50)` | listing_analyzer, agentic_readiness | Produits avec metafields, variants, images, SEO |
| `appInstallations` | app_impact, ghost_billing, security_monitor | Apps installées, scopes, handle |
| `scriptTags` | residue_detector, code_weight | Scripts injectés par les apps |
| `recurringApplicationCharges` | ghost_billing | Charges récurrents actifs (REST) |
| `webhookSubscriptions` | OAuth setup | Webhooks enregistrés |
| `productUpdate` (mutation) | one_click_fixer | Metafields, alt text, descriptions |
| `themeFilesDelete` (mutation) | one_click_fixer | Supprimer du code résiduel |
| `urlRedirectCreate` (mutation) | one_click_fixer | Créer des redirections (broken links) |

### Pagination

Toujours cursor-based. JAMAIS de pagination par offset (Shopify ne le supporte pas en GraphQL).

```python
async def fetch_all_paginated(shopify: ShopifyClient, query: str,
                                resource: str, page_size: int = 50) -> list[dict]:
    """Helper pagination générique pour les queries Shopify GraphQL."""
    all_items = []
    cursor = None

    while True:
        variables = {"first": page_size, "after": cursor}
        data = await shopify.graphql(query, variables)

        resource_data = data[resource]
        edges = resource_data["edges"]
        all_items.extend([edge["node"] for edge in edges])

        page_info = resource_data["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]

        # Safety : max 20 pages (1000 items) pour éviter les boucles infinies
        if len(all_items) >= 1000:
            logger.warning("pagination_capped", resource=resource, count=len(all_items))
            break

    return all_items
```

### Bulk Operations (pour les gros catalogues)

Pour les stores avec >1000 produits, utiliser les Shopify Bulk Operations :

```graphql
mutation BulkProducts {
  bulkOperationRunQuery(
    query: """
    {
      products {
        edges {
          node {
            id
            title
            descriptionHtml
            variants { edges { node { barcode sku } } }
            metafields { edges { node { namespace key value } } }
          }
        }
      }
    }
    """
  ) {
    bulkOperation { id status }
    userErrors { field message }
  }
}
```

Le résultat est un fichier JSONL téléchargeable. Utiliser quand `products_count > 1000`.

```python
async def fetch_products_bulk(shopify: ShopifyClient) -> list[dict]:
    """Utilise Bulk Operations pour les gros catalogues (>1000 produits)."""
    # 1. Lancer la bulk operation
    result = await shopify.graphql(BULK_PRODUCTS_MUTATION)
    operation_id = result["bulkOperationRunQuery"]["bulkOperation"]["id"]

    # 2. Poller le status (toutes les 5s, max 5 min)
    for _ in range(60):
        status = await shopify.graphql(BULK_STATUS_QUERY, {"id": operation_id})
        op = status["node"]
        if op["status"] == "COMPLETED":
            # 3. Télécharger le fichier JSONL
            return await download_and_parse_jsonl(op["url"])
        elif op["status"] == "FAILED":
            raise ShopifyError(
                code=ErrorCode.SHOPIFY_GRAPHQL_ERROR,
                message=f"Bulk operation failed: {op.get('errorCode')}",
                status_code=502,
            )
        await asyncio.sleep(5)

    raise ShopifyError(
        code=ErrorCode.SHOPIFY_GRAPHQL_ERROR,
        message="Bulk operation timed out",
        status_code=504,
    )
```

---

## WEBHOOKS

### Topics enregistrés

| Topic | Trigger | Handler | Priorité |
|-------|---------|---------|----------|
| `app/uninstalled` | Merchant désinstalle l'app | Cleanup complet (SECURITY.md §8) | Mandatory |
| `customers/data_request` | Shopify GDPR request | Exporter données merchant | Mandatory |
| `customers/redact` | Shopify GDPR request | Supprimer données client | Mandatory |
| `shop/redact` | 48h après uninstall | Supprimer TOUTES les données | Mandatory |
| `products/create` | Nouveau produit ajouté | Agentic monitoring (#37) | StoreMD |
| `products/update` | Produit modifié | Agentic monitoring (#37) + listing watch (#31) | StoreMD |
| `themes/update` | Thème modifié | Collection backup (#7) + trigger rescan | StoreMD |
| `app_subscriptions/update` | Changement billing app | Log, vérifier ghost billing | StoreMD |

### Enregistrement des webhooks

Après le OAuth callback, enregistrer tous les webhooks :

```python
WEBHOOK_TOPICS = [
    "APP_UNINSTALLED",
    "CUSTOMERS_DATA_REQUEST",
    "CUSTOMERS_REDACT",
    "SHOP_REDACT",
    "PRODUCTS_CREATE",
    "PRODUCTS_UPDATE",
    "THEMES_UPDATE",
    "APP_SUBSCRIPTIONS_UPDATE",
]

async def register_webhooks(shopify: ShopifyClient):
    """Enregistre tous les webhooks après l'installation."""
    callback_url = f"{settings.BACKEND_URL}/api/v1/webhooks/shopify"

    for topic in WEBHOOK_TOPICS:
        try:
            result = await shopify.graphql("""
                mutation RegisterWebhook($topic: WebhookSubscriptionTopic!, $url: URL!) {
                    webhookSubscriptionCreate(
                        topic: $topic,
                        webhookSubscription: { callbackUrl: $url, format: JSON }
                    ) {
                        webhookSubscription { id }
                        userErrors { field message }
                    }
                }
            """, {"topic": topic, "url": callback_url})

            errors = result["webhookSubscriptionCreate"]["userErrors"]
            if errors:
                logger.warning("webhook_registration_error",
                               topic=topic, errors=errors)
            else:
                logger.info("webhook_registered", topic=topic)

        except Exception as exc:
            logger.error("webhook_registration_failed",
                         topic=topic, error=str(exc))
            # Ne pas bloquer l'installation pour un webhook
```

### Webhook Handler — Routing

```python
# app/api/routes/webhooks_shopify.py

TOPIC_HANDLERS = {
    "app/uninstalled": handle_app_uninstalled,
    "customers/data_request": handle_customers_data_request,
    "customers/redact": handle_customers_redact,
    "shop/redact": handle_shop_redact,
    "products/create": handle_product_created,
    "products/update": handle_product_updated,
    "themes/update": handle_theme_updated,
    "app_subscriptions/update": handle_app_subscription_updated,
}

async def process_shopify_webhook(webhook_event_id: str):
    """Celery task : traite un webhook Shopify depuis la table webhook_events."""
    event = await get_webhook_event(webhook_event_id)
    topic = event["topic"]
    shop = event["shop_domain"]
    payload = event["payload"]

    handler = TOPIC_HANDLERS.get(topic)
    if not handler:
        logger.warning("unknown_webhook_topic", topic=topic, shop=shop)
        await mark_webhook_processed(webhook_event_id)
        return

    try:
        await handler(shop, payload)
        await mark_webhook_processed(webhook_event_id)
        logger.info("webhook_processed", topic=topic, shop=shop)
    except Exception as exc:
        logger.error("webhook_processing_failed",
                     topic=topic, shop=shop, error=str(exc))
        await mark_webhook_failed(webhook_event_id, str(exc))
```

### Handlers spécifiques

```python
async def handle_product_created(shop: str, payload: dict):
    """Webhook products/create → agentic monitoring + new product watch."""
    store = await get_store_by_domain(shop)
    if not store:
        return

    merchant = await get_merchant(store["merchant_id"])
    plan = merchant.get("plan", "free")

    # Feature #31 — New Product Watch (Starter+)
    if plan in ("starter", "pro", "agency"):
        # Trigger une analyse du nouveau produit
        analyze_new_product.delay(store["id"], payload["admin_graphql_api_id"])

    # Feature #37 — Agentic Monitoring (Pro+)
    if plan in ("pro", "agency"):
        check_agentic_readiness.delay(store["id"], payload["admin_graphql_api_id"])


async def handle_theme_updated(shop: str, payload: dict):
    """Webhook themes/update → backup + potentiel rescan."""
    store = await get_store_by_domain(shop)
    if not store:
        return

    # Feature #7 — Collection Backup (Starter+)
    merchant = await get_merchant(store["merchant_id"])
    if merchant.get("plan") in ("starter", "pro", "agency"):
        create_backup.delay(store["id"])

    # Mettre à jour le thème en DB
    await update_store_theme(store["id"], payload)

    # Si le merchant a le plan Pro+, trigger un rescan rapide
    if merchant.get("plan") in ("pro", "agency"):
        trigger_theme_change_scan.delay(store["id"])


async def handle_app_uninstalled(shop: str, payload: dict):
    """Webhook app/uninstalled → cleanup complet.
    Voir SECURITY.md section 8 pour le détail."""
    store = await get_store_by_domain(shop)
    if not store:
        return

    merchant_id = store["merchant_id"]

    # 1. Cancel Stripe subscription IMMÉDIATEMENT
    billing = StripeBillingService(get_supabase_service())
    await billing.cancel_subscription(merchant_id)

    # 2. Marquer le store comme uninstalled
    await get_supabase_service().table("stores").update({
        "status": "uninstalled",
        "uninstalled_at": datetime.now(UTC).isoformat(),
    }).eq("id", store["id"]).execute()

    # 3. Supprimer le token Shopify
    await get_supabase_service().table("merchants").update({
        "shopify_access_token_encrypted": None,
    }).eq("id", merchant_id).execute()

    # 4. Cleanup Mem0
    memory = StoreMemory()
    await memory.forget_merchant(merchant_id)
    await memory.forget_store(store["id"])

    # 5. Email confirmation
    await send_uninstall_email(merchant_id)

    # 6. Planifier suppression données dans 30 jours (GDPR)
    schedule_data_deletion.apply_async(
        args=[merchant_id], countdown=30 * 24 * 3600
    )

    logger.info("app_uninstalled_cleanup_complete", shop=shop, merchant_id=merchant_id)


async def handle_customers_data_request(shop: str, payload: dict):
    """GDPR : Shopify demande les données d'un client."""
    customer_emails = payload.get("customer", {}).get("email")
    shop_domain = payload.get("shop_domain")
    # StoreMD ne stocke pas de données clients directement
    # Retourner un acknowledgement — rien à exporter
    logger.info("gdpr_data_request", shop=shop_domain, customer=customer_emails)


async def handle_customers_redact(shop: str, payload: dict):
    """GDPR : Shopify demande la suppression des données d'un client."""
    # StoreMD ne stocke pas de données clients
    logger.info("gdpr_customers_redact", shop=shop)


async def handle_shop_redact(shop: str, payload: dict):
    """GDPR : Shopify demande la suppression totale des données du store.
    Appelé 48h après app/uninstalled."""
    store = await get_store_by_domain(shop)
    if store:
        # Supprimer TOUT : store, scans, issues, screenshots, etc.
        # CASCADE depuis la table stores supprime tout
        await get_supabase_service().table("stores").delete().eq(
            "id", store["id"]
        ).execute()
        logger.info("gdpr_shop_redacted", shop=shop, store_id=store["id"])
```

---

## RATE LIMITING SHOPIFY

### GraphQL — Bucket-based (cost points)

```
Bucket max        : 1000 points
Restore rate      : 50 points/seconde
Cost par query    : dépend de la complexité (calculé par Shopify)
Typical scan query: 5-20 points
```

Le coût est retourné dans `extensions.cost` de chaque réponse :

```json
{
  "extensions": {
    "cost": {
      "requestedQueryCost": 12,
      "actualQueryCost": 8,
      "throttleStatus": {
        "maximumAvailable": 1000,
        "currentlyAvailable": 892,
        "restoreRate": 50
      }
    }
  }
}
```

### REST — 40 requests/second (bucket)

Pour les endpoints REST uniquement (comme `recurring_application_charges`).

### Protection dans le client

Le `ShopifyClient` (voir `.claude/skills/shopify-api/SKILL.md`) gère :
1. **Semaphore** : max 4 requêtes parallèles
2. **Retry 429** : exponential backoff (2s, 4s, 8s)
3. **Throttle detection** : si `currentlyAvailable < 100`, attendre 2s

---

## SHOPIFY APP BRIDGE — EMBEDDED APP

StoreMD est une app embedded dans le Shopify Admin. Le frontend utilise App Bridge pour :

```typescript
// lib/shopify-app-bridge.ts

import { createApp } from "@shopify/app-bridge";
import { Redirect } from "@shopify/app-bridge/actions";

const app = createApp({
  apiKey: process.env.NEXT_PUBLIC_SHOPIFY_API_KEY!,
  host: new URLSearchParams(window.location.search).get("host")!,
});

// Redirect dans le Shopify Admin
const redirect = Redirect.create(app);
redirect.dispatch(Redirect.Action.APP, "/dashboard");

// Navigation bar
import { NavigationMenu } from "@shopify/app-bridge/actions";
const navigationMenu = NavigationMenu.create(app, {
  items: [
    { label: "Dashboard", destination: "/dashboard" },
    { label: "Settings", destination: "/dashboard/settings" },
    { label: "Pricing", destination: "/pricing" },
  ],
});
```

### Session Token (alternative au JWT cookie)

Pour les apps embedded, Shopify recommande les session tokens :

```typescript
import { getSessionToken } from "@shopify/app-bridge-utils";

async function fetchWithAuth(url: string, options: RequestInit = {}) {
  const token = await getSessionToken(app);
  return fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      Authorization: `Bearer ${token}`,
    },
  });
}
```

Le backend valide ce token comme un JWT Shopify (pas Supabase) — à adapter dans le middleware auth si on utilise App Bridge session tokens au lieu de Supabase Auth.

---

## "BUILT FOR SHOPIFY" — CHECKLIST

Badge de confiance dans le Shopify App Store. Objectif : l'obtenir au launch.

```
Requirements obligatoires :
[ ] App installable en 1 clic (OAuth flow clean)
[ ] Mandatory webhooks implémentés (app/uninstalled, GDPR)
[ ] Pas de facturation après désinstallation
[ ] App fonctionne dans l'admin Shopify (embedded via App Bridge)
[ ] Respecte les Polaris design guidelines
[ ] Supporte les thèmes 2.0 (Online Store 2.0)
[ ] Pas de code injecté dans le thème du merchant (sauf si nécessaire et réversible)
[ ] Performance : app ne ralentit pas le storefront
[ ] Privacy policy + terms of service
[ ] Support client accessible (email minimum)
[ ] Pas de popup/review harcèlement
[ ] Annulation instantanée, zéro frais cachés

Performance :
[ ] App charge en <3s dans le Shopify Admin
[ ] Pas de requêtes bloquantes au storefront
[ ] Respecte les rate limits API

UI/UX :
[ ] Utilise Polaris ou cohérent avec les guidelines Shopify
[ ] Onboarding en <5 étapes
[ ] Valeur visible en <3 minutes
```

---

## INTERDICTIONS

- ❌ `shopify-python-api` → ✅ `httpx` directement (thread-safety)
- ❌ Token Shopify en clair → ✅ Fernet encryption toujours
- ❌ `==` pour comparer HMAC → ✅ `hmac.compare_digest()` (constant-time)
- ❌ Requête sans rate limit handling → ✅ Semaphore + retry 429
- ❌ Pagination par offset → ✅ Cursor-based (pageInfo.endCursor)
- ❌ Ignorer `userErrors` dans les mutations → ✅ Toujours vérifier
- ❌ Webhook sans HMAC validation → ✅ Valider AVANT tout traitement
- ❌ Webhook sans idempotency → ✅ Check webhook_events table
- ❌ Facturer après uninstall → ✅ Cancel Stripe dans le webhook handler
- ❌ Code résiduel dans le thème après uninstall → ✅ Cleanup complet
