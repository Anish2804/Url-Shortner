"""Unit tests for RedirectService covering IP anonymization, hashing, password protection, and cache hits."""

import pytest
from unittest.mock import AsyncMock, patch
from app.core.exceptions import (
    InvalidLinkPasswordException,
    LinkExpiredException,
    LinkPasswordRequiredException,
    NotFoundException,
)
from app.core.security import hash_password
from app.services.redirect_service import RedirectService, anonymize_ip, hash_ip


def test_anonymize_ip_ipv4_and_ipv6_and_invalid():
    # IPv4 masks last octet
    assert anonymize_ip("192.168.1.55") == "192.168.1.0"
    # IPv6 masks to /48
    assert anonymize_ip("2001:db8:85a3::8a2e:370:7334") is not None
    # None and invalid inputs
    assert anonymize_ip(None) is None
    assert anonymize_ip("not-an-ip") is None


def test_hash_ip_deterministic():
    h1 = hash_ip("203.0.113.195")
    h2 = hash_ip("203.0.113.195")
    assert h1 == h2
    assert len(h1) == 64


@pytest.mark.asyncio
async def test_redirect_null_sentinel_raises_not_found():
    mock_repo = AsyncMock()
    service = RedirectService(mock_repo)

    with patch("app.services.redirect_service.cache_service.get_url", new_callable=AsyncMock) as mock_cache:
        # Null sentinel hit returns (True, None)
        mock_cache.return_value = (True, None)
        with pytest.raises(NotFoundException):
            await service.resolve_redirect("non_existent_code")


@pytest.mark.asyncio
async def test_redirect_password_verification():
    mock_repo = AsyncMock()
    service = RedirectService(mock_repo)

    pwd = "SecretPassWord123!"
    p_hash = hash_password(pwd)

    cached_link = {
        "id": "00000000-0000-0000-0000-000000000001",
        "original_url": "https://example.com/protected",
        "short_code": "secret1",
        "password_hash": p_hash,
        "is_one_time": False,
        "is_active": True,
        "redirect_http_code": 302,
    }

    with patch("app.services.redirect_service.cache_service.get_url", new_callable=AsyncMock) as mock_cache:
        mock_cache.return_value = (True, cached_link)

        # 1. Missing password
        with pytest.raises(LinkPasswordRequiredException):
            await service.resolve_redirect("secret1", provided_password=None)

        # 2. Wrong password
        with pytest.raises(InvalidLinkPasswordException):
            await service.resolve_redirect("secret1", provided_password="WrongPassword")

        # 3. Correct password
        dest, code = await service.resolve_redirect("secret1", provided_password=pwd)
        assert dest == "https://example.com/protected"
        assert code == 302


@pytest.mark.asyncio
async def test_redirect_cached_expired():
    mock_repo = AsyncMock()
    service = RedirectService(mock_repo)

    cached_expired = {
        "id": "00000000-0000-0000-0000-000000000002",
        "original_url": "https://example.com/expired",
        "short_code": "expired1",
        "expires_at": "2020-01-01T00:00:00+00:00",
        "is_one_time": False,
        "is_active": True,
    }

    with patch("app.services.redirect_service.cache_service.get_url", new_callable=AsyncMock) as mock_cache:
        mock_cache.return_value = (True, cached_expired)
        with pytest.raises(LinkExpiredException):
            await service.resolve_redirect("expired1")
