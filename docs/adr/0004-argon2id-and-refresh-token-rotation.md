# ADR 0004: Argon2id Password Hashing & Cryptographic Refresh Token Rotation

## Status
Accepted

## Context
Standard password hashing (MD5, SHA-256, basic bcrypt) is vulnerable to modern GPU-based offline dictionary attacks.
Furthermore, static refresh tokens or non-rotating tokens create severe persistent hijacking risks if a client storage or network boundary is compromised.

## Decision
We implemented a defense-in-depth authentication model in:
- [hash_password](file:///e:/url_shortner/app/core/security.py) using **Argon2id** (OWASP-recommended algorithm).
- [AuthService](file:///e:/url_shortner/app/services/auth_service.py) with **Refresh Token Rotation & Reuse Detection**.

Key Mechanisms:
1. **Argon2id Parameters:** Configured with `time_cost=3`, `memory_cost=65536` (64 MB RAM), `parallelism=4`. This forces GPU/ASIC crackers to allocate substantial memory per guess, neutralizing brute-force hardware.
2. **Short-Lived Access Tokens:** Signed with HMAC-SHA256 JWT, valid for 15 minutes (`ACCESS_TOKEN_EXPIRE_MINUTES`).
3. **Rotating Cryptographic Refresh Tokens:** 32-byte cryptographically secure random tokens (`secrets.token_urlsafe(32)`).
4. **Hashed Storage:** Refresh tokens are never stored in plaintext. Only their SHA-256 digests are stored in the database (`RefreshToken.token_hash`), preventing token exposure in the event of database exfiltration.
5. **Automatic Reuse Detection & Revocation Cascade:** If an already-rotated or revoked refresh token is presented, the system detects a token reuse attack, immediately revokes all active refresh tokens for that user, and forces full re-authentication.

## Consequences
- **Positive:** Maximum credential protection against offline cracking. Hijacked refresh tokens cannot be silently used once the legitimate user triggers rotation.
- **Negative:** Increased CPU and memory utilization during password hashing (~100ms per registration/login), which also naturally rate-limits brute-force attempts.
