# Operational Workflows — URL Shortener & Distributed Analytics Platform

## Workflow 1: Authentication & Refresh Token Rotation with Reuse Detection

```mermaid
sequenceDiagram
    autonumber
    actor User as Client Application
    participant API as Auth Endpoints
    participant Svc as AuthService
    participant DB as PostgreSQL DB

    User->>API: POST /api/v1/auth/login {email, password}
    API->>Svc: authenticate_user(email, password)
    Svc->>DB: Get user by email
    Svc->>Svc: Verify Argon2id password hash
    Svc->>Svc: Generate access_token (JWT, 15m)
    Svc->>Svc: Generate refresh_token (32-byte CSPRNG string)
    Svc->>DB: Store SHA-256(refresh_token) in refresh_tokens table
    Svc-->>User: {access_token, refresh_token, token_type: "bearer"}

    Note over User,DB: Token Refresh Workflow
    User->>API: POST /api/v1/auth/refresh {refresh_token}
    API->>Svc: rotate_refresh_token(refresh_token)
    Svc->>Svc: Compute SHA-256(refresh_token)
    Svc->>DB: Lookup refresh token record
    
    alt Valid Active Token
        Svc->>DB: Mark old token as revoked (is_revoked = true)
        Svc->>Svc: Generate new access_token & new refresh_token
        Svc->>DB: Store new token record
        Svc-->>User: {new access_token, new refresh_token}
    else Token Reuse Detected (Token already revoked)
        Note right of Svc: Security Alert: Refresh Token Hijacking Attempt
        Svc->>DB: Revoke ALL refresh tokens for this user_id
        Svc-->>User: 401 Unauthorized ("Token reuse detected. All sessions revoked.")
    end
```

---

## Workflow 2: One-Time Self-Destructing Link Lifecycle

1. **Creation:** User creates URL with `is_one_time = true`.
2. **Storage:** Record created in `urls` with `is_one_time=true, is_consumed=false, is_active=true`.
3. **First Request:**
   - Client requests `GET /{short_code}`.
   - [RedirectService](file:///e:/url_shortner/app/services/redirect_service.py) executes atomic SQL:
     ```sql
     UPDATE urls SET is_consumed=true, is_active=false WHERE id=:id AND is_one_time=true AND is_consumed=false;
     ```
   - Transaction succeeds (`rowcount == 1`).
   - Short code mapping deleted from Redis cache.
   - Client redirected via HTTP 302 to destination URL.
4. **Second Request:**
   - Subsequent client requests `GET /{short_code}`.
   - System checks database record and observes `is_consumed == true`.
   - Endpoint raises [LinkAlreadyConsumedException](file:///e:/url_shortner/app/core/exceptions.py), returning **HTTP 410 Gone** with error details.

---

## Workflow 3: Machine-to-Machine API Key Authentication

1. **Issuance:** Authenticated developer calls `POST /api/v1/api-keys` with scopes `["urls:read", "urls:write"]`.
2. **Generation:**
   - 32 random bytes generated, formatted as `url_live_{token}`.
   - Prefix `url_live_` + first 8 characters saved in `api_keys.prefix`.
   - Plaintext key is displayed **once** in the HTTP 201 response.
   - SHA-256 digest is persisted in `api_keys.hashed_key`.
3. **Invocation:** Client sends HTTP header `X-API-Key: url_live_abc123...`.
4. **Resolution:**
   - Middleware extracts prefix, locates candidates in database.
   - Compares SHA-256 hash using `secrets.compare_digest()`.
   - Verifies expiration date and required scopes before dispatching to business logic.

---

## Workflow 4: Abuse Reporting & Domain Takedown

1. **Report Submission:** Public user submits `POST /api/v1/admin/abuse` with `url_id` and violation reason (phishing, malware, spam).
2. **Review:** Administrator reviews pending reports via `GET /api/v1/admin/abuse/pending`.
3. **Takedown Action:**
   - Admin calls `POST /api/v1/admin/domains/block` specifying domain and reason.
   - Domain is inserted into `blocked_domains` table.
   - All existing active URLs pointing to this domain are set to `is_active = false`.
   - Redis cache keys for all affected short codes are purged immediately.
