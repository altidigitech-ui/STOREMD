# ERRORS.md — Catalogue d'erreurs StoreMD

> **Référence unique pour tous les codes d'erreur.**
> **Chaque erreur a un code, un HTTP status, un message, et un handler frontend.**

---

## ARCHITECTURE ERREURS

### Hiérarchie des classes

```python
# app/core/exceptions.py

from enum import StrEnum

class ErrorCode(StrEnum):
    """Tous les codes d'erreur de l'application.
    
    Convention : DOMAIN_ACTION_DETAIL
    """

    # === Auth (1xxx) ===
    JWT_INVALID = "AUTH_JWT_INVALID"
    JWT_EXPIRED = "AUTH_JWT_EXPIRED"
    MERCHANT_NOT_FOUND = "AUTH_MERCHANT_NOT_FOUND"
    STORE_NOT_FOUND = "AUTH_STORE_NOT_FOUND"
    STORE_ACCESS_DENIED = "AUTH_STORE_ACCESS_DENIED"
    PLAN_REQUIRED = "AUTH_PLAN_REQUIRED"
    RATE_LIMIT_EXCEEDED = "AUTH_RATE_LIMIT_EXCEEDED"

    # === OAuth (2xxx) ===
    INVALID_SHOP_DOMAIN = "OAUTH_INVALID_SHOP_DOMAIN"
    OAUTH_STATE_INVALID = "OAUTH_STATE_INVALID"
    OAUTH_CODE_EXCHANGE_FAILED = "OAUTH_CODE_EXCHANGE_FAILED"
    OAUTH_TOKEN_MISSING = "OAUTH_TOKEN_MISSING"

    # === HMAC / Webhooks (3xxx) ===
    HMAC_MISSING = "WEBHOOK_HMAC_MISSING"
    HMAC_INVALID = "WEBHOOK_HMAC_INVALID"
    STRIPE_SIGNATURE_INVALID = "WEBHOOK_STRIPE_SIGNATURE_INVALID"
    STRIPE_PAYLOAD_INVALID = "WEBHOOK_STRIPE_PAYLOAD_INVALID"
    WEBHOOK_DUPLICATE = "WEBHOOK_DUPLICATE"
    WEBHOOK_PROCESSING_FAILED = "WEBHOOK_PROCESSING_FAILED"

    # === Shopify API (4xxx) ===
    SHOPIFY_RATE_LIMIT = "SHOPIFY_RATE_LIMIT"
    SHOPIFY_GRAPHQL_ERROR = "SHOPIFY_GRAPHQL_ERROR"
    SHOPIFY_TOKEN_EXPIRED = "SHOPIFY_TOKEN_EXPIRED"
    SHOPIFY_TOKEN_REVOKED = "SHOPIFY_TOKEN_REVOKED"
    SHOPIFY_SCOPE_INSUFFICIENT = "SHOPIFY_SCOPE_INSUFFICIENT"
    SHOPIFY_STORE_NOT_FOUND = "SHOPIFY_STORE_NOT_FOUND"
    SHOPIFY_API_UNAVAILABLE = "SHOPIFY_API_UNAVAILABLE"

    # === Token Encryption (5xxx) ===
    TOKEN_DECRYPT_FAILED = "TOKEN_DECRYPT_FAILED"
    TOKEN_ENCRYPT_FAILED = "TOKEN_ENCRYPT_FAILED"

    # === Scan (6xxx) ===
    SCAN_FAILED = "SCAN_FAILED"
    SCAN_TIMEOUT = "SCAN_TIMEOUT"
    SCAN_NOT_FOUND = "SCAN_NOT_FOUND"
    SCAN_ALREADY_RUNNING = "SCAN_ALREADY_RUNNING"
    SCAN_LIMIT_REACHED = "SCAN_LIMIT_REACHED"
    SCANNER_FAILED = "SCANNER_FAILED"
    SCAN_PARTIAL = "SCAN_PARTIAL"

    # === Agent / LLM (7xxx) ===
    CLAUDE_API_ERROR = "AGENT_CLAUDE_API_ERROR"
    CLAUDE_API_TIMEOUT = "AGENT_CLAUDE_API_TIMEOUT"
    CLAUDE_API_RATE_LIMIT = "AGENT_CLAUDE_API_RATE_LIMIT"
    CLAUDE_API_CONTEXT_TOO_LONG = "AGENT_CLAUDE_CONTEXT_TOO_LONG"
    MEM0_ERROR = "AGENT_MEM0_ERROR"
    MEM0_UNAVAILABLE = "AGENT_MEM0_UNAVAILABLE"
    LANGGRAPH_ERROR = "AGENT_LANGGRAPH_ERROR"

    # === Browser Automation (8xxx) ===
    PLAYWRIGHT_ERROR = "BROWSER_PLAYWRIGHT_ERROR"
    PLAYWRIGHT_TIMEOUT = "BROWSER_PLAYWRIGHT_TIMEOUT"
    PLAYWRIGHT_NAVIGATION_FAILED = "BROWSER_NAVIGATION_FAILED"
    SCREENSHOT_FAILED = "BROWSER_SCREENSHOT_FAILED"
    SIMULATION_FAILED = "BROWSER_SIMULATION_FAILED"

    # === Billing / Stripe (9xxx) ===
    STRIPE_CHECKOUT_FAILED = "BILLING_CHECKOUT_FAILED"
    STRIPE_PORTAL_FAILED = "BILLING_PORTAL_FAILED"
    STRIPE_CUSTOMER_NOT_FOUND = "BILLING_CUSTOMER_NOT_FOUND"
    STRIPE_SUBSCRIPTION_NOT_FOUND = "BILLING_SUBSCRIPTION_NOT_FOUND"
    STRIPE_WEBHOOK_HANDLER_FAILED = "BILLING_WEBHOOK_HANDLER_FAILED"

    # === Fix Engine (10xxx) ===
    FIX_NOT_FOUND = "FIX_NOT_FOUND"
    FIX_ALREADY_APPLIED = "FIX_ALREADY_APPLIED"
    FIX_APPLY_FAILED = "FIX_APPLY_FAILED"
    FIX_REVERT_FAILED = "FIX_REVERT_FAILED"
    FIX_NOT_REVERTABLE = "FIX_NOT_REVERTABLE"
    FIX_APPROVAL_REQUIRED = "FIX_APPROVAL_REQUIRED"

    # === Listings (11xxx) ===
    LISTING_NOT_FOUND = "LISTING_NOT_FOUND"
    LISTING_REWRITE_FAILED = "LISTING_REWRITE_FAILED"
    BULK_IMPORT_FAILED = "LISTING_BULK_IMPORT_FAILED"
    BULK_IMPORT_INVALID_CSV = "LISTING_BULK_IMPORT_INVALID_CSV"
    BULK_OPERATION_LIMIT = "LISTING_BULK_OPERATION_LIMIT"

    # === Notifications (12xxx) ===
    PUSH_DELIVERY_FAILED = "NOTIFICATION_PUSH_FAILED"
    EMAIL_DELIVERY_FAILED = "NOTIFICATION_EMAIL_FAILED"
    NOTIFICATION_NOT_FOUND = "NOTIFICATION_NOT_FOUND"

    # === Validation (13xxx) ===
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_MODULE = "VALIDATION_INVALID_MODULE"
    INVALID_INPUT = "VALIDATION_INVALID_INPUT"

    # === Internal (99xxx) ===
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DATABASE_ERROR = "INTERNAL_DATABASE_ERROR"
    REDIS_ERROR = "INTERNAL_REDIS_ERROR"
    REDIS_UNAVAILABLE = "INTERNAL_REDIS_UNAVAILABLE"


class AppError(Exception):
    """Base. TOUTES les erreurs de l'app héritent de celle-ci."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int = 500,
        context: dict | None = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.context = context or {}
        super().__init__(message)

    def to_dict(self) -> dict:
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
            }
        }


class AuthError(AppError):
    """Auth, JWT, permissions, plan checking, rate limit."""
    pass

class ShopifyError(AppError):
    """Shopify API : rate limit, GraphQL errors, token issues."""
    pass

class ScanError(AppError):
    """Scan pipeline : scanner failures, timeouts, limits."""
    pass

class AgentError(AppError):
    """Agent IA : Claude API, Mem0, LangGraph."""
    pass

class BrowserError(AppError):
    """Playwright : navigation, screenshots, simulations."""
    pass

class BillingError(AppError):
    """Stripe : checkout, portal, subscriptions."""
    pass

class FixError(AppError):
    """One-Click Fix : apply, revert, approval."""
    pass

class ListingError(AppError):
    """Listings : rewrite, bulk import, bulk operations."""
    pass
```

---

## HANDLER GLOBAL

```python
# app/main.py

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    """Handler pour toutes les erreurs métier."""
    logger.error(
        "app_error",
        code=exc.code.value,
        message=exc.message,
        status_code=exc.status_code,
        path=request.url.path,
        **exc.context,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Handler pour les erreurs de validation Pydantic."""
    logger.warning(
        "validation_error",
        path=request.url.path,
        errors=str(exc.errors()),
    )
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": ErrorCode.VALIDATION_ERROR.value,
                "message": "Validation failed",
                "details": exc.errors(),
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    """Handler catch-all pour les erreurs non gérées.
    
    Log l'erreur complète, mais retourne un message générique au client.
    Sentry capture automatiquement.
    """
    logger.exception(
        "unhandled_error",
        path=request.url.path,
        error_type=type(exc).__name__,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": ErrorCode.INTERNAL_ERROR.value,
                "message": "An unexpected error occurred",
            }
        },
    )
```

---

## CATALOGUE COMPLET

### Auth Errors

| Code | HTTP | Message | Quand | Handler frontend |
|------|------|---------|-------|-----------------|
| `AUTH_JWT_INVALID` | 401 | Invalid or expired token | JWT manquant, malformé, ou signature invalide | Redirect → login |
| `AUTH_JWT_EXPIRED` | 401 | Token expired | JWT expiré (Supabase session TTL) | Refresh token ou redirect → login |
| `AUTH_MERCHANT_NOT_FOUND` | 401 | Merchant profile not found | JWT valide mais pas de profil merchant en DB (corruption) | Error page + contact support |
| `AUTH_STORE_NOT_FOUND` | 404 | Store not found or access denied | Store ID invalide ou n'appartient pas au merchant | Redirect → dashboard (store list) |
| `AUTH_STORE_ACCESS_DENIED` | 403 | Access denied to this store | Merchant tente d'accéder au store d'un autre merchant | Error page |
| `AUTH_PLAN_REQUIRED` | 403 | Feature requires {plan} plan or above | Feature payante, plan insuffisant | Afficher upgrade modal avec le plan requis |
| `AUTH_RATE_LIMIT_EXCEEDED` | 429 | Rate limit exceeded | Trop de requêtes, retry après X secondes | Afficher "Too many requests, please wait" + `retry_after` du header |

### OAuth Errors

| Code | HTTP | Message | Quand | Handler frontend |
|------|------|---------|-------|-----------------|
| `OAUTH_INVALID_SHOP_DOMAIN` | 400 | Invalid shop domain | Domain ne matche pas `*.myshopify.com` | Error page "Invalid store URL" |
| `OAUTH_STATE_INVALID` | 403 | Invalid OAuth state — possible CSRF | State mismatch ou expiré (>5 min) | Redirect → reinstall flow |
| `OAUTH_CODE_EXCHANGE_FAILED` | 502 | Failed to exchange OAuth code | Shopify refuse le code (expiré, déjà utilisé) | Error page "Installation failed, try again" |
| `OAUTH_TOKEN_MISSING` | 500 | Access token not received | Shopify retourne un response sans token | Error page + contact support |

### Webhook Errors

| Code | HTTP | Message | Quand | Handler frontend |
|------|------|---------|-------|-----------------|
| `WEBHOOK_HMAC_MISSING` | 401 | Missing HMAC header | Webhook sans header X-Shopify-Hmac-Sha256 | N/A (backend only) |
| `WEBHOOK_HMAC_INVALID` | 401 | Invalid HMAC | HMAC ne matche pas (possible attaque) | N/A |
| `WEBHOOK_STRIPE_SIGNATURE_INVALID` | 401 | Invalid Stripe signature | Signature Stripe ne matche pas | N/A |
| `WEBHOOK_STRIPE_PAYLOAD_INVALID` | 400 | Invalid Stripe payload | Payload JSON malformé | N/A |
| `WEBHOOK_DUPLICATE` | 200 | Already processed | Webhook déjà vu (idempotency) | N/A (retourne 200 OK) |
| `WEBHOOK_PROCESSING_FAILED` | 500 | Webhook processing failed | Erreur pendant le traitement async | N/A (retry automatique Shopify/Stripe) |

### Shopify API Errors

| Code | HTTP | Message | Quand | Handler frontend |
|------|------|---------|-------|-----------------|
| `SHOPIFY_RATE_LIMIT` | 429 | Shopify API rate limit exceeded | 429 de Shopify après retries | Toast "Shopify is busy, scan will retry" |
| `SHOPIFY_GRAPHQL_ERROR` | 502 | Shopify GraphQL error: {detail} | Erreur GraphQL (query invalide, data issue) | Toast "Error fetching store data" |
| `SHOPIFY_TOKEN_EXPIRED` | 401 | Shopify access token expired | Token invalide (merchant a révoqué ?) | Prompt reinstall |
| `SHOPIFY_TOKEN_REVOKED` | 401 | Shopify access token revoked | App désinstallée ou permissions révoquées | Prompt reinstall |
| `SHOPIFY_SCOPE_INSUFFICIENT` | 403 | Missing required Shopify scope: {scope} | App n'a pas le scope nécessaire (write_products pour One-Click Fix) | Prompt re-authorize |
| `SHOPIFY_STORE_NOT_FOUND` | 404 | Shopify store not found | Shop domain n'existe pas ou a été supprimé | Error page |
| `SHOPIFY_API_UNAVAILABLE` | 503 | Shopify API unavailable | Shopify en panne (très rare) | Toast "Shopify is down, try later" |

### Token Errors

| Code | HTTP | Message | Quand | Handler frontend |
|------|------|---------|-------|-----------------|
| `TOKEN_DECRYPT_FAILED` | 500 | Failed to decrypt Shopify token | Fernet key rotation incorrecte ou DB corrompue | Error page + contact support |
| `TOKEN_ENCRYPT_FAILED` | 500 | Failed to encrypt Shopify token | Fernet key invalide | Error page + contact support |

### Scan Errors

| Code | HTTP | Message | Quand | Handler frontend |
|------|------|---------|-------|-----------------|
| `SCAN_FAILED` | 500 | Scan failed: {reason} | Erreur non-récupérable pendant le scan | Afficher "Scan failed" + reason + retry button |
| `SCAN_TIMEOUT` | 504 | Scan timed out after {seconds}s | Scan dépasse le timeout (5 min default) | Afficher "Scan took too long" + retry |
| `SCAN_NOT_FOUND` | 404 | Scan not found | Scan ID invalide | Redirect → scan list |
| `SCAN_ALREADY_RUNNING` | 409 | A scan is already running for this store | Merchant trigger un scan alors qu'un autre tourne | Afficher "Scan in progress" + lien vers le scan actif |
| `SCAN_LIMIT_REACHED` | 403 | Scan limit reached for this billing period | Usage limit du plan dépassé | Afficher upgrade modal |
| `SCANNER_FAILED` | 500 | Scanner {name} failed: {reason} | Un scanner spécifique a échoué (scan continue, marqué partial) | Afficher warning "Some checks failed" dans les résultats |
| `SCAN_PARTIAL` | 200 | Scan completed with partial results | Certains scanners ont échoué, le scan est marqué partial | Afficher les résultats + warning sur les scanners manquants |

### Agent / LLM Errors

| Code | HTTP | Message | Quand | Handler frontend |
|------|------|---------|-------|-----------------|
| `AGENT_CLAUDE_API_ERROR` | 502 | Claude API error: {detail} | Erreur API Anthropic | Toast "AI analysis temporarily unavailable" |
| `AGENT_CLAUDE_API_TIMEOUT` | 504 | Claude API timeout | Timeout API Anthropic (>30s) | Toast "AI analysis timed out, using basic analysis" |
| `AGENT_CLAUDE_API_RATE_LIMIT` | 429 | Claude API rate limit | Rate limit Anthropic | Retry automatique avec backoff |
| `AGENT_CLAUDE_CONTEXT_TOO_LONG` | 400 | Context too long for Claude API | Trop de données pour le context window | Tronquer le contexte, retry |
| `AGENT_MEM0_ERROR` | 500 | Mem0 error: {detail} | Erreur Mem0 (stockage/recall) | Continuer sans mémoire, log warning |
| `AGENT_MEM0_UNAVAILABLE` | 503 | Mem0 service unavailable | Mem0 down | Continuer sans mémoire (dégradé gracefully) |
| `AGENT_LANGGRAPH_ERROR` | 500 | LangGraph orchestration error | Erreur dans le graph (node failure, edge invalide) | Scan failed + retry |

### Browser Automation Errors

| Code | HTTP | Message | Quand | Handler frontend |
|------|------|---------|-------|-----------------|
| `BROWSER_PLAYWRIGHT_ERROR` | 500 | Playwright error: {detail} | Erreur Playwright générique | Toast "Browser test failed" |
| `BROWSER_PLAYWRIGHT_TIMEOUT` | 504 | Page load timed out after {seconds}s | Page ne charge pas en <60s | Afficher "Store too slow for browser test" |
| `BROWSER_NAVIGATION_FAILED` | 502 | Failed to navigate to {url} | URL inaccessible (DNS, SSL, 5xx) | Afficher "Could not access your store" |
| `BROWSER_SCREENSHOT_FAILED` | 500 | Screenshot capture failed | Playwright ne peut pas capturer | Skip visual test, continuer scan |
| `BROWSER_SIMULATION_FAILED` | 500 | User simulation failed at step {step} | Un step du parcours échoue (bouton introuvable, etc.) | Afficher résultats partiels |

### Billing Errors

| Code | HTTP | Message | Quand | Handler frontend |
|------|------|---------|-------|-----------------|
| `BILLING_CHECKOUT_FAILED` | 502 | Failed to create checkout session | Stripe Checkout échoue | Toast "Payment setup failed, try again" |
| `BILLING_PORTAL_FAILED` | 502 | Failed to create customer portal | Stripe Portal échoue | Toast "Settings unavailable, try again" |
| `BILLING_CUSTOMER_NOT_FOUND` | 404 | Stripe customer not found | Customer ID invalide | Redirect → pricing (créer un nouveau customer) |
| `BILLING_SUBSCRIPTION_NOT_FOUND` | 404 | Subscription not found | Subscription ID invalide | Redirect → pricing |
| `BILLING_WEBHOOK_HANDLER_FAILED` | 500 | Billing webhook handler failed | Erreur traitement webhook Stripe | N/A (retry automatique Stripe) |

### Fix Engine Errors

| Code | HTTP | Message | Quand | Handler frontend |
|------|------|---------|-------|-----------------|
| `FIX_NOT_FOUND` | 404 | Fix not found | Fix ID invalide | Redirect → scan results |
| `FIX_ALREADY_APPLIED` | 409 | Fix already applied | Merchant re-clique sur un fix déjà appliqué | Toast "Already fixed" |
| `FIX_APPLY_FAILED` | 500 | Failed to apply fix: {reason} | Shopify API write échoue | Toast "Fix failed" + reason + retry button |
| `FIX_REVERT_FAILED` | 500 | Failed to revert fix: {reason} | Revert échoue (store a changé entre temps) | Toast "Revert failed" + manual instructions |
| `FIX_NOT_REVERTABLE` | 400 | This fix cannot be reverted | Fix sans before_state ou trop ancien | Toast "Cannot undo this fix" |
| `FIX_APPROVAL_REQUIRED` | 403 | Fix requires merchant approval before applying | Fix auto-triggered sans approbation (ne devrait pas arriver) | Afficher preview + approve button |

### Listing Errors

| Code | HTTP | Message | Quand | Handler frontend |
|------|------|---------|-------|-----------------|
| `LISTING_NOT_FOUND` | 404 | Product not found | Product ID Shopify invalide ou supprimé | Skip dans le scan |
| `LISTING_REWRITE_FAILED` | 500 | Failed to rewrite listing: {reason} | Claude API ou Shopify write échoue | Toast "Rewrite failed" + retry |
| `LISTING_BULK_IMPORT_FAILED` | 500 | Bulk import failed: {reason} | Import CSV échoue | Afficher erreurs de validation par ligne |
| `LISTING_BULK_IMPORT_INVALID_CSV` | 400 | Invalid CSV: {detail} | CSV malformé (encoding, colonnes manquantes) | Afficher les erreurs + lien template CSV |
| `LISTING_BULK_OPERATION_LIMIT` | 403 | Bulk operation limit reached | Limite du plan dépassée | Upgrade modal |

### Notification Errors

| Code | HTTP | Message | Quand | Handler frontend |
|------|------|---------|-------|-----------------|
| `NOTIFICATION_PUSH_FAILED` | 500 | Push notification delivery failed | Web-push échoue (subscription expirée, browser bloqué) | Marquer comme non-livré, fallback email |
| `NOTIFICATION_EMAIL_FAILED` | 500 | Email delivery failed | Resend API échoue | Retry automatique, marquer comme non-livré |
| `NOTIFICATION_NOT_FOUND` | 404 | Notification not found | Notification ID invalide | Ignore |

### Validation Errors

| Code | HTTP | Message | Quand | Handler frontend |
|------|------|---------|-------|-----------------|
| `VALIDATION_ERROR` | 422 | Validation failed | Pydantic validation échoue | Afficher les champs en erreur |
| `VALIDATION_INVALID_MODULE` | 400 | Invalid module: {name} | Module demandé n'existe pas | Afficher les modules disponibles |
| `VALIDATION_INVALID_INPUT` | 400 | Invalid input: {detail} | Input non validé (catch-all) | Afficher le détail |

### Internal Errors

| Code | HTTP | Message exposé | Quand | Handler frontend |
|------|------|----------------|-------|-----------------|
| `INTERNAL_ERROR` | 500 | An unexpected error occurred | Erreur non-gérée (catch-all) | Error page générique + "try again or contact support" |
| `INTERNAL_DATABASE_ERROR` | 500 | An unexpected error occurred | Supabase down ou query échoue | Error page générique (JAMAIS exposer le détail DB) |
| `INTERNAL_REDIS_ERROR` | 500 | An unexpected error occurred | Redis down | Error page générique |
| `INTERNAL_REDIS_UNAVAILABLE` | 503 | Service temporarily unavailable | Redis inaccessible au startup | Healthcheck retourne 503, Railway restart auto |

---

## RÉPONSE API — FORMAT

### Succès

```json
{
  "score": 72,
  "issues": [...]
}
```

Pas d'enveloppe `{"data": ...}` — le payload EST la data. Conforme aux conventions REST simples.

### Erreur

```json
{
  "error": {
    "code": "AUTH_PLAN_REQUIRED",
    "message": "Feature 'visual_store_test' requires pro plan or above"
  }
}
```

### Erreur de validation (422)

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": [
      {
        "loc": ["body", "modules", 0],
        "msg": "Invalid modules: {'invalid_module'}",
        "type": "value_error"
      }
    ]
  }
}
```

---

## FRONTEND — ERROR HANDLING

```typescript
// lib/api.ts

class ApiError extends Error {
  code: string;
  statusCode: number;
  details?: unknown;

  constructor(code: string, message: string, statusCode: number, details?: unknown) {
    super(message);
    this.code = code;
    this.statusCode = statusCode;
    this.details = details;
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const error = body?.error;
    throw new ApiError(
      error?.code ?? "UNKNOWN_ERROR",
      error?.message ?? "An error occurred",
      response.status,
      error?.details,
    );
  }
  return response.json() as Promise<T>;
}
```

```typescript
// Composant — pattern de gestion d'erreur

import { useToast } from "@/components/ui/toast";

function ScanResults() {
  const { toast } = useToast();

  const handleScanError = (error: ApiError) => {
    switch (error.code) {
      case "AUTH_PLAN_REQUIRED":
        // Ouvrir le modal d'upgrade
        openUpgradeModal(error.message);
        break;

      case "SCAN_ALREADY_RUNNING":
        toast({ title: "Scan in progress", description: "Please wait for the current scan to complete." });
        break;

      case "SCAN_LIMIT_REACHED":
        openUpgradeModal("You've reached your scan limit for this month.");
        break;

      case "SHOPIFY_RATE_LIMIT":
        toast({ title: "Shopify is busy", description: "Your scan will retry automatically." });
        break;

      case "AUTH_JWT_INVALID":
      case "AUTH_JWT_EXPIRED":
        // Redirect to re-auth
        router.push("/api/v1/auth/install");
        break;

      default:
        toast({ title: "Error", description: error.message, variant: "destructive" });
    }
  };
}
```

---

## GRACEFUL DEGRADATION

Certaines erreurs ne doivent PAS bloquer le scan complet. Le scan continue en mode dégradé :

| Erreur | Comportement | Résultat |
|--------|-------------|----------|
| `AGENT_MEM0_UNAVAILABLE` | Scan continue SANS mémoire historique | Résultats moins personnalisés mais fonctionnels |
| `AGENT_CLAUDE_API_TIMEOUT` | Utiliser une analyse basique (rules-based) au lieu de Claude | Score calculé, mais pas de recommandations en langage naturel |
| `SCANNER_FAILED` (1 scanner) | Les autres scanners continuent | Scan marqué `partial_scan: true`, warning affiché |
| `BROWSER_PLAYWRIGHT_TIMEOUT` | Skip les tests browser | Scan complété sans le module Browser |
| `NOTIFICATION_PUSH_FAILED` | Fallback vers email | Notification livrée par un autre canal |
| `NOTIFICATION_EMAIL_FAILED` | Marquer comme non-livré | Visible uniquement in-app |

```python
# Pattern dans l'orchestrateur

async def run_scanners(self, state: AgentState) -> AgentState:
    for scanner in self.get_scanners(state.modules):
        try:
            result = await scanner.scan(state.store_id, self.shopify, state.historical_context)
            state.scanner_results[scanner.name] = result
        except Exception as exc:
            logger.warning("scanner_failed", scanner=scanner.name, error=str(exc))
            state.errors.append(f"Scanner {scanner.name} failed: {str(exc)}")
            # Continuer avec les autres scanners — pas de raise
    return state
```
