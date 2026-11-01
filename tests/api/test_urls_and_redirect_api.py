"""API tests for URL creation, bulk ingest, custom aliases, QR codes, and redirects."""

import pytest
from httpx import AsyncClient


async def get_auth_headers(client: AsyncClient, username: str = "url_owner") -> dict:
    email = f"{username}@example.com"
    pwd = "SecurePassword123!"
    await client.post("/api/v1/auth/register", json={"email": email, "username": username, "password": pwd})
    login_res = await client.post("/api/v1/auth/login", json={"username_or_email": username, "password": pwd})
    token = login_res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_url_creation_and_redirection(client: AsyncClient):
    headers = await get_auth_headers(client, "alice")

    # 1. Create standard short link
    create_payload = {
        "original_url": "https://python.org/downloads",
        "title": "Python Downloads",
        "redirect_http_code": 302,
    }
    create_res = await client.post("/api/v1/urls/", json=create_payload, headers=headers)
    assert create_res.status_code == 201
    url_data = create_res.json()["data"]
    short_code = url_data["short_code"]
    assert short_code

    # 2. Test high-speed redirect
    # Follow redirects = False to inspect HTTP 302 and Location header
    redir_res = await client.get(f"/{short_code}", follow_redirects=False)
    assert redir_res.status_code == 302
    assert redir_res.headers["location"] == "https://python.org/downloads"

    # 3. Create custom alias
    alias_payload = {
        "original_url": "https://fastapi.tiangolo.com",
        "custom_alias": "fastapi-docs",
    }
    alias_res = await client.post("/api/v1/urls/", json=alias_payload, headers=headers)
    assert alias_res.status_code == 201

    # 4. Redirect via alias
    alias_redir = await client.get("/fastapi-docs", follow_redirects=False)
    assert alias_redir.status_code == 302
    assert alias_redir.headers["location"] == "https://fastapi.tiangolo.com"

    # 5. Reject duplicate alias
    dup_res = await client.post("/api/v1/urls/", json=alias_payload, headers=headers)
    assert dup_res.status_code == 409

    # 6. Generate QR code
    qr_res = await client.get(f"/api/v1/urls/{short_code}/qr")
    assert qr_res.status_code == 200
    assert qr_res.headers["content-type"] == "image/png"
    assert len(qr_res.content) > 100


@pytest.mark.asyncio
async def test_bulk_url_creation(client: AsyncClient):
    headers = await get_auth_headers(client, "bulk_creator")

    bulk_payload = {
        "items": [
            {"original_url": "https://docs.python.org/3/whatsnew/3.12.html", "title": "What's New 3.12"},
            {"original_url": "https://docs.python.org/3/whatsnew/3.13.html", "title": "What's New 3.13"},
            {"original_url": "https://docs.python.org/3/whatsnew/3.14.html", "title": "What's New 3.14"},
        ]
    }
    res = await client.post("/api/v1/urls/bulk", json=bulk_payload, headers=headers)
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["total_requested"] == 3
    assert data["total_successful"] == 3
    assert len(data["created"]) == 3


@pytest.mark.asyncio
async def test_password_protected_link(client: AsyncClient):
    headers = await get_auth_headers(client, "secret_sharer")

    create_payload = {
        "original_url": "https://confidential.example.com/report",
        "password": "LinkSecretPassword123!",
    }
    res = await client.post("/api/v1/urls/", json=create_payload, headers=headers)
    assert res.status_code == 201
    short_code = res.json()["data"]["short_code"]

    # Redirect without password -> 401
    no_pwd_res = await client.get(f"/{short_code}", follow_redirects=False)
    assert no_pwd_res.status_code == 401

    # Redirect with wrong password -> 403
    wrong_pwd_res = await client.get(f"/{short_code}?pwd=WrongPassword", follow_redirects=False)
    assert wrong_pwd_res.status_code == 403

    # Redirect with correct password -> 302
    good_pwd_res = await client.get(f"/{short_code}?pwd=LinkSecretPassword123!", follow_redirects=False)
    assert good_pwd_res.status_code == 302
    assert good_pwd_res.headers["location"] == "https://confidential.example.com/report"


@pytest.mark.asyncio
async def test_one_time_link_atomic_consumption(client: AsyncClient):
    headers = await get_auth_headers(client, "one_time_user")

    create_payload = {
        "original_url": "https://one-time.example.com/secret-token",
        "is_one_time": True,
    }
    res = await client.post("/api/v1/urls/", json=create_payload, headers=headers)
    assert res.status_code == 201
    short_code = res.json()["data"]["short_code"]

    # First access consumes the link -> 302
    first_res = await client.get(f"/{short_code}", follow_redirects=False)
    assert first_res.status_code == 302

    # Second access must return 410 Gone!
    second_res = await client.get(f"/{short_code}", follow_redirects=False)
    assert second_res.status_code == 410
    assert "already been used" in second_res.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_url_update_and_soft_deletion(client: AsyncClient):
    headers = await get_auth_headers(client, "editor_user")

    # Create link
    create_res = await client.post(
        "/api/v1/urls/",
        json={"original_url": "https://initial-site.com"},
        headers=headers,
    )
    short_code = create_res.json()["data"]["short_code"]

    # Update destination
    update_res = await client.put(
        f"/api/v1/urls/{short_code}",
        json={"original_url": "https://updated-destination.com", "title": "Updated Site"},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["data"]["original_url"] == "https://updated-destination.com"

    # Verify redirect reflects new destination
    redir = await client.get(f"/{short_code}", follow_redirects=False)
    assert redir.status_code == 302
    assert redir.headers["location"] == "https://updated-destination.com"

    # Soft delete
    del_res = await client.delete(f"/api/v1/urls/{short_code}", headers=headers)
    assert del_res.status_code == 200

    # Subsequent redirect returns 404
    after_del = await client.get(f"/{short_code}", follow_redirects=False)
    assert after_del.status_code == 404
