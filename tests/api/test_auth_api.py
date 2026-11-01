"""API integration tests for user authentication and authorization."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_registration_and_login_flow(client: AsyncClient):
    # 1. Register new user
    register_payload = {
        "email": "testuser@example.com",
        "username": "testuser",
        "password": "ValidPassword123!",
    }
    reg_res = await client.post("/api/v1/auth/register", json=register_payload)
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert reg_data["success"] is True
    assert reg_data["data"]["email"] == "testuser@example.com"
    assert reg_data["data"]["username"] == "testuser"

    # 2. Reject duplicate email
    dup_res = await client.post("/api/v1/auth/register", json=register_payload)
    assert dup_res.status_code == 409

    # 3. Successful login
    login_payload = {
        "username_or_email": "testuser",
        "password": "ValidPassword123!",
    }
    login_res = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    token_data = login_res.json()["data"]
    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]
    assert access_token and refresh_token

    # 4. Access protected profile endpoint
    headers = {"Authorization": f"Bearer {access_token}"}
    me_res = await client.get("/api/v1/users/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()["data"]
    assert me_data["username"] == "testuser"

    # 5. Rotate refresh token
    refresh_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 200
    new_tokens = refresh_res.json()["data"]
    new_access = new_tokens["access_token"]
    new_refresh = new_tokens["refresh_token"]
    assert new_access
    assert new_refresh != refresh_token

    # 6. Reuse detection: old refresh token must be rejected
    reuse_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert reuse_res.status_code == 401

    # 7. Logout with new refresh token
    logout_res = await client.post("/api/v1/auth/logout", json={"refresh_token": new_refresh})
    assert logout_res.status_code == 200


@pytest.mark.asyncio
async def test_auth_brute_force_lockout(client: AsyncClient):
    # Register user
    email = "lockout_victim@example.com"
    username = "lockout_victim"
    pwd = "VictimPassword123!"

    await client.post("/api/v1/auth/register", json={"email": email, "username": username, "password": pwd})

    # Fail login 5 times
    bad_login = {"username_or_email": username, "password": "WrongPassword!"}
    for _ in range(5):
        res = await client.post("/api/v1/auth/login", json=bad_login)
        assert res.status_code == 401

    # 6th attempt should be locked out with 403 Forbidden even if correct password is provided!
    locked_res = await client.post("/api/v1/auth/login", json={"username_or_email": username, "password": pwd})
    assert locked_res.status_code == 403
    assert "locked" in locked_res.json()["error"]["message"].lower()
