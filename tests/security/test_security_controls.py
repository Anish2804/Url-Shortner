"""Security suite testing IDOR defenses, RBAC enforcement, and HTTP hardening headers."""

import pytest
from httpx import AsyncClient


async def register_and_get_token(client: AsyncClient, username: str) -> str:
    email = f"{username}@example.com"
    pwd = "SecurePassword123!"
    await client.post("/api/v1/auth/register", json={"email": email, "username": username, "password": pwd})
    res = await client.post("/api/v1/auth/login", json={"username_or_email": username, "password": pwd})
    return res.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_idor_protection_on_url_modification(client: AsyncClient):
    """User B must NOT be able to modify or delete User A's URL."""
    token_a = await register_and_get_token(client, "user_a")
    token_b = await register_and_get_token(client, "user_b")

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A creates a URL
    create_res = await client.post(
        "/api/v1/urls/",
        json={"original_url": "https://user-a-private-site.com"},
        headers=headers_a,
    )
    assert create_res.status_code == 201
    short_code = create_res.json()["data"]["short_code"]

    # User B attempts to modify User A's URL -> Must fail
    attack_res = await client.put(
        f"/api/v1/urls/{short_code}",
        json={"original_url": "https://malicious-redirect.com"},
        headers=headers_b,
    )
    assert attack_res.status_code in (400, 403)

    # User B attempts to delete User A's URL -> Must fail
    delete_res = await client.delete(
        f"/api/v1/urls/{short_code}",
        headers=headers_b,
    )
    assert delete_res.status_code in (400, 403)

    # User B attempts to inspect User A's URL analytics -> Must fail
    analytics_res = await client.get(
        f"/api/v1/analytics/urls/{short_code}",
        headers=headers_b,
    )
    assert analytics_res.status_code in (400, 403)


@pytest.mark.asyncio
async def test_security_headers_and_request_correlation(client: AsyncClient):
    """All responses must contain OWASP security headers and correlation ID."""
    res = await client.get("/health")
    assert res.status_code == 200

    # OWASP Security Headers
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["x-frame-options"] == "DENY"
    assert "max-age" in res.headers["strict-transport-security"]
    assert "default-src" in res.headers["content-security-policy"]

    # Correlation ID
    assert "x-request-id" in res.headers
    assert len(res.headers["x-request-id"]) > 10


@pytest.mark.asyncio
async def test_admin_rbac_enforcement(client: AsyncClient):
    """Regular users without administrator role must be denied from /api/v1/admin endpoints."""
    token = await register_and_get_token(client, "regular_joe")
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.get("/api/v1/admin/abuse-reports", headers=headers)
    assert res.status_code == 403
    assert "privileges required" in res.json()["error"]["message"].lower()
