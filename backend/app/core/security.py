"""Security utilities : Fernet encryption/decryption, HMAC validation."""

import hashlib
import hmac as hmac_module

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings
from app.core.exceptions import AppError, ErrorCode


def _get_fernet() -> Fernet:
    return Fernet(settings.FERNET_KEY.encode())


def encrypt_token(token: str) -> str:
    """Encrypt a Shopify access token with Fernet.

    Returns the encrypted token as a UTF-8 string (base64).
    """
    try:
        f = _get_fernet()
        return f.encrypt(token.encode()).decode()
    except Exception as exc:
        raise AppError(
            code=ErrorCode.TOKEN_ENCRYPT_FAILED,
            message=f"Failed to encrypt token: {exc}",
            status_code=500,
        ) from exc


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a Fernet-encrypted Shopify access token.

    Returns the plaintext token.
    """
    try:
        f = _get_fernet()
        return f.decrypt(encrypted_token.encode()).decode()
    except InvalidToken as exc:
        raise AppError(
            code=ErrorCode.TOKEN_DECRYPT_FAILED,
            message="Failed to decrypt Shopify token — key rotation or DB corruption",
            status_code=500,
        ) from exc
    except Exception as exc:
        raise AppError(
            code=ErrorCode.TOKEN_DECRYPT_FAILED,
            message=f"Failed to decrypt token: {exc}",
            status_code=500,
        ) from exc


def validate_shopify_hmac(data: bytes, hmac_header: str, secret: str) -> bool:
    """Validate Shopify webhook HMAC-SHA256.

    Uses hmac.compare_digest for constant-time comparison (timing-attack safe).
    """
    import base64

    computed = base64.b64encode(
        hmac_module.new(secret.encode(), data, hashlib.sha256).digest()
    ).decode()
    return hmac_module.compare_digest(computed, hmac_header)
