# Skill: Shopify API

> **Utilise ce skill dès que tu touches à l'API Shopify :**
> **OAuth, GraphQL queries, webhooks, HMAC, token management, rate limiting.**

---

## QUAND UTILISER

- Écrire ou modifier le client Shopify (`app/services/shopify.py`)
- Implémenter l'OAuth flow (`app/api/routes/auth.py`)
- Écrire un scanner qui appelle l'API Shopify
- Gérer les webhooks Shopify (`app/api/routes/webhooks_shopify.py`)
- Implémenter un One-Click Fix qui écrit via l'API Shopify

---

## API VERSION

```python
SHOPIFY_API_VERSION = "2026-01"  # depuis config.py / env vars
```

Toujours utiliser la version configurée, jamais hardcoder dans les queries.

---

## CLIENT HTTP — HTTPX, PAS shopify-python-api

`shopify-python-api` est deprecated et a des problèmes de thread-safety. Utiliser `httpx` directement.

```python
# app/services/shopify.py

import httpx
import asyncio
from app.core.security import decrypt_token
from app.core.exceptions import ShopifyError, ErrorCode

class ShopifyClient:
    """Client async pour l'API Shopify Admin (GraphQL)."""

    def __init__(self, shop_domain: str, encrypted_token: str):
        self.shop_domain = shop_domain
        self.access_token = decrypt_token(encrypted_token)
        self.api_version = settings.SHOPIFY_API_VERSION
        self.base_url = f"https://{shop_domain}/admin/api/{self.api_version}"
        self.semaphore = asyncio.Semaphore(4)  # max 4 requêtes parallèles

    @property
    def headers(self) -> dict:
        return {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
        }

    async def graphql(self, query: str, variables: dict | None = None) -> dict:
        """Exécute une query GraphQL avec retry sur 429."""
        async with self.semaphore:
            async with httpx.AsyncClient(timeout=30.0) as client:
                for attempt in range(4):  # 1 essai + 3 retries
                    response = await client.post(
                        f"{self.base_url}/graphql.json",
                        json={"query": query, "variables": variables or {}},
                        headers=self.headers,
                    )

                    # Rate limit → retry avec backoff
                    if response.status_code == 429:
                        retry_after = float(response.headers.get("Retry-After", 2))
                        wait = retry_after * (2 ** attempt)
                        logger.warning("shopify_rate_limit",
                            shop=self.shop_domain, retry_after=wait, attempt=attempt)
                        await asyncio.sleep(wait)
                        continue

                    # Server error → retry
                    if response.status_code >= 500:
                        wait = 2 ** attempt
                        logger.warning("shopify_server_error",
                            shop=self.shop_domain, status=response.status_code)
                        await asyncio.sleep(wait)
                        continue

                    response.raise_for_status()
                    data = response.json()

                    # GraphQL errors (200 mais avec erreurs dans le body)
                    if "errors" in data:
                        raise ShopifyError(
                            code=ErrorCode.SHOPIFY_GRAPHQL_ERROR,
                            message=str(data["errors"]),
                            status_code=502,
                            context={"shop": self.shop_domain, "query": query[:200]},
                        )

                    return data["data"]

                # Tous les retries échoués
                raise ShopifyError(
                    code=ErrorCode.SHOPIFY_RATE_LIMIT,
                    message="Shopify API unavailable after 4 attempts",
                    status_code=429,
                    context={"shop": self.shop_domain},
                )

    async def rest_get(self, endpoint: str, params: dict | None = None) -> dict:
        """GET REST (pour les endpoints sans équivalent GraphQL)."""
        async with self.semaphore:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/{endpoint}.json",
                    params=params,
                    headers=self.headers,
                )
                if response.status_code == 429:
                    raise ShopifyError(
                        code=ErrorCode.SHOPIFY_RATE_LIMIT,
                        message="Rate limited",
                        status_code=429,
                    )
                response.raise_for_status()
                return response.json()
```

---

## GRAPHQL QUERIES — PATTERNS

### Fetch products (paginated)

```graphql
query FetchProducts($first: Int!, $after: String) {
  products(first: $first, after: $after) {
    edges {
      cursor
      node {
        id
        title
        handle
        status
        productType
        vendor
        tags
        totalInventory
        onlineStoreUrl
        descriptionHtml
        seo {
          title
          description
        }
        images(first: 10) {
          edges {
            node {
              id
              altText
              url
              width
              height
            }
          }
        }
        variants(first: 100) {
          edges {
            node {
              id
              title
              sku
              barcode
              price
              inventoryQuantity
            }
          }
        }
        metafields(first: 20) {
          edges {
            node {
              namespace
              key
              value
              type
            }
          }
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
```

```python
# Pagination helper
async def fetch_all_products(shopify: ShopifyClient) -> list[dict]:
    products = []
    cursor = None
    while True:
        data = await shopify.graphql(
            FETCH_PRODUCTS_QUERY,
            variables={"first": 50, "after": cursor},
        )
        edges = data["products"]["edges"]
        products.extend([edge["node"] for edge in edges])
        page_info = data["products"]["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]
    return products
```

### Fetch theme assets

```graphql
query FetchThemeAssets($themeId: ID!) {
  theme(id: $themeId) {
    id
    name
    role
    files(first: 250) {
      edges {
        node {
          filename
          contentType
          size
          body {
            ... on OnlineStoreThemeFileBodyText {
              content
            }
          }
        }
      }
    }
  }
}
```

### Fetch installed apps

```graphql
query FetchApps {
  appInstallations(first: 50) {
    edges {
      node {
        app {
          id
          title
          handle
          developerName
          apiKey
        }
        accessScopes {
          handle
        }
      }
    }
  }
}
```

### Fetch script tags (code résiduel)

```graphql
query FetchScriptTags {
  scriptTags(first: 100) {
    edges {
      node {
        id
        src
        displayScope
        cache
      }
    }
  }
}
```

### Write product metafield (One-Click Fix)

```graphql
mutation UpdateProductMetafield($input: ProductInput!) {
  productUpdate(input: $input) {
    product {
      id
      metafields(first: 5) {
        edges {
          node {
            namespace
            key
            value
          }
        }
      }
    }
    userErrors {
      field
      message
    }
  }
}
```

```python
# Variables
variables = {
    "input": {
        "id": "gid://shopify/Product/123456",
        "metafields": [
            {
                "namespace": "custom",
                "key": "material",
                "value": "100% organic cotton",
                "type": "single_line_text_field",
            }
        ],
    }
}
```

### Update product images alt text (One-Click Fix)

```graphql
mutation UpdateImageAltText($productId: ID!, $image: ImageInput!) {
  productImageUpdate(productId: $productId, image: $image) {
    image {
      id
      altText
    }
    userErrors {
      field
      message
    }
  }
}
```

---

## SCOPES

```
read_products       → Catalogue scan, listing analyzer, agentic readiness
write_products      → One-Click Fix (alt text, metafields, descriptions)
read_themes         → Theme analysis, residue detection, code weight
write_themes        → One-Click Fix (supprimer code résiduel)
read_orders         → Traffic analytics, bot filter data
read_online_store   → Pages, blog posts, navigation
```

**INTERDIT :**
- `read_apps` → nécessite Shopify Partner approval, pas en V1
- `write_checkouts` → pas besoin, scope dangereuse
- `write_orders` → pas besoin, scope dangereuse

Si un scanner a besoin d'un scope non listé → discuter AVANT d'ajouter.

---

## OAUTH FLOW

Voir `docs/SECURITY.md` section 7 pour le flow complet (10 étapes).

Résumé :
1. Valider shop domain (regex `^[a-zA-Z0-9][a-zA-Z0-9\-]*\.myshopify\.com$`)
2. Générer state (nonce anti-CSRF), stocker Redis TTL 5 min
3. Redirect vers Shopify consent screen
4. Callback : valider state, échanger code → token
5. Chiffrer token Fernet → stocker DB
6. Créer session Supabase

---

## WEBHOOKS

### Webhooks à enregistrer

```python
REQUIRED_WEBHOOKS = [
    # Mandatory Shopify
    {"topic": "app/uninstalled", "address": f"{BACKEND_URL}/api/v1/webhooks/shopify"},
    {"topic": "customers/data_request", "address": f"{BACKEND_URL}/api/v1/webhooks/shopify"},
    {"topic": "customers/redact", "address": f"{BACKEND_URL}/api/v1/webhooks/shopify"},
    {"topic": "shop/redact", "address": f"{BACKEND_URL}/api/v1/webhooks/shopify"},

    # StoreMD triggers
    {"topic": "products/create", "address": f"{BACKEND_URL}/api/v1/webhooks/shopify"},
    {"topic": "products/update", "address": f"{BACKEND_URL}/api/v1/webhooks/shopify"},
    {"topic": "themes/update", "address": f"{BACKEND_URL}/api/v1/webhooks/shopify"},
    {"topic": "app_subscriptions/update", "address": f"{BACKEND_URL}/api/v1/webhooks/shopify"},
]
```

### Enregistrement après OAuth

```python
async def register_webhooks(shopify: ShopifyClient):
    """Enregistre tous les webhooks requis après l'installation."""
    for webhook in REQUIRED_WEBHOOKS:
        mutation = """
        mutation CreateWebhook($topic: WebhookSubscriptionTopic!, $url: URL!) {
          webhookSubscriptionCreate(topic: $topic, webhookSubscription: { callbackUrl: $url, format: JSON }) {
            webhookSubscription { id }
            userErrors { field message }
          }
        }
        """
        await shopify.graphql(mutation, {
            "topic": webhook["topic"].upper().replace("/", "_"),
            "url": webhook["address"],
        })
```

### HMAC validation

Voir `docs/SECURITY.md` section 2. Toujours `hmac.compare_digest()`, jamais `==`.

---

## RATE LIMITING SHOPIFY

### GraphQL (bucket-based)

Shopify GraphQL utilise un bucket de "cost points" :
- Bucket max : 1000 points
- Restore rate : 50 points/seconde
- Chaque query a un coût calculé

Lire le header `X-Shopify-Shop-Api-Call-Limit` ou le champ `extensions.cost` dans la réponse GraphQL.

```python
# Vérifier le throttle status dans la réponse
async def graphql_with_throttle(self, query: str, variables: dict | None = None) -> dict:
    data = await self.graphql(query, variables)
    # La réponse GraphQL inclut le coût
    # Si on approche la limite, attendre
    extensions = data.get("extensions", {})
    cost = extensions.get("cost", {})
    available = cost.get("throttleStatus", {}).get("currentlyAvailable", 1000)
    if available < 100:
        logger.info("shopify_throttle_approaching", available=available)
        await asyncio.sleep(2)
    return data
```

### REST (40 requests/second)

Limité à 40 requests/second par store (pour les endpoints REST). Le semaphore à 4 dans le client gère ça.

---

## ERREURS COURANTES

| Erreur | Cause | Fix |
|--------|-------|-----|
| `Access token is invalid` | Token expiré ou app désinstallée | Vérifier status store, prompt reinstall |
| `Throttled` / 429 | Rate limit dépassé | Retry avec exponential backoff (déjà dans le client) |
| `Access denied` | Scope manquant | Vérifier les scopes, prompt re-authorize |
| `Not Found` | Produit/thème supprimé entre le query et l'action | Catch et skip gracefully |
| `Internal error` (500) | Shopify down | Retry, max 3 fois |

---

## INTERDICTIONS

- ❌ `shopify-python-api` → ✅ `httpx` direct (thread-safety)
- ❌ Hardcoder l'API version → ✅ `settings.SHOPIFY_API_VERSION`
- ❌ Token en clair dans le client → ✅ Decrypt au runtime via `decrypt_token()`
- ❌ Requête sans semaphore → ✅ Toujours via `self.semaphore`
- ❌ Ignorer `userErrors` dans les mutations → ✅ Toujours vérifier `userErrors`
- ❌ Pagination sans cursor → ✅ Toujours utiliser `pageInfo.endCursor`
- ❌ Requête sans timeout → ✅ `httpx.AsyncClient(timeout=30.0)`
