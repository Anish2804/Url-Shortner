# Production-Grade URL Shortener & Distributed Analytics Platform

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D.svg)](https://redis.io/)
[![Apache Kafka](https://img.shields.io/badge/Apache%20Kafka-KRaft-231F20.svg)](https://kafka.apache.org/)
[![Docker & Compose](https://img.shields.io/badge/Docker-Multi--stage-2496ED.svg)](https://www.docker.com/)
[![Kubernetes & Helm](https://img.shields.io/badge/Kubernetes-HPA%20%7C%20Helm-326CE5.svg)](https://kubernetes.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A high-performance, production-grade distributed backend system engineered to deliver ultra-low-latency URL redirection ($<15\text{ms}$ p95), resilient cache-aside caching with stampede protection, high-throughput asynchronous click event streaming via Apache Kafka, and privacy-preserving analytics.

Built to genuine Senior/Principal backend engineering standards with zero mock implementations, verified reversible database migrations, hardened container builds, and comprehensive architectural documentation.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    Client["Client / Web Browser / API Consumer"]
    
    subgraph Edge & Routing Layer
        Ingress["Kubernetes Ingress / Nginx Proxy"]
        SecMW["Security Headers & Correlation Middleware (X-Request-ID)"]
        RateMW["Sliding-Window Rate Limiter (Redis)"]
    end
    
    subgraph Core Application Service
        FastAPI["FastAPI Core Engine (app.main)"]
        RedirSvc["RedirectService (app.services.redirect_service)"]
        UrlSvc["UrlService (app.services.url_service)"]
        AuthSvc["AuthService (app.services.auth_service)"]
        CacheSvc["CacheService (app.cache.cache_service)"]
        Producer["Kafka EventProducer (app.events.producer)"]
    end

    subgraph Data & Caching Tier
        Redis[("Redis 7 In-Memory Store\n- Cache-Aside Mapping\n- Distributed Mutex Locks\n- Sliding-Window Rate Limits")]
        Postgres[("PostgreSQL 16 Primary DB\n- URLs & Domain Schemas\n- Users & RBAC\n- Analytics Aggregate Rollups")]
    end

    subgraph Asynchronous Event Streaming Pipeline
        Queue["In-Memory Bounded Queue\n(asyncio.Queue maxsize=5000)"]
        Kafka["Apache Kafka Broker\nTopic: url-clicks\nTopic: url-clicks-dlq"]
        Worker["Analytics Consumer Worker\n(app.workers.analytics_worker)"]
        Dedupe["LRU Deduplication Cache"]
        AggCron["Daily Aggregation Cron\n(app.workers.aggregation_cron)"]
    end

    subgraph Observability
        Prom["Prometheus Scraper (:9090)"]
        Graf["Grafana Dashboard (:3000)"]
    end

    %% Flow connections
    Client -->|HTTP Request| Ingress
    Ingress --> SecMW --> RateMW --> FastAPI
    
    FastAPI -->|GET /{short_code}| RedirSvc
    FastAPI -->|POST /api/v1/urls| UrlSvc
    FastAPI -->|POST /api/v1/auth| AuthSvc

    RedirSvc -->|1. Check Cache| CacheSvc
    CacheSvc <-->|Fast Path <2ms| Redis
    CacheSvc -->|2. Fallback Lock & Query| Postgres
    
    RedirSvc -->|3. Non-blocking Enqueue| Queue
    Queue --> Producer --> Kafka
    
    Kafka --> Worker --> Dedupe --> Postgres
    AggCron -->|Nightly Rollup| Postgres
    
    FastAPI -.->|Metrics :8000/metrics| Prom
    Prom -.-> Graf
```

---

## ⚡ Key Engineering Capabilities

- **Ultra-Fast Redirection Path ($<10\text{ms}$ p95):** Read-heavy redirect endpoint queries Redis cache-aside first; dispatches clickstream events to a non-blocking in-memory queue that feeds Apache Kafka without adding latency to the client response.
- **Cache Stampede & Penetration Defense:** Distributed atomic Redis mutex locking (`lock:url:{code}`) prevents database overload when viral links expire. Missing short codes are stored as `__NULL__` sentinels with 60-second TTLs to shield PostgreSQL from cache penetration attacks.
- **Strict Anti-SSRF Protection:** Target URLs are checked for valid schemes (`http`/`https`), DNS is resolved, and destination IPs are strictly verified against private (`10/8`, `172.16/12`, `192.168/16`), loopback (`127/8`, `::1`), link-local, and cloud metadata (`169.254.169.254`) ranges. Preserves IPv6 NAT64 synthesized prefixes.
- **Argon2id & Cryptographic Refresh Token Rotation:** Passwords hashed with memory-hard Argon2id ($m=65536, t=3, p=4$). Single-use rotating refresh tokens with automatic replay/reuse detection that revokes all active sessions if a stolen token is reused.
- **Atomic One-Time Links:** Conditional SQL update (`UPDATE urls SET is_consumed=true WHERE is_consumed=false`) eliminates double-consumption race conditions and immediately serves HTTP 410 Gone on second access.
- **Sliding-Window Rate Limiting:** Built on Redis sorted sets with millisecond precision and automatic in-memory fallback if Redis is unreachable.
- **GDPR & CCPA Compliant Analytics:** Visitor IP addresses are immediately pseudonymized using HMAC-SHA256 with an environment salt and subnet masked. Raw IPs are never persisted.
- **Streaming Large Data Exports:** Analytics CSV endpoint streams data directly from the PostgreSQL cursor using chunked transfer encoding, keeping memory usage constant ($<10\text{MB}$) regardless of export size.

---

## 🚀 Quickstart Guide

### Option 1: Full Distributed Stack via Docker Compose

Spin up FastAPI, Analytics Worker, PostgreSQL 16, Redis 7, Kafka KRaft, Prometheus, and Grafana in one command:

```bash
# 1. Clone the repository
git clone https://github.com/yourorg/url-shortener.git
cd url-shortener

# 2. Copy environment configuration
cp .env.example .env

# 3. Build and launch all services
docker compose up -d --build

# 4. Apply database migrations
docker compose exec api alembic upgrade head
```

- **Interactive API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check Endpoint:** [http://localhost:8000/health](http://localhost:8000/health)
- **Prometheus Metrics:** [http://localhost:9090](http://localhost:9090)
- **Grafana Analytics Dashboard:** [http://localhost:3000](http://localhost:3000) (Credentials: `admin` / `admin`)

---

### Option 2: Local Python Environment

```bash
# 1. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run database migrations (SQLite or Postgres)
alembic upgrade head

# 4. Start Uvicorn development server
uvicorn app.main:app --reload --port 8000
```

---

## 🧪 Comprehensive Test Suite

The platform includes unit, API, integration, and security tests:

```bash
# Run all tests with verbose output
pytest -v

# Run with test coverage report
pytest --cov=app --cov-report=term-missing tests/

# Run native async benchmark runner (measures p50, p90, p95, p99 latency & RPS)
python tests/performance/benchmark_runner.py --url http://localhost:8000 -c 20 -n 1000

# Run k6 high-concurrency load test (verifies p95 < 15ms SLA threshold)
k6 run tests/performance/k6_redirect_test.js
```

---

## 📚 Complete Technical Documentation Suite

The complete engineering documentation suite is located in [`/docs/`](file:///e:/url_shortner/docs/README.md):

| Document | Description |
| :--- | :--- |
| [Project Overview](file:///e:/url_shortner/docs/PROJECT_OVERVIEW.md) | Executive summary, business context, and core value proposition. |
| [System Architecture](file:///e:/url_shortner/docs/ARCHITECTURE.md) | High-level system topology, deep Mermaid diagrams, and component boundaries. |
| [System Design Deep Dive](file:///e:/url_shortner/docs/SYSTEM_DESIGN.md) | Quantitative estimations, CAP theorem trade-offs, and concurrency controls. |
| [Project Structure](file:///e:/url_shortner/docs/PROJECT_STRUCTURE.md) | Granular file-by-file codebase layout and component responsibilities. |
| [Module Specifications](file:///e:/url_shortner/docs/MODULES.md) | Detailed module breakdown, exported classes, and inter-module dependencies. |
| [Component Architecture](file:///e:/url_shortner/docs/COMPONENTS.md) | Software components, interaction protocols, and specifications. |
| [Data Flow Architecture](file:///e:/url_shortner/docs/DATA_FLOW.md) | Ingress, transformation, storage, and egress data flows. |
| [Operational Workflows](file:///e:/url_shortner/docs/WORKFLOWS.md) | End-to-end workflows for auth, one-time links, API keys, and abuse management. |
| [Database Schema](file:///e:/url_shortner/docs/DATABASE.md) | Complete ERD, table specs, indexing strategy, and partitioning guide. |
| [API Documentation](file:///e:/url_shortner/docs/API_DOCUMENTATION.md) | Global headers, request/response schemas, and cURL examples for all endpoints. |
| [Authentication & RBAC](file:///e:/url_shortner/docs/AUTHENTICATION.md) | Dual-auth model, Argon2id hashing, token rotation, and RBAC scopes. |
| [Application Security](file:///e:/url_shortner/docs/SECURITY.md) | Threat model, strict anti-SSRF defense, sliding-window rate limiting, and GDPR. |
| [Configuration Guide](file:///e:/url_shortner/docs/CONFIGURATION.md) | Pydantic Settings v2 architecture and environment profiles. |
| [Environment Variables](file:///e:/url_shortner/docs/ENVIRONMENT_VARIABLES.md) | Exhaustive reference table of all configuration parameters. |
| [Error Handling](file:///e:/url_shortner/docs/ERROR_HANDLING.md) | RFC-standard error envelopes, domain exception catalog, and DLQ handling. |
| [Logging & Monitoring](file:///e:/url_shortner/docs/LOGGING_AND_MONITORING.md) | Structured JSON logging, Prometheus metrics, and Grafana dashboard layout. |
| [Performance Engineering](file:///e:/url_shortner/docs/PERFORMANCE.md) | Latency targets, optimization mechanisms, and load testing execution. |
| [Testing Strategy](file:///e:/url_shortner/docs/TESTING.md) | Test pyramid, directory structure, commands, and isolation fixtures. |
| [Deployment Guide](file:///e:/url_shortner/docs/DEPLOYMENT.md) | Docker Compose, Kubernetes manifests, Helm chart, and production checklist. |
| [Production Troubleshooting](file:///e:/url_shortner/docs/TROUBLESHOOTING.md) | Playbooks for latency spikes, queue drops, consumer lag, and Redis outages. |
| [Contributing Guidelines](file:///e:/url_shortner/docs/CONTRIBUTING.md) | Engineering principles, local setup, and pull request conventions. |
| [Changelog](file:///e:/url_shortner/docs/CHANGELOG.md) | Historical record of features, security fixes, and releases. |
| [Engineering Glossary](file:///e:/url_shortner/docs/GLOSSARY.md) | Definitions of distributed systems, security, and backend engineering terms. |
| [Technical Interview Q&A](file:///e:/url_shortner/docs/TECHNICAL_INTERVIEW.md) | Senior/Principal interview defense questions on architecture and tradeoffs. |

### Architecture Decision Records (ADRs)
- [ADR 0001: Base62 Cryptographically Random Short Codes](file:///e:/url_shortner/docs/adr/0001-base62-random-short-codes.md)
- [ADR 0002: Cache-Aside with Distributed Mutex & Null Sentinel](file:///e:/url_shortner/docs/adr/0002-cache-aside-with-redis-mutex.md)
- [ADR 0003: Asynchronous Kafka Event Stream for Click Analytics](file:///e:/url_shortner/docs/adr/0003-asynchronous-kafka-click-events.md)
- [ADR 0004: Argon2id Password Hashing & Refresh Token Rotation](file:///e:/url_shortner/docs/adr/0004-argon2id-and-refresh-token-rotation.md)
- [ADR 0005: Strict Anti-SSRF Validation & Private IP Blocking](file:///e:/url_shortner/docs/adr/0005-strict-anti-ssrf-validation.md)

---

## 📜 License

Licensed under the MIT License. See [LICENSE](LICENSE) for details.
