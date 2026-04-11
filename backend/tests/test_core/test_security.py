"""Tests for Fernet encryption/decryption and HMAC validation."""

import pytest

from app.core.exceptions import AppError
from app.core.security import decrypt_token, encrypt_token, validate_shopify_hmac


@pytest.mark.unit
class TestFernetEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        """Encrypt then decrypt returns the original token."""
        original = "shpat_abc123_test_token"
        encrypted = encrypt_token(original)

        assert encrypted != original
        assert decrypt_token(encrypted) == original

    def test_encrypted_token_is_different_each_time(self):
        """Fernet produces different ciphertext for same input (due to timestamp)."""
        token = "shpat_test_token"
        enc1 = encrypt_token(token)
        enc2 = encrypt_token(token)
        assert enc1 != enc2

    def test_decrypt_invalid_token_raises(self):
        """Decrypting garbage raises AppError with TOKEN_DECRYPT_FAILED."""
        with pytest.raises(AppError) as exc_info:
            decrypt_token("not-a-valid-fernet-token")
        assert exc_info.value.code.value == "TOKEN_DECRYPT_FAILED"
        assert exc_info.value.status_code == 500

    def test_decrypt_empty_string_raises(self):
        """Decrypting empty string raises AppError."""
        with pytest.raises(AppError) as exc_info:
            decrypt_token("")
        assert exc_info.value.code.value == "TOKEN_DECRYPT_FAILED"


@pytest.mark.unit
class TestHMACValidation:
    def test_valid_hmac(self):
        """Valid HMAC is accepted."""
        import base64
        import hashlib
        import hmac

        secret = "test_secret"
        data = b'{"id": 123, "topic": "products/create"}'
        computed = base64.b64encode(
            hmac.new(secret.encode(), data, hashlib.sha256).digest()
        ).decode()

        assert validate_shopify_hmac(data, computed, secret) is True

    def test_invalid_hmac(self):
        """Invalid HMAC is rejected."""
        data = b'{"id": 123}'
        assert validate_shopify_hmac(data, "invalid_hmac_value", "secret") is False

    def test_tampered_payload(self):
        """HMAC computed on original payload fails for tampered payload."""
        import base64
        import hashlib
        import hmac

        secret = "test_secret"
        original = b'{"amount": 100}'
        tampered = b'{"amount": 999}'

        computed = base64.b64encode(
            hmac.new(secret.encode(), original, hashlib.sha256).digest()
        ).decode()

        assert validate_shopify_hmac(original, computed, secret) is True
        assert validate_shopify_hmac(tampered, computed, secret) is False

    def test_empty_data(self):
        """HMAC on empty payload still works (edge case)."""
        import base64
        import hashlib
        import hmac

        secret = "s"
        data = b""
        computed = base64.b64encode(
            hmac.new(secret.encode(), data, hashlib.sha256).digest()
        ).decode()

        assert validate_shopify_hmac(data, computed, secret) is True
