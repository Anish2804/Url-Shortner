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


@pytest.mark.asyncio
async def test_password_reset_flow(client: AsyncClient):
    """Test full forgot-password and reset-password token lifecycle."""
    email = "reset_user@example.com"
    username = "reset_user"
    pwd = "OriginalPassword123!"

    # 1. Register user
    await client.post("/api/v1/auth/register", json={"email": email, "username": username, "password": pwd})

    # 2. Request reset token
    forgot_res = await client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert forgot_res.status_code == 200
    reset_token = forgot_res.json()["data"]["reset_token"]
    assert reset_token

    # 3. Non-existent email returns success to prevent user enumeration
    ghost_res = await client.post("/api/v1/auth/forgot-password", json={"email": "nonexistent@example.com"})
    assert ghost_res.status_code == 200
    assert "reset_token" not in ghost_res.json()["data"]

    # 4. Perform password reset
    new_pwd = "NewPassword123!"
    reset_res = await client.post("/api/v1/auth/reset-password", json={"token": reset_token, "new_password": new_pwd})
    assert reset_res.status_code == 200

    # 5. Old password rejected
    old_login = await client.post("/api/v1/auth/login", json={"username_or_email": username, "password": pwd})
    assert old_login.status_code == 401

    # 6. New password accepted
    new_login = await client.post("/api/v1/auth/login", json={"username_or_email": username, "password": new_pwd})
    assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_email_verification_flow(client: AsyncClient):
    """Test email verification token generation and confirmation."""
    email = "verify_user@example.com"
    username = "verify_user"
    pwd = "VerifyPassword123!"

    # 1. Register user
    await client.post("/api/v1/auth/register", json={"email": email, "username": username, "password": pwd})
    login_res = await client.post("/api/v1/auth/login", json={"username_or_email": username, "password": pwd})
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Initial state: unverified
    me_res = await client.get("/api/v1/users/me", headers=headers)
    assert me_res.json()["data"]["is_verified"] is False

    # 2. Request verification token
    req_res = await client.post("/api/v1/auth/request-verification", json={"email": email})
    assert req_res.status_code == 200
    verify_token = req_res.json()["data"]["verification_token"]

    # 3. Confirm email verification
    confirm_res = await client.post("/api/v1/auth/verify-email", json={"token": verify_token})
    assert confirm_res.status_code == 200

    # 4. Account is now verified
    verified_me = await client.get("/api/v1/users/me", headers=headers)
    assert verified_me.json()["data"]["is_verified"] is True
