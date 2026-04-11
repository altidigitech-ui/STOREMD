# API.md — Référence API REST StoreMD

> **Tous les endpoints, request/response schemas, auth, pagination, error codes.**
> **Le backend implémente EXACTEMENT ces routes. Pas d'improvisation.**

---

## CONVENTIONS GLOBALES

### Base URL

```
Production : https://api.storemd.com/api/v1
Staging    : https://api-staging.storemd.com/api/v1
Dev        : http://localhost:8000/api/v1
```

### Versioning

Toujours préfixé `/api/v1/`. Quand une v2 sera nécessaire, les routes v1 continuent de fonctionner.

### Auth

Toutes les routes (sauf webhooks et healthcheck) nécessitent un JWT Supabase :

```
Authorization: Bearer <jwt_token>
```

Les webhooks utilisent HMAC (Shopify) ou signature (Stripe) au lieu du JWT.

### Content-Type

```
Request  : application/json
Response : application/json
```

### Pagination (cursor-based)

```
GET /api/v1/stores/{store_id}/scans?limit=20&cursor=xxx

Response :
{
  "data": [...],
  "pagination": {
    "has_next": true,
    "next_cursor": "eyJpZCI6...",
    "total_count": 142
  }
}
```

Paramètres :
- `limit` : 1-100, default 20
- `cursor` : opaque string du résultat précédent (base64 encoded ID)

### Réponses

**Succès :** le payload directement (pas d'enveloppe `{"data": ...}` sauf pour les listes paginées).

```json
// Single resource
{ "id": "xxx", "score": 72, ... }

// List (paginated)
{
  "data": [{ "id": "xxx" }, { "id": "yyy" }],
  "pagination": { "has_next": true, "next_cursor": "..." }
}
```

**Erreur :**

```json
{
  "error": {
    "code": "AUTH_PLAN_REQUIRED",
    "message": "Feature 'visual_store_test' requires pro plan or above"
  }
}
```

### Status codes utilisés

| Code | Signification |
|------|--------------|
| 200 | Succès |
| 201 | Créé (POST qui crée une ressource) |
| 204 | Succès sans body (DELETE) |
| 400 | Input invalide |
| 401 | Non authentifié (JWT manquant/invalide) |
| 403 | Interdit (plan insuffisant, store d'un autre merchant) |
| 404 | Ressource non trouvée |
| 409 | Conflit (scan déjà en cours, fix déjà appliqué) |
| 422 | Validation Pydantic échouée |
| 429 | Rate limit dépassé |
| 500 | Erreur serveur interne |
| 502 | Erreur service externe (Shopify, Stripe) |
| 504 | Timeout |

---

## AUTH

### POST /api/v1/auth/install

Redirige vers Shopify OAuth consent screen.

**Auth :** aucune (c'est le début du flow OAuth)

| Param | Type | Requis | Description |
|-------|------|--------|-------------|
| `shop` | query string | ✅ | `mystore.myshopify.com` |

**Response :** `302 Redirect` vers Shopify OAuth URL

**Errors :**
- `400 OAUTH_INVALID_SHOP_DOMAIN` — domain ne matche pas `*.myshopify.com`

---

### GET /api/v1/auth/callback

Callback OAuth Shopify. Échange le code pour un token.

**Auth :** aucune (Shopify redirige ici)

| Param | Type | Requis | Description |
|-------|------|--------|-------------|
| `code` | query string | ✅ | Authorization code |
| `state` | query string | ✅ | State nonce (anti-CSRF) |
| `shop` | query string | ✅ | Shop domain |
| `hmac` | query string | ✅ | HMAC signature |

**Response :** `302 Redirect` vers `/dashboard` ou `/onboarding`

**Errors :**
- `403 OAUTH_STATE_INVALID` — state mismatch ou expiré
- `400 OAUTH_INVALID_SHOP_DOMAIN` — domain invalide
- `502 OAUTH_CODE_EXCHANGE_FAILED` — Shopify refuse le code
- `502 OAUTH_TOKEN_MISSING` — pas de token dans la réponse

---

### POST /api/v1/auth/logout

Déconnexion. Invalide la session Supabase.

**Auth :** Bearer JWT

**Response :** `204 No Content`

---

## STORES

### GET /api/v1/stores/{store_id}

Informations du store.

**Auth :** Bearer JWT (merchant doit posséder le store)

**Response :**

```json
{
  "id": "uuid",
  "shopify_shop_domain": "mystore.myshopify.com",
  "name": "My Store",
  "primary_domain": "mystore.com",
  "theme_name": "Dawn 15.0",
  "products_count": 847,
  "apps_count": 14,
  "currency": "USD",
  "country": "US",
  "shopify_plan": "shopify",
  "status": "active",
  "created_at": "2026-04-09T10:00:00Z"
}
```

**Errors :**
- `404 AUTH_STORE_NOT_FOUND` — store inexistant ou pas au merchant

---

### GET /api/v1/stores/{store_id}/apps

Apps installées sur le store avec leur impact.

**Auth :** Bearer JWT

**Response :**

```json
{
  "data": [
    {
      "id": "uuid",
      "name": "Privy",
      "handle": "privy",
      "status": "active",
      "impact_ms": 1800,
      "scripts_count": 3,
      "scripts_size_kb": 340.5,
      "css_size_kb": 12.0,
      "billing_amount": 29.99,
      "scopes": ["read_products", "write_script_tags"],
      "developer": "Privy Inc",
      "first_detected_at": "2026-01-15T00:00:00Z"
    }
  ],
  "total_apps": 14,
  "total_impact_ms": 3200
}
```

---

## SCANS

### POST /api/v1/stores/{store_id}/scans

Déclenche un nouveau scan.

**Auth :** Bearer JWT

**Request :**

```json
{
  "modules": ["health", "listings", "agentic"]
}
```

| Field | Type | Requis | Validation |
|-------|------|--------|-----------|
| `modules` | string[] | ✅ | 1-5 items, values: `health`, `listings`, `agentic`, `compliance`, `browser` |

**Response :** `201 Created`

```json
{
  "id": "uuid",
  "status": "pending",
  "modules": ["health", "listings", "agentic"],
  "trigger": "manual",
  "created_at": "2026-04-09T10:30:00Z"
}
```

**Errors :**
- `403 AUTH_PLAN_REQUIRED` — module demandé nécessite un plan supérieur
- `403 SCAN_LIMIT_REACHED` — limite de scans du plan atteinte
- `409 SCAN_ALREADY_RUNNING` — un scan est déjà en cours pour ce store
- `422 VALIDATION_ERROR` — module invalide

---

### GET /api/v1/stores/{store_id}/scans

Liste des scans (paginés, plus récents en premier).

**Auth :** Bearer JWT

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | query int | 20 | 1-100 |
| `cursor` | query string | null | Pagination cursor |
| `status` | query string | null | Filtrer: `pending`, `running`, `completed`, `failed` |

**Response :**

```json
{
  "data": [
    {
      "id": "uuid",
      "status": "completed",
      "trigger": "cron",
      "modules": ["health"],
      "score": 67,
      "mobile_score": 52,
      "desktop_score": 81,
      "issues_count": 5,
      "critical_count": 1,
      "partial_scan": false,
      "duration_ms": 42000,
      "started_at": "2026-04-09T03:00:00Z",
      "completed_at": "2026-04-09T03:00:42Z",
      "created_at": "2026-04-09T03:00:00Z"
    }
  ],
  "pagination": {
    "has_next": true,
    "next_cursor": "eyJpZCI6...",
    "total_count": 24
  }
}
```

---

### GET /api/v1/stores/{store_id}/scans/{scan_id}

Résultat détaillé d'un scan avec ses issues.

**Auth :** Bearer JWT

**Response :**

```json
{
  "id": "uuid",
  "status": "completed",
  "score": 67,
  "mobile_score": 52,
  "desktop_score": 81,
  "modules": ["health", "listings"],
  "trigger": "manual",
  "partial_scan": false,
  "duration_ms": 42000,
  "issues": [
    {
      "id": "uuid",
      "module": "health",
      "scanner": "app_impact",
      "severity": "critical",
      "title": "App 'Privy' injects 340KB of unminified JS",
      "description": "...",
      "impact": "+1.8s load time",
      "impact_value": 1.8,
      "impact_unit": "seconds",
      "fix_type": "manual",
      "fix_description": "Consider replacing Privy with a lighter alternative",
      "auto_fixable": false,
      "fix_applied": false,
      "dismissed": false
    }
  ],
  "errors": [],
  "started_at": "2026-04-09T10:30:00Z",
  "completed_at": "2026-04-09T10:30:42Z"
}
```

**Errors :**
- `404 SCAN_NOT_FOUND`

---

### GET /api/v1/stores/{store_id}/health

Score de santé actuel + trend.

**Auth :** Bearer JWT

**Response :**

```json
{
  "score": 67,
  "mobile_score": 52,
  "desktop_score": 81,
  "trend": "up",
  "trend_delta": 9,
  "last_scan_at": "2026-04-09T03:00:42Z",
  "issues_count": 5,
  "critical_count": 1,
  "previous_score": 58,
  "history": [
    { "date": "2026-04-09", "score": 67 },
    { "date": "2026-04-08", "score": 63 },
    { "date": "2026-04-07", "score": 58 }
  ]
}
```

---

## LISTINGS

### GET /api/v1/stores/{store_id}/listings/scan

Résultats du catalogue scan (produits analysés).

**Auth :** Bearer JWT

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | query int | 20 | 1-100 |
| `cursor` | query string | null | Pagination |
| `sort` | query string | `score_asc` | `score_asc`, `score_desc`, `revenue_desc`, `priority` |
| `min_score` | query int | null | Filtrer produits sous ce score |
| `max_score` | query int | null | Filtrer produits au-dessus |

**Response :**

```json
{
  "products_scanned": 847,
  "avg_score": 54,
  "data": [
    {
      "shopify_product_id": "gid://shopify/Product/123",
      "title": "Organic Face Cream",
      "handle": "organic-face-cream",
      "score": 42,
      "title_score": 65,
      "description_score": 20,
      "images_score": 35,
      "seo_score": 60,
      "revenue_30d": 1240.50,
      "orders_30d": 34,
      "priority_rank": 3,
      "issues": [
        { "element": "description", "score": 20, "suggestion": "Too short (23 words)" },
        { "element": "images", "score": 35, "suggestion": "3/5 images missing alt text" }
      ]
    }
  ],
  "pagination": { "has_next": true, "next_cursor": "..." }
}
```

---

### GET /api/v1/stores/{store_id}/listings/priorities

Top produits à améliorer (score faible + revenue élevé).

**Auth :** Bearer JWT

**Response :**

```json
{
  "data": [
    {
      "shopify_product_id": "gid://shopify/Product/123",
      "title": "Organic Face Cream",
      "score": 42,
      "revenue_30d": 1240.50,
      "potential_uplift_pct": 35,
      "priority_rank": 1,
      "top_issue": "Description too short (23 words)"
    }
  ]
}
```

---

### POST /api/v1/stores/{store_id}/listings/{product_id}/rewrite

Réécrit les éléments faibles d'un listing produit.

**Auth :** Bearer JWT
**Plan :** Starter+

**Request :**

```json
{
  "elements": ["description", "seo"],
  "tone": "professional",
  "keep_strong": true
}
```

**Response :**

```json
{
  "product_id": "gid://shopify/Product/123",
  "rewrites": [
    {
      "element": "description",
      "before": "<p>Nice cream for face.</p>",
      "after": "<p>Luxurious organic face cream with...</p>",
      "applied": false
    },
    {
      "element": "seo_description",
      "before": "Nice cream for face.",
      "after": "Organic face cream with vitamin E...",
      "applied": false
    }
  ]
}
```

Le merchant doit appeler `/fixes/{fix_id}/apply` pour appliquer.

---

### POST /api/v1/stores/{store_id}/listings/bulk

Opération bulk sur les listings (rewrite, alt text, SEO).

**Auth :** Bearer JWT
**Plan :** Pro+

**Request :**

```json
{
  "operation": "generate_alt_text",
  "product_ids": ["gid://shopify/Product/123", "gid://shopify/Product/456"],
  "options": {}
}
```

| Field | Type | Values |
|-------|------|--------|
| `operation` | string | `generate_alt_text`, `rewrite_descriptions`, `optimize_seo`, `fill_metafields` |
| `product_ids` | string[] | 1-500 product GIDs |

**Response :** `202 Accepted` (background task)

```json
{
  "bulk_operation_id": "uuid",
  "status": "pending",
  "product_count": 2,
  "operation": "generate_alt_text"
}
```

---

### POST /api/v1/stores/{store_id}/listings/import

Import CSV de produits.

**Auth :** Bearer JWT
**Plan :** Pro+

**Request :** `multipart/form-data`

| Field | Type | Description |
|-------|------|-------------|
| `file` | file (CSV) | Fichier CSV avec les colonnes requises |
| `mode` | string | `validate_only` ou `import` |

**Response :**

```json
{
  "status": "validated",
  "rows_total": 150,
  "rows_valid": 142,
  "rows_errors": 8,
  "errors": [
    { "row": 23, "column": "title", "error": "Title exceeds 255 characters" }
  ]
}
```

---

## AGENTIC

### GET /api/v1/stores/{store_id}/agentic/score

Agentic readiness score.

**Auth :** Bearer JWT
**Plan :** Starter+

**Response :**

```json
{
  "score": 34,
  "products_scanned": 847,
  "checks": [
    {
      "name": "gtin_present",
      "status": "fail",
      "affected_products": 120,
      "pass_rate": 85.8,
      "fix_description": "Add GTIN/barcode to 120 products"
    },
    {
      "name": "metafields_filled",
      "status": "partial",
      "affected_products": 89,
      "pass_rate": 89.5,
      "fix_description": "Fill material, dimensions for 89 products"
    },
    {
      "name": "structured_description",
      "status": "fail",
      "affected_products": 245,
      "pass_rate": 71.1,
      "fix_description": "Restructure 245 descriptions for AI"
    },
    {
      "name": "schema_markup",
      "status": "pass",
      "affected_products": 0,
      "pass_rate": 100
    },
    {
      "name": "google_category",
      "status": "fail",
      "affected_products": 400,
      "pass_rate": 52.8,
      "fix_description": "Assign Google categories to 400 products"
    },
    {
      "name": "shopify_catalog",
      "status": "pass",
      "affected_products": 0,
      "pass_rate": 100
    }
  ]
}
```

---

### POST /api/v1/stores/{store_id}/agentic/fixes

Générer et appliquer les fixes agentic.

**Auth :** Bearer JWT
**Plan :** Starter+

**Request :**

```json
{
  "checks": ["metafields_filled", "structured_description"],
  "product_ids": ["gid://shopify/Product/123"],
  "auto_apply": false
}
```

**Response :**

```json
{
  "fixes": [
    {
      "fix_id": "uuid",
      "product_id": "gid://shopify/Product/123",
      "check": "metafields_filled",
      "field": "material",
      "suggested_value": "100% organic cotton",
      "status": "pending_approval",
      "auto_fixable": true
    }
  ]
}
```

---

### GET /api/v1/stores/{store_id}/products/hs-codes

Validation des HS codes.

**Auth :** Bearer JWT
**Plan :** Pro+

**Response :**

```json
{
  "total_products": 847,
  "missing_count": 47,
  "suspicious_count": 12,
  "valid_count": 788,
  "data": [
    {
      "shopify_product_id": "gid://shopify/Product/456",
      "title": "Silk Scarf",
      "hs_code": null,
      "status": "missing",
      "suggestion": "6214.10 (silk scarves)",
      "product_type": "scarf"
    },
    {
      "shopify_product_id": "gid://shopify/Product/789",
      "title": "Leather Bag",
      "hs_code": "9999.99",
      "status": "suspicious",
      "suggestion": "4202.21 (leather handbags)",
      "product_type": "bag"
    }
  ],
  "pagination": { "has_next": false }
}
```

---

## COMPLIANCE

### GET /api/v1/stores/{store_id}/accessibility

Scan WCAG 2.1. Ajouter `?live=true` pour le scan Playwright (Pro).

**Auth :** Bearer JWT
**Plan :** Starter+ (statique), Pro+ (live)

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `live` | query bool | false | Inclure le test Playwright (Pro) |

**Response :**

```json
{
  "score": 62,
  "eaa_compliant": false,
  "violations_count": 30,
  "violations": [
    {
      "rule": "img-alt",
      "severity": "critical",
      "count": 23,
      "fix_description": "Add alt text to 23 images",
      "auto_fixable": true
    },
    {
      "rule": "color-contrast",
      "severity": "major",
      "count": 5,
      "fix_description": "Increase contrast ratio on 5 elements",
      "auto_fixable": false
    }
  ],
  "live_test_included": false,
  "live_test_available": true
}
```

---

### GET /api/v1/stores/{store_id}/links/broken

Broken links scanner.

**Auth :** Bearer JWT
**Plan :** Starter+

**Response :**

```json
{
  "broken_count": 8,
  "pages_crawled": 47,
  "data": [
    {
      "url": "/products/old-product",
      "source_page": "/collections/summer",
      "status_code": 404,
      "type": "internal",
      "auto_fixable": true,
      "fix_description": "Create redirect to a similar product"
    }
  ]
}
```

---

## BROWSER (Pro+)

### GET /api/v1/stores/{store_id}/visual/diff

Visual Store Test — screenshots + diff.

**Auth :** Bearer JWT
**Plan :** Pro+

**Response :**

```json
{
  "screenshots": {
    "mobile": {
      "current_url": "https://storage.supabase.co/screenshots/xxx/mobile.png",
      "previous_url": "https://storage.supabase.co/screenshots/yyy/mobile.png",
      "diff_pct": 12.4,
      "significant_change": true
    },
    "desktop": {
      "current_url": "https://storage.supabase.co/screenshots/xxx/desktop.png",
      "previous_url": null,
      "diff_pct": null,
      "significant_change": false
    }
  },
  "diff_regions": [
    {
      "area": "top (header/hero)",
      "change_pct": 18.2,
      "probable_cause": "Reviews+ v3.2 update shifted hero banner"
    }
  ],
  "scan_id": "uuid",
  "scanned_at": "2026-04-09T03:01:15Z"
}
```

---

### GET /api/v1/stores/{store_id}/simulation

Real User Simulation results.

**Auth :** Bearer JWT
**Plan :** Pro+

**Response :**

```json
{
  "total_time_ms": 14200,
  "bottleneck_step": "Product",
  "bottleneck_cause": "Privy popup injects 340KB before content renders",
  "steps": [
    { "name": "Homepage", "url": "/", "time_ms": 2100, "bottleneck": false },
    { "name": "Collection", "url": "/collections/all", "time_ms": 1800, "bottleneck": false },
    { "name": "Product", "url": "/products/face-cream", "time_ms": 6100, "bottleneck": true, "cause": "Privy popup 340KB" },
    { "name": "Add to Cart", "url": null, "time_ms": 800, "bottleneck": false },
    { "name": "Cart/Checkout", "url": "/cart", "time_ms": 3400, "bottleneck": false }
  ],
  "scan_id": "uuid",
  "scanned_at": "2026-04-09T03:02:30Z"
}
```

---

## FIXES

### POST /api/v1/stores/{store_id}/fixes/{fix_id}/apply

Appliquer un fix (One-Click Fix). Le merchant a vu le preview et approuve.

**Auth :** Bearer JWT
**Plan :** Starter+

**Response :**

```json
{
  "fix_id": "uuid",
  "status": "applied",
  "fix_type": "alt_text",
  "before_state": { "alt_text": null },
  "after_state": { "alt_text": "Organic face cream in glass jar" },
  "revertable": true,
  "applied_at": "2026-04-09T11:00:00Z"
}
```

**Errors :**
- `404 FIX_NOT_FOUND`
- `409 FIX_ALREADY_APPLIED`
- `500 FIX_APPLY_FAILED` — Shopify API write échoue
- `403 FIX_APPROVAL_REQUIRED`

---

### POST /api/v1/stores/{store_id}/fixes/{fix_id}/revert

Annuler un fix appliqué.

**Auth :** Bearer JWT

**Response :**

```json
{
  "fix_id": "uuid",
  "status": "reverted",
  "reverted_at": "2026-04-09T11:05:00Z"
}
```

**Errors :**
- `404 FIX_NOT_FOUND`
- `400 FIX_NOT_REVERTABLE`
- `500 FIX_REVERT_FAILED`

---

## FEEDBACK

### POST /api/v1/feedback

Ouroboros — le merchant accepte ou refuse une recommandation.

**Auth :** Bearer JWT

**Request :**

```json
{
  "issue_id": "uuid",
  "accepted": false,
  "reason": "I need Privy for my popups",
  "reason_category": "disagree"
}
```

| Field | Type | Requis | Validation |
|-------|------|--------|-----------|
| `issue_id` | string | ✅ | UUID existant dans scan_issues |
| `accepted` | boolean | ✅ | |
| `reason` | string | ❌ | Max 500 chars |
| `reason_category` | string | ❌ | `not_relevant`, `too_risky`, `will_do_later`, `disagree`, `already_fixed`, `other` |

**Response :** `201 Created`

```json
{
  "id": "uuid",
  "accepted": false,
  "reason_category": "disagree",
  "created_at": "2026-04-09T11:10:00Z"
}
```

---

## BILLING

### POST /api/v1/billing/checkout

Crée une Stripe Checkout session.

**Auth :** Bearer JWT

**Request :**

```json
{
  "plan": "pro"
}
```

| Field | Type | Validation |
|-------|------|-----------|
| `plan` | string | `starter`, `pro`, `agency` |

**Response :**

```json
{
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_xxx"
}
```

---

### GET /api/v1/billing/portal

URL vers le Stripe Customer Portal (gérer l'abonnement).

**Auth :** Bearer JWT

**Response :**

```json
{
  "portal_url": "https://billing.stripe.com/p/session/xxx"
}
```

**Errors :**
- `404 BILLING_CUSTOMER_NOT_FOUND`

---

### GET /api/v1/billing/usage

Usage actuel du merchant pour la période en cours.

**Auth :** Bearer JWT

**Response :**

```json
{
  "plan": "starter",
  "period_start": "2026-04-01",
  "period_end": "2026-04-30",
  "usage": [
    { "type": "scan", "count": 3, "limit": 5, "remaining": 2 },
    { "type": "listing_analysis", "count": 42, "limit": 100, "remaining": 58 },
    { "type": "one_click_fix", "count": 8, "limit": 20, "remaining": 12 },
    { "type": "browser_test", "count": 0, "limit": 0, "remaining": 0 },
    { "type": "bulk_operation", "count": 0, "limit": 0, "remaining": 0 }
  ]
}
```

---

## NOTIFICATIONS

### GET /api/v1/notifications

Liste des notifications du merchant (paginées, plus récentes en premier).

**Auth :** Bearer JWT

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | query int | 20 | 1-100 |
| `cursor` | query string | null | Pagination |
| `unread_only` | query bool | false | Filtrer non lues |

**Response :**

```json
{
  "data": [
    {
      "id": "uuid",
      "channel": "push",
      "title": "Score dropped 5 points",
      "body": "Your mobile score went from 67 to 62. Reviews+ updated 2h ago.",
      "action_url": "/dashboard/health",
      "category": "score_drop",
      "read": false,
      "sent_at": "2026-04-09T10:00:00Z"
    }
  ],
  "unread_count": 3,
  "pagination": { "has_next": false }
}
```

---

### PATCH /api/v1/notifications/{id}/read

Marquer une notification comme lue.

**Auth :** Bearer JWT

**Response :** `204 No Content`

---

## REPORTS

### GET /api/v1/stores/{store_id}/reports/latest

Dernier rapport hebdomadaire.

**Auth :** Bearer JWT
**Plan :** Starter+

**Response :**

```json
{
  "period": "2026-04-01 to 2026-04-07",
  "score": 67,
  "score_delta": 9,
  "trend": "up",
  "issues_resolved": 3,
  "new_issues": 1,
  "top_action": "Your store is 34% ready for ChatGPT Shopping. 12 products missing GTIN.",
  "report_pdf_url": "https://storage.supabase.co/reports/xxx/2026-04-07.pdf",
  "generated_at": "2026-04-07T09:00:00Z"
}
```

---

## WEBHOOKS (pas de JWT)

### POST /api/v1/webhooks/shopify

Reçoit tous les webhooks Shopify. Validation HMAC.

**Auth :** HMAC (`X-Shopify-Hmac-Sha256`)

**Headers requis :**
- `X-Shopify-Hmac-Sha256` — HMAC signature
- `X-Shopify-Topic` — ex: `products/create`
- `X-Shopify-Shop-Domain` — ex: `mystore.myshopify.com`
- `X-Shopify-Webhook-Id` — idempotency key

**Response :** `200 OK`

```json
{ "status": "accepted" }
```

---

### POST /api/v1/webhooks/stripe

Reçoit tous les webhooks Stripe. Validation signature.

**Auth :** Stripe signature (`Stripe-Signature`)

**Response :** `200 OK`

```json
{ "status": "accepted" }
```

---

## HEALTHCHECK

### GET /api/v1/health

Status du backend. Pas d'auth.

**Auth :** aucune

**Response :**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "db": "connected",
  "redis": "connected",
  "uptime_seconds": 86400
}
```

Status codes :
- `200` — tout est OK
- `503` — DB ou Redis inaccessible

---

## RATE LIMITS

| Plan | Limite | Window |
|------|--------|--------|
| Free | 30 req/min | 60s |
| Starter | 60 req/min | 60s |
| Pro | 120 req/min | 60s |
| Agency | 300 req/min | 60s |

Header retourné quand rate limit dépassé :

```
HTTP 429 Too Many Requests
Retry-After: 42
```

```json
{
  "error": {
    "code": "AUTH_RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded"
  }
}
```
