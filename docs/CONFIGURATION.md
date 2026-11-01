# Configuration Management Guide — URL Shortener & Distributed Analytics Platform

## Configuration Architecture

The platform centralizes all configuration parameters in [Settings](file:///e:/url_shortner/app/core/config.py) using **Pydantic Settings v2**. This architecture guarantees:
- **Strict Typing:** All numeric limits, URLs, booleans, and durations are validated at boot time.
- **Fail-Fast Initialization:** If required secrets (e.g. `DATABASE_URL` or `SECRET_KEY`) are missing or malformed, the application halts immediately during startup rather than failing at runtime.
- **Immutable State:** Settings are instantiated as a singleton via `@lru_cache` and cannot be modified dynamically across threads.

---

## Configuration Hierarchy & Precedence

1. **Host Environment Variables:** Explicit OS environment variables take highest priority (e.g., Kubernetes Pod environment variables).
2. **Local Environment Files:** Loaded from `.env` in the project root if present.
3. **Pydantic Default Values:** Safe local development defaults configured in `app/core/config.py`.

---

## Environment Profiles

| Environment | Mode | Database | Cache | Kafka | Security Posture |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Development** | `ENVIRONMENT=development` | Local PostgreSQL or Docker | Redis (localhost:6379) | Kafka or Disabled (falls back to bounded queue) | `DEBUG=True`, CORS permissive for localhost |
| **Testing** | `ENVIRONMENT=test` | In-memory SQLite (`sqlite+aiosqlite:///:memory:`) | In-memory mock or isolated Redis test DB | In-memory mock | `DEBUG=True`, fast test fixtures |
| **Production** | `ENVIRONMENT=production` | Managed Cloud PostgreSQL (RDS/Cloud SQL) | Managed Redis Cluster with TLS | Apache Kafka KRaft cluster | `DEBUG=False`, strict CORS, HSTS preload, Vault secrets |

---

## Production Secrets Management

In production deployments (Kubernetes, AWS ECS, or GCP Cloud Run):
- **Never commit `.env` to version control.** The `.gitignore` file enforces this rule.
- Mount sensitive keys (`SECRET_KEY`, `IP_HASH_SALT`, `DATABASE_URL`) from Kubernetes Secrets or HashiCorp Vault.
- Provide cryptographically generated keys with minimum 32 bytes of entropy:
  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```
