# Testing Strategy & Verification Guide — URL Shortener & Distributed Analytics Platform

## 1. Test Architecture & Coverage Pyramid

The platform enforces a rigorous test-driven verification strategy across multiple testing layers:

```
                  / \
                 /   \      Performance Tests (k6, benchmark_runner.py)
                /     \     
               /-------\    Security Tests (IDOR, RBAC, SSRF, Headers)
              /         \   
             /-----------\  Integration Tests (Redis Resilience, Kafka DLQ, LRU)
            /             \ 
           /---------------\ API & Unit Tests (Pytest, Base62, Argon2id, JWT)
```

---

## 2. Test Suite Directory Structure

### Unit Tests (`tests/unit/`)
- [test_base62.py](file:///e:/url_shortner/tests/unit/test_base62.py): Verifies Base62 encoding math, 7-character length guarantees, and uniform distribution without collisions.
- [test_security.py](file:///e:/url_shortner/tests/unit/test_security.py): Validates Argon2id hashing, JWT access token issuance/expiration, refresh token SHA-256 generation, API key prefixes, and constant-time string comparison.
- [test_url_validation.py](file:///e:/url_shortner/tests/unit/test_url_validation.py): Verifies strict anti-SSRF filtering against private IP ranges (`10.0.0.0/8`, `127.0.0.1`, `169.254.169.254`, `::1`), dangerous schemes (`file:`, `ftp:`), and preservation of NAT64 prefixes.

### API & Workflow Tests (`tests/api/`)
- [test_auth_api.py](file:///e:/url_shortner/tests/api/test_auth_api.py): Tests user registration, login, token refresh, and brute-force lockout after 5 consecutive failures.
- [test_urls_and_redirect_api.py](file:///e:/url_shortner/tests/api/test_urls_and_redirect_api.py): Tests link creation, bulk ingestion, 302 redirection, password protection unlocking, atomic one-time consumption, and soft deletion.
- [test_analytics_and_api_keys.py](file:///e:/url_shortner/tests/api/test_analytics_and_api_keys.py): Tests machine-to-machine API key lifecycle, analytics aggregation summaries, and CSV streaming exports.

### Integration & Resilience Tests (`tests/integration/`)
- [test_redis_resilience.py](file:///e:/url_shortner/tests/integration/test_redis_resilience.py): Simulates complete Redis network outages and proves that [CacheService](file:///e:/url_shortner/app/cache/cache_service.py) automatically degrades gracefully to PostgreSQL without crashing or throwing 500 errors.
- [test_kafka_events.py](file:///e:/url_shortner/tests/integration/test_kafka_events.py): Verifies producer bounded-queue backpressure, event drop metrics, consumer LRU deduplication caching, and event schema versioning.

### Security Tests (`tests/security/`)
- [test_security_controls.py](file:///e:/url_shortner/tests/security/test_security_controls.py): Proves IDOR protection on URL modification/deletion, verifies admin RBAC enforcement, and asserts mandatory security headers (HSTS, CSP, X-Frame-Options).

---

## 3. Executing the Test Suite

All tests can be executed locally using the virtual environment:

```bash
# Run entire automated test suite (Unit, API, Security, Integration)
pytest -v

# Run with test coverage report
pytest --cov=app --cov-report=term-missing tests/

# Run only security tests
pytest tests/security/ -v

# Run only integration resilience tests
pytest tests/integration/ -v
```

---

## 4. Test Fixtures & Database Isolation

Implemented in [conftest.py](file:///e:/url_shortner/tests/conftest.py):
- **Isolated In-Memory Database:** Every test function receives an isolated in-memory SQLite database instance (`sqlite+aiosqlite:///:memory:`).
- **Per-Test Table Lifecycle:** Tables are cleanly created and dropped per test, eliminating cross-test state pollution.
- **Async HTTP Client Injection:** Tests use `httpx.AsyncClient` with `transport=ASGITransport(app=app)` to exercise the entire middleware and router stack in-memory without binding external TCP sockets.
