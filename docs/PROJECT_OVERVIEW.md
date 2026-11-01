# Project Overview — URL Shortener & Distributed Analytics Platform

## Executive Summary

The **URL Shortener & Distributed Analytics Platform** is a production-grade, distributed backend system engineered to deliver ultra-low-latency URL redirection ($<15\text{ms}$ p95), resilient cache-aside caching, high-throughput asynchronous event ingestion via Apache Kafka, and privacy-preserving clickstream analytics.

Designed to meet the stringent architectural and reliability standards of modern high-scale distributed systems, the platform handles high-concurrency redirection bursts, shields databases from cache stampedes via distributed mutex locking, and protects internal infrastructure through strict anti-SSRF defenses.

---

## Core Value Proposition

| Requirement | Conventional Implementation | Our Distributed Engineering Solution |
| :--- | :--- | :--- |
| **Short Code Generation** | Sequential auto-increment IDs or MD5 truncations. Scraped easily via IDOR enumeration. | 7-character CSPRNG Base62 codes ($3.52\times 10^{12}$ space) generated via [generate_random_base62](file:///e:/url_shortner/app/services/url_service.py). Zero predictability. |
| **Redirect Latency** | Synchronous database read & write on every redirect ($40\text{ms}-100\text{ms}$). | In-memory Redis cache-aside with sub-2ms lookups. Synchronous DB query only on miss. |
| **Cache Stampede** | Viral link cache expiry causes database lockups (thundering herd). | Distributed atomic Redis mutex locks in [CacheService](file:///e:/url_shortner/app/cache/cache_service.py); competing requests wait & read warmed cache. |
| **Cache Penetration** | Attackers flood non-existent codes to bypass Redis and degrade DB. | Null-sentinel (`__NULL__`) caching with 60-second TTL prevents DB bypass. |
| **Analytics Processing** | Blocking writes in request cycle destroy redirect throughput. | Non-blocking in-memory queue (`asyncio.Queue`) dispatches to Kafka broker via [EventProducer](file:///e:/url_shortner/app/events/producer.py) with zero redirect latency impact. |
| **Data Privacy** | Raw IP addresses stored, violating GDPR/CCPA regulations. | IP addresses salted and hashed via HMAC-SHA256 (`ip_hash`) and masked (`masked_ip`), ensuring irreversible pseudonymization. |
| **One-Time Links** | Vulnerable to race conditions allowing multiple redemptions. | Atomic conditional SQL update (`is_consumed=false` condition) with rowcount validation. |
| **SSRF Defense** | Naive string matching or absent URL validation. | Recursive DNS resolution verifying every IP against private, loopback, link-local, and multicast ranges in [validate_and_normalize_url](file:///e:/url_shortner/app/services/url_service.py). |

---

## Architectural Highlights

- **FastAPI Async Engine:** Python 3.12+ non-blocking asynchronous event loop powered by `asyncio` and `uvicorn`.
- **Relational Persistence:** PostgreSQL 16 managed with SQLAlchemy 2.0 async engine and Alembic revision control.
- **In-Memory Cache & Lock Manager:** Redis 7 for cache-aside reads, atomic mutex locks, sliding-window rate limiting, and session tracking.
- **Distributed Event Pipeline:** Apache Kafka KRaft cluster for decoupled stream ingestion, consumer batching, deduplication caching, and Dead Letter Queue (DLQ) routing.
- **Containerization & Orchestration:** Hardened multi-stage Dockerfiles (unprivileged non-root UID 10001), Docker Compose environment, Kubernetes manifests, and Helm chart.
- **Full Observability:** Prometheus metrics instrumentation, custom Grafana dashboards, OpenTelemetry distributed tracing, and structured JSON logs with correlation IDs.
