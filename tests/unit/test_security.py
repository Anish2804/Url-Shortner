"""Unit tests for Argon2id hashing, JWT token lifecycle, and API key cryptography."""

from datetime import timedelta
import pytest
from app.core.exceptions import UnauthorizedException
from app.core.security import (
    constant_time_compare,
    create_access_token,
    decode_access_token,
    generate_api_key,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)


def test_argon2id_password_hashing():
    raw = "SuperSecretPassword123!"
    hashed = hash_password(raw)

    assert hashed.startswith("$argon2id$")
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_access_token_lifecycle():
    subject = "user-12345"
    claims = {"roles": ["user", "admin"], "username": "alice"}
    token = create_access_token(subject, claims=claims, expires_delta=timedelta(minutes=5))

    decoded = decode_access_token(token)
    assert decoded["sub"] == subject
    assert decoded["username"] == "alice"
    assert "admin" in decoded["roles"]
    assert decoded["type"] == "access"


def test_jwt_expired_token():
    token = create_access_token("user-expired", expires_delta=timedelta(seconds=-10))
    with pytest.raises(UnauthorizedException) as exc_info:
        decode_access_token(token)
    assert "expired" in str(exc_info.value).lower()


def test_api_key_generation_and_hashing():
    full_key, prefix, hashed = generate_api_key(prefix="lks")

    assert full_key.startswith("lks_")
    assert prefix in full_key
    assert len(hashed) == 64  # SHA-256 hex string

    # Verify deterministic hash
    assert hash_token(full_key) == hashed


def test_refresh_token_generation():
    raw, hashed = generate_refresh_token()
    assert len(raw) > 30
    assert hash_token(raw) == hashed


def test_constant_time_compare():
    assert constant_time_compare("secret_string_123", "secret_string_123") is True
    assert constant_time_compare("secret_string_123", "different_string_456") is False
