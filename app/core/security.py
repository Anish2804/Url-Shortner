"""Cryptographic security, Argon2id password hashing, JWT and API key management."""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

from app.core.config import settings
from app.core.exceptions import UnauthorizedException


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure datetime object is timezone-aware UTC for cross-database consistency."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

# Argon2id password hasher with production parameters
_ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MB
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hash plaintext password using Argon2id."""
    return _ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against Argon2id hash with constant-time guarantee."""
    try:
        return _ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError):
        return False


def needs_rehash(hashed_password: str) -> bool:
    """Check if password hash parameters need updating."""
    return _ph.check_needs_rehash(hashed_password)


def hash_token(token: str) -> str:
    """Hash sensitive tokens (refresh tokens, API keys) with SHA-256 before DB storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(
    subject: str,
    claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generate signed JWT access token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: Dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }
    if claims:
        payload.update(claims)

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate JWT access token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub", "iat"]},
        )
        if payload.get("type") != "access":
            raise UnauthorizedException("Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException("Access token has expired")
    except jwt.InvalidTokenError as e:
        raise UnauthorizedException(f"Invalid access token: {str(e)}")


def generate_refresh_token() -> Tuple[str, str]:
    """Generate a high-entropy refresh token and its SHA-256 hash.
    
    Returns:
        (raw_token, hashed_token)
    """
    raw_token = secrets.token_urlsafe(64)
    hashed_token = hash_token(raw_token)
    return raw_token, hashed_token


def generate_api_key(prefix: str = "lks") -> Tuple[str, str, str]:
    """Generate a secure API key with prefix.
    
    Format: lks_<prefix_id>_<secret>
    Returns:
        (full_key, key_prefix_for_display, hashed_secret_for_db)
    """
    display_id = secrets.token_hex(4)  # 8 chars for quick identification
    secret_part = secrets.token_urlsafe(32)
    full_key = f"{prefix}_{display_id}_{secret_part}"
    key_prefix = f"{prefix}_{display_id}"
    hashed_key = hash_token(full_key)
    return full_key, key_prefix, hashed_key


def constant_time_compare(val1: str, val2: str) -> bool:
    """HMAC constant-time string comparison to prevent timing attacks."""
    return hmac.compare_digest(val1.encode("utf-8"), val2.encode("utf-8"))
