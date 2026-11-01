# Project Structure — URL Shortener & Distributed Analytics Platform

A complete, granular breakdown of every directory and file in the codebase.

```
e:\url_shortner\
├── .github/
│   └── workflows/
│       ├── ci.yml                     # GitHub Actions CI (lint, mypy, pytest with coverage, docker build)
│       └── security-scan.yml          # Bandit, pip-audit, and TruffleHog automated security scans
├── alembic/
│   ├── versions/
│   │   └── 001_initial_schema.py      # Reversible database migration creating all 13 core tables & indexes
│   ├── env.py                         # Alembic migration engine context with async engine support
│   └── script.py.mako                 # Migration file template
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── admin.py               # Admin endpoints (abuse report reviews, domain blocking)
│   │       ├── analytics.py           # Analytics summary, time-series rollups, and CSV export
│   │       ├── api_keys.py            # API key generation, scope listing, and revocation
│   │       ├── auth.py                # User registration, login, logout, and token rotation
│   │       ├── domains.py             # Custom branded domain registration and verification
│   │       ├── redirect.py            # High-performance root /{short_code} redirection router
│   │       ├── router.py              # Central API v1 router mounting all sub-modules
│   │       ├── urls.py                # URL creation, bulk ingestion, update, QR code, and deletion
│   │       └── users.py               # User profile, password update, and account management
│   ├── cache/
│   │   ├── cache_service.py           # Cache-aside logic, distributed mutex locks, null-sentinel caching
│   │   ├── rate_limiter.py            # Sliding-window rate limiting engine with in-memory fallback
│   │   └── redis_client.py            # Async Redis connection pool manager and health checks
│   ├── core/
│   │   ├── config.py                  # Pydantic Settings v2 configuration management with validation
│   │   ├── exceptions.py              # Domain exception hierarchy mapped to HTTP RFC error statuses
│   │   ├── handlers.py                # Global exception handlers producing standardized JSON error envelopes
│   │   ├── logging.py                 # Structured JSON logger with sensitive data redaction & request context
│   │   └── security.py                # Argon2id password hashing, JWT creation/decoding, API key hashing
│   ├── database/
│   │   ├── base.py                    # SQLAlchemy Base, TimestampMixin, UUIDMixin, and dialect GUID
│   │   └── session.py                 # Async SQLAlchemy engine, session maker, and DB health checks
│   ├── events/
│   │   ├── consumer.py                # Kafka analytics consumer with LRU deduplication & DLQ routing
│   │   ├── producer.py                # Non-blocking bounded-queue Kafka click event producer
│   │   └── schema.py                  # Versioned ClickEventMessage Pydantic event schema
│   ├── middleware/
│   │   ├── correlation.py             # X-Request-ID propagation and logging context middleware
│   │   ├── metrics_mw.py              # Prometheus HTTP metrics collector & X-Process-Time-Ms header
│   │   ├── rate_limit_mw.py           # Sliding-window rate limit enforcement middleware
│   │   └── security_headers.py        # HSTS, CSP, X-Frame-Options, X-Content-Type-Options headers
│   ├── models/
│   │   ├── abuse.py                   # AbuseReport and BlockedDomain SQLAlchemy models
│   │   ├── analytics.py               # ClickEvent, DailyAggregate, HourlyAggregate models
│   │   ├── api_key.py                 # ApiKey model with hashed key and scope permissions
│   │   ├── audit.py                   # AuditLog model for administrative and security actions
│   │   ├── domain.py                  # CustomDomain model for branded domain verification
│   │   ├── url.py                     # Url model with short_code, custom_alias, expiration, and flags
│   │   ├── user.py                    # User, Role, UserRole, and RefreshToken models
│   │   └── __init__.py                # Package model exports for Alembic metadata discovery
│   ├── monitoring/
│   │   ├── prometheus.py              # Prometheus metric instruments (counters, histograms, gauges)
│   │   └── tracer.py                  # OpenTelemetry distributed tracing initialization
│   ├── repositories/
│   │   ├── abuse_repo.py              # Abuse report and blocked domain data access operations
│   │   ├── analytics_repo.py          # Click event querying, aggregation rollups, and CSV streaming
│   │   ├── api_key_repo.py            # API key storage, prefix lookup, and revocation
│   │   ├── base.py                    # Generic async CRUD repository base class
│   │   ├── domain_repo.py             # Custom domain data access and verification records
│   │   ├── url_repo.py                # URL lookup, Base62 uniqueness check, atomic consumption
│   │   └── user_repo.py               # User authentication, lockout management, refresh token queries
│   ├── schemas/
│   │   └── common.py                  # Pydantic schemas for requests, responses, pagination, analytics
│   ├── services/
│   │   ├── abuse_service.py           # Abuse reporting workflow and domain blacklist management
│   │   ├── admin_service.py           # System administration, user role management, system metrics
│   │   ├── analytics_service.py       # Click aggregation, device/geo metrics, and CSV reporting
│   │   ├── api_key_service.py         # M2M API key generation, validation, and scope verification
│   │   ├── auth_service.py            # Registration, login, lockout, token rotation, reuse detection
│   │   ├── domain_service.py          # Branded custom domain registration and DNS verification
│   │   ├── redirect_service.py        # High-speed cache-aside redirect and Kafka dispatch
│   │   └── url_service.py             # Base62 generation, anti-SSRF validation, QR codes, bulk ingestion
│   ├── workers/
│   │   ├── aggregation_cron.py        # Nightly cron script aggregating raw click events into daily rollups
│   │   └── analytics_worker.py        # Background Kafka analytics stream consumer daemon
│   └── main.py                        # FastAPI application instantiation, lifespan, CORS, and routing
├── docs/
│   ├── adr/                           # Architecture Decision Records (0001 - 0005)
│   └── *.md                           # Complete 24-document engineering specification suite
├── infra/
│   ├── docker/
│   │   ├── Dockerfile                 # Multi-stage non-root Python runtime for API
│   │   ├── Dockerfile.worker          # Container build for Kafka analytics stream consumer
│   │   └── docker-compose.yml         # Container composition mirror for infra directory
│   ├── helm/
│   │   └── url-shortener/             # Production Helm chart (Chart.yaml, values.yaml, templates/)
│   ├── kubernetes/                    # Kubernetes manifests (Deployment, Service, HPA, Ingress, Secrets)
│   └── monitoring/
│       ├── grafana/                   # Grafana provisioning configs and analytics dashboard JSON
│       ├── prometheus.yml             # Prometheus scrape configuration
│       └── prometheus-alerts.yml      # Prometheus alerting rules for SLA and error spikes
├── tests/
│   ├── api/                           # Full-stack API tests (Auth, URLs, Redirect, Analytics, API Keys)
│   ├── integration/                   # Resilience tests (Redis offline fallback, Kafka backpressure, LRU)
│   ├── performance/                   # k6 load script and native Python async benchmark runner
│   ├── security/                      # IDOR prevention, RBAC enforcement, and security header tests
│   ├── unit/                          # Base62 math, Argon2id, JWT, and SSRF unit tests
│   └── conftest.py                    # Async test fixtures, test SQLite DB, and HTTP client injection
├── alembic.ini                        # Database migration configuration
├── docker-compose.yml                 # Root Docker Compose orchestrating all services
├── pytest.ini                         # Pytest configuration and asyncio loop settings
├── requirements.txt                   # Production and testing Python dependencies
└── README.md                          # Repository root documentation and quickstart
```
