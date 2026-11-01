"""API tests for machine API keys, analytics reporting, and CSV export."""

import pytest
from httpx import AsyncClient


async def get_auth_headers(client: AsyncClient, username: str = "analytics_user") -> dict:
    email = f"{username}@example.com"
    pwd = "SecurePassword123!"
    await client.post("/api/v1/auth/register", json={"email": email, "username": username, "password": pwd})
    login_res = await client.post("/api/v1/auth/login", json={"username_or_email": username, "password": pwd})
    token = login_res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_api_key_lifecycle_and_machine_authentication(client: AsyncClient):
    headers = await get_auth_headers(client, "robot_admin")

    # 1. Create API key
    key_payload = {
        "name": "CI/CD Deployment Key",
        "scopes": ["urls:read", "urls:write"],
        "expires_in_days": 30,
    }
    create_res = await client.post("/api/v1/api-keys/", json=key_payload, headers=headers)
    assert create_res.status_code == 201
    key_data = create_res.json()["data"]
    raw_key = key_data["key"]
    key_id = key_data["id"]
    assert raw_key.startswith("lks_")

    # 2. Use raw key in X-API-Key header to create a short link without JWT
    machine_headers = {"X-API-Key": raw_key}
    create_url_res = await client.post(
        "/api/v1/urls/",
        json={"original_url": "https://kubernetes.io"},
        headers=machine_headers,
    )
    assert create_url_res.status_code == 201
    assert create_url_res.json()["data"]["original_url"] == "https://kubernetes.io"

    # 3. List API keys
    list_res = await client.get("/api/v1/api-keys/", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) >= 1

    # 4. Revoke API key
    revoke_res = await client.delete(f"/api/v1/api-keys/{key_id}", headers=headers)
    assert revoke_res.status_code == 200

    # 5. Subsequent request with revoked key must fail with 401
    fail_res = await client.post(
        "/api/v1/urls/",
        json={"original_url": "https://docker.com"},
        headers=machine_headers,
    )
    assert fail_res.status_code == 401


@pytest.mark.asyncio
async def test_analytics_summary_and_csv_export(client: AsyncClient):
    headers = await get_auth_headers(client, "metrics_fan")

    # Create link
    url_res = await client.post(
        "/api/v1/urls/",
        json={"original_url": "https://grafana.com"},
        headers=headers,
    )
    short_code = url_res.json()["data"]["short_code"]

    # Trigger redirects to generate click events
    await client.get(f"/{short_code}", headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0"})
    await client.get(f"/{short_code}", headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0) Safari/604.1", "Referer": "https://twitter.com"})

    # Fetch URL analytics summary
    analytics_res = await client.get(f"/api/v1/analytics/urls/{short_code}", headers=headers)
    assert analytics_res.status_code == 200
    summary = analytics_res.json()["data"]
    assert summary["short_code"] == short_code
    assert "devices" in summary
    assert "browsers" in summary
    assert "time_series" in summary

    # Export analytics CSV
    csv_res = await client.get(f"/api/v1/analytics/urls/{short_code}/export", headers=headers)
    assert csv_res.status_code == 200
    assert csv_res.headers["content-type"].startswith("text/csv")
    assert "Event ID,Short Code,Timestamp UTC" in csv_res.text

    # Account overview
    overview_res = await client.get("/api/v1/analytics/overview", headers=headers)
    assert overview_res.status_code == 200
    overview = overview_res.json()["data"]
    assert overview["total_urls"] >= 1
