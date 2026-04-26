"""Hierarchie centralisee d'erreurs StoreMD.

Catalogue complet : docs/ERRORS.md
"""

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
    SHOPIFY_BILLING_FAILED = "SHOPIFY_BILLING_FAILED"

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
    """Base. TOUTES les erreurs de l'app heritent de celle-ci."""

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


class ShopifyError(AppError):
    """Shopify API : rate limit, GraphQL errors, token issues."""


class ScanError(AppError):
    """Scan pipeline : scanner failures, timeouts, limits."""


class AgentError(AppError):
    """Agent IA : Claude API, Mem0, LangGraph."""


class BrowserError(AppError):
    """Playwright : navigation, screenshots, simulations."""


class BillingError(AppError):
    """Stripe : checkout, portal, subscriptions."""


class FixError(AppError):
    """One-Click Fix : apply, revert, approval."""


class ListingError(AppError):
    """Listings : rewrite, bulk import, bulk operations."""
