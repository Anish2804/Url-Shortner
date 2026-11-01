# Changelog — URL Shortener & Distributed Analytics Platform

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-11-01

### Added
- **Core Redirection Engine:**
  - High-performance asynchronous FastAPI router with HTTP 301/302 redirects.
  - 7-character Base62 collision-resistant random code generator ($3.52\times 10^{12}$ combinations).
  - Password-protected links with constant-time verification.
  - Atomic one-time self-destructing links with immediate cache purge and HTTP 410 Gone status.
  - Soft-deletion support with `is_deleted` and `is_active` flags.
  - High-resolution QR code generator endpoint rendering binary PNG images.
  - Bulk URL creation endpoint with partial failure tolerance and detailed reporting.
- **Security & Cryptography:**
  - Strict anti-SSRF hostname validation resolving DNS and blocking private, loopback, and cloud metadata IPs.
  - Support for IPv6 NAT64/DNS64 synthesis addresses.
  - Argon2id password hashing with memory-hard parameters ($m=65536, t=3, p=4$).
  - Short-lived JWT access tokens paired with rotating refresh tokens and reuse detection.
  - Brute-force account lockout (5 failed attempts = 15m lockout).
  - Machine-to-machine API keys with prefix indexing and fine-grained RBAC scopes.
  - Security headers middleware (HSTS preload, CSP, X-Frame-Options, X-Content-Type-Options).
  - Anonymized click analytics via salted HMAC-SHA256 IP hashing and subnet masking.
- **Distributed Caching & Rate Limiting:**
  - Redis cache-aside implementation with sub-2ms read path.
  - Distributed atomic mutex locking for cache stampede (thundering herd) defense.
  - Null-sentinel (`__NULL__`) caching with 60-second TTL for cache penetration defense.
  - Sliding-window rate limiter using Redis sorted sets with in-memory local fallback.
  - Graceful degradation to PostgreSQL when Redis is unreachable.
- **Distributed Event Streaming & Analytics:**
  - Non-blocking bounded-queue Kafka producer (`asyncio.Queue(maxsize=5000)`) guaranteeing zero redirect latency penalty.
  - Standalone Kafka analytics consumer daemon with LRU deduplication cache.
  - Dead Letter Queue (`url-clicks-dlq`) for poison-pill message isolation.
  - Nightly rollup cron daemon compressing raw click events into `daily_aggregates`.
  - Comprehensive analytics summary endpoints and memory-constant chunked CSV streaming export.
- **Infrastructure & Observability:**
  - Multi-stage non-root Dockerfiles for API and Analytics Worker.
  - Complete Docker Compose environment with Postgres 16, Redis 7, Kafka KRaft, Prometheus, and Grafana.
  - Production Kubernetes manifests (Deployments, ClusterIP Services, HPA, Ingress with TLS).
  - Helm chart with templated ConfigMaps, Secrets, HPAs, and Ingress.
  - Prometheus metric instruments (`redirect_latency_seconds`, `cache_hits_total`, etc.).
  - Auto-provisioned Grafana analytics dashboard and SLA alerting rules.
  - OpenTelemetry distributed tracing hooks.
  - Native Python async benchmark runner and k6 load testing suite.
  - Complete 24-document technical documentation suite and Architecture Decision Records (ADRs).
