"""Security suite testing IDOR defenses, RBAC enforcement, and HTTP hardening headers."""

import uuid
import pytest
from httpx import AsyncClient


async def register_and_get_token(client: AsyncClient, username: str) -> str:
    unique_user = f"{username}_{uuid.uuid4().hex[:6]}"
    email = f"{unique_user}@example.com"
    pwd = "SecurePassword123!"
    reg = await client.post("/api/v1/auth/register", json={"email": email, "username": unique_user, "password": pwd})
    assert reg.status_code == 201
    res = await client.post("/api/v1/auth/login", json={"username_or_email": unique_user, "password": pwd})
    assert res.status_code == 200
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


@pytest.mark.asyncio
async def test_api_key_scope_enforcement(client: AsyncClient):
    """API keys must strictly enforce granted scopes; unauthorized operations return 403 Forbidden."""
    token = await register_and_get_token(client, "scope_tester")
    jwt_headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a Read-Only API Key (only 'urls:read')
    key_res = await client.post(
        "/api/v1/api-keys/",
        json={"name": "Read-Only Key", "scopes": ["urls:read"]},
        headers=jwt_headers,
    )
    assert key_res.status_code == 201
    read_only_key = key_res.json()["data"]["key"]

    read_headers = {"X-API-Key": read_only_key}

    # Allowed: list URLs with read-only key
    list_res = await client.get("/api/v1/urls/", headers=read_headers)
    assert list_res.status_code == 200

    # Denied (403): Attempting to create URL requires 'urls:write' scope
    write_res = await client.post(
        "/api/v1/urls/",
        json={"original_url": "https://forbidden-write.com"},
        headers=read_headers,
    )
    assert write_res.status_code == 403
    assert "urls:write" in write_res.json()["error"]["message"]

    # Denied (403): Attempting to access analytics requires 'analytics:read' scope
    analytics_res = await client.get("/api/v1/analytics/overview", headers=read_headers)
    assert analytics_res.status_code == 403
    assert "analytics:read" in analytics_res.json()["error"]["message"]

    # 2. Create Full Scope API Key
    full_key_res = await client.post(
        "/api/v1/api-keys/",
        json={"name": "Full Access Key", "scopes": ["urls:read", "urls:write", "analytics:read"]},
        headers=jwt_headers,
    )
    assert full_key_res.status_code == 201
    full_key = full_key_res.json()["data"]["key"]
    full_headers = {"X-API-Key": full_key}

    # Allowed: write URL with full key
    create_success = await client.post(
        "/api/v1/urls/",
        json={"original_url": "https://allowed-write.com"},
        headers=full_headers,
    )
    assert create_success.status_code == 201

    # Allowed: access analytics overview with full key
    overview_success = await client.get("/api/v1/analytics/overview", headers=full_headers)
    assert overview_success.status_code == 200


@pytest.mark.asyncio
async def test_api_key_revocation_enforcement(client: AsyncClient):
    """Revoked API keys must immediately fail authentication with 401 Unauthorized."""
    token = await register_and_get_token(client, "revocation_tester")
    jwt_headers = {"Authorization": f"Bearer {token}"}

    key_res = await client.post(
        "/api/v1/api-keys/",
        json={"name": "To-Be-Revoked Key", "scopes": ["urls:read"]},
        headers=jwt_headers,
    )
    key_id = key_res.json()["data"]["id"]
    raw_key = key_res.json()["data"]["key"]
    key_headers = {"X-API-Key": raw_key}

    # Verify key works before revocation
    res = await client.get("/api/v1/urls/", headers=key_headers)
    assert res.status_code == 200

    # Revoke key
    del_res = await client.delete(f"/api/v1/api-keys/{key_id}", headers=jwt_headers)
    assert del_res.status_code == 200

    # Key must now return 401
    revoked_res = await client.get("/api/v1/urls/", headers=key_headers)
    assert revoked_res.status_code == 401
