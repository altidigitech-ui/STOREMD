"""HMAC validation for Shopify webhooks."""

from app.config import settings
from app.core.exceptions import AuthError, ErrorCode
from app.core.security import validate_shopify_hmac


async def verify_shopify_webhook_hmac(body: bytes, hmac_header: str | None) -> None:
    """Validate the X-Shopify-Hmac-Sha256 header on incoming webhooks.

    Raises AuthError if missing or invalid.
    """
    if not hmac_header:
        raise AuthError(
            code=ErrorCode.HMAC_MISSING,
            message="Missing X-Shopify-Hmac-Sha256 header",
            status_code=401,
        )

    if not validate_shopify_hmac(body, hmac_header, settings.SHOPIFY_API_SECRET):
        raise AuthError(
            code=ErrorCode.HMAC_INVALID,
            message="Invalid HMAC — possible tampered webhook",
            status_code=401,
        )
