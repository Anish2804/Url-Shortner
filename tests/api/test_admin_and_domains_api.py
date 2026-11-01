"""API tests for Admin moderation, abuse handling, and custom domain management."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def create_user_and_token(
    client: AsyncClient,
    db_session: AsyncSession,
    username: str,
    is_superuser: bool = False,
) -> tuple[str, str]:
    email = f"{username}@example.com"
    pwd = "SecurePassword123!"
    reg_res = await client.post("/api/v1/auth/register", json={"email": email, "username": username, "password": pwd})
    assert reg_res.status_code == 201

    if is_superuser:
        stmt = select(User).where(User.username == username)
        u = (await db_session.execute(stmt)).scalar_one()
        u.is_superuser = True
        await db_session.commit()

    login_res = await client.post("/api/v1/auth/login", json={"username_or_email": username, "password": pwd})
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    return token, email


@pytest.mark.asyncio
async def test_custom_domain_lifecycle(client: AsyncClient, db_session: AsyncSession):
    """Test custom domain registration, listing, and DNS TXT verification."""
    token, _ = await create_user_and_token(client, db_session, "domain_user")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Add domain
    add_res = await client.post(
        "/api/v1/domains/",
        json={"domain": "go.mybrand.org"},
        headers=headers,
    )
    assert add_res.status_code == 201
    domain_data = add_res.json()["data"]
    assert domain_data["domain"] == "go.mybrand.org"
    assert domain_data["is_verified"] is False
    assert domain_data["verification_token"].startswith("lks-verify-")
    domain_id = domain_data["id"]

    # 2. Reject duplicate registration
    dup_res = await client.post(
        "/api/v1/domains/",
        json={"domain": "go.mybrand.org"},
        headers=headers,
    )
    assert dup_res.status_code == 409

    # 3. List user domains
    list_res = await client.get("/api/v1/domains/", headers=headers)
    assert list_res.status_code == 200
    domains = list_res.json()["data"]
    assert any(d["id"] == domain_id for d in domains)

    # 4. Verify domain
    verify_res = await client.post(f"/api/v1/domains/{domain_id}/verify", headers=headers)
    assert verify_res.status_code == 200
    verify_data = verify_res.json()["data"]
    assert verify_data["is_verified"] is True


@pytest.mark.asyncio
async def test_admin_abuse_reporting_and_domain_blocking(client: AsyncClient, db_session: AsyncSession):
    """Test submitting abuse reports, admin review, resolving, and blocking domains."""
    user_token, _ = await create_user_and_token(client, db_session, "regular_reporter")
    admin_token, _ = await create_user_and_token(client, db_session, "super_admin", is_superuser=True)

    user_headers = {"Authorization": f"Bearer {user_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Create a short URL to report
    url_res = await client.post(
        "/api/v1/urls/",
        json={"original_url": "https://suspicious-site.com/login"},
        headers=user_headers,
    )
    short_code = url_res.json()["data"]["short_code"]

    # 2. Submit abuse report (public/user)
    report_res = await client.post(
        "/api/v1/admin/abuse-reports",
        json={
            "short_code": short_code,
            "reporter_email": "whistleblower@example.com",
            "reason": "Phishing and credential harvesting page",
        },
    )
    assert report_res.status_code == 201
    report_data = report_res.json()["data"]
    assert report_data["short_code"] == short_code
    assert report_data["status"] == "PENDING"
    report_id = report_data["id"]

    # 3. Admin lists abuse reports
    list_res = await client.get("/api/v1/admin/abuse-reports", headers=admin_headers)
    assert list_res.status_code == 200
    reports = list_res.json()["data"]
    assert any(r["id"] == report_id for r in reports)

    # 4. Admin resolves abuse report
    resolve_res = await client.put(f"/api/v1/admin/abuse-reports/{report_id}/resolve", headers=admin_headers)
    assert resolve_res.status_code == 200

    # 5. Admin blocks malicious domain
    block_res = await client.post(
        "/api/v1/admin/blocked-domains",
        json={"domain": "malicious-phishing-network.org", "reason": "Known malware distribution C2"},
        headers=admin_headers,
    )
    assert block_res.status_code == 201
    assert block_res.json()["data"]["domain"] == "malicious-phishing-network.org"

    # 6. Verify URL shortener now rejects shortened links to blocked domain!
    blocked_url_res = await client.post(
        "/api/v1/urls/",
        json={"original_url": "https://malicious-phishing-network.org/exploit.exe"},
        headers=user_headers,
    )
    assert blocked_url_res.status_code == 400
    assert "blocked by security policy" in blocked_url_res.json()["error"]["message"].lower()
