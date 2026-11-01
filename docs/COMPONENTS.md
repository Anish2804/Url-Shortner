# Component Architecture — URL Shortener & Distributed Analytics Platform

## Component Breakdown & Interaction Matrix

```
+-----------------------------------------------------------------------------------+
|                                  PLATFORM CORE                                    |
|                                                                                   |
|  +--------------------+        +--------------------+        +-----------------+  |
|  |     FastAPI API    | -----> |    Redis Client    | -----> |  PostgreSQL DB  |  |
|  |  (Uvicorn :8000)   |        |    (Cluster :6379) |        |   (Port :5432)  |  |
|  +--------------------+        +--------------------+        +-----------------+  |
|            |                                                          ^           |
|            | (Non-blocking queue)                                     |           |
|            v                                                          | (Batch)   |
|  +--------------------+        +--------------------+        +-----------------+  |
|  |   Kafka Producer   | -----> |    Kafka Broker    | -----> | Analytics Worker|  |
|  |  (Bounded Queue)   |        |   (Topic :9092)    |        | (Consumer Group)|  |
|  +--------------------+        +--------------------+        +-----------------+  |
+-----------------------------------------------------------------------------------+
```

---

## Component Specifications

### 1. API Application Server
- **Implementation:** FastAPI application running on Uvicorn ASGI workers.
- **Port:** `8000` (HTTP).
- **Protocol:** HTTP/1.1 and HTTP/2 over TLS via Ingress.
- **Role:** Handles client requests, performs authentication, validates input schemas via Pydantic v2, coordinates cache lookups, and dispatches click events.
- **Health Check Endpoint:** `GET /health` returns JSON `{"status": "healthy", "timestamp": "...", "database": "connected", "redis": "connected"}` with HTTP 200.

### 2. Cache & Lock Manager
- **Implementation:** Redis 7 In-Memory Database.
- **Port:** `6379` (TCP).
- **Eviction Policy:** `allkeys-lru` with 256MB–8GB memory limits.
- **Key Namespaces:**
  - `url:mapping:{short_code}`: Cached JSON payload of target URL details (TTL: 86,400s).
  - `lock:url:{short_code}`: Distributed mutex lock for stampede defense (TTL: 5s).
  - `rate_limit:{identifier}:{window}`: Sorted set for sliding-window rate tracking.
  - `blacklist:token:{jti}`: Revoked JWT access token identifiers.

### 3. Distributed Event Broker
- **Implementation:** Apache Kafka (KRaft mode).
- **Port:** `9092` (Internal), `9093` (Controller).
- **Topics:**
  - `url-clicks`: Partitioned click event stream (default: 3 partitions, replication factor 1/3).
  - `url-clicks-dlq`: Dead Letter Queue for corrupted or malformed payloads.
- **Data Format:** JSON-encoded [ClickEventMessage](file:///e:/url_shortner/app/events/schema.py).

### 4. Background Analytics Consumer Worker
- **Implementation:** Python async daemon process in [analytics_worker.py](file:///e:/url_shortner/app/workers/analytics_worker.py).
- **Consumer Group:** `url-shortener-analytics-workers`.
- **Deduplication:** In-memory LRU tracking of recent `event_id` values (capacity: 10,000 entries).
- **Batch Processing:** Flushes batches of up to 100 events or 1.0s intervals via bulk SQL inserts into `click_events`.

### 5. Nightly Aggregation Cron Daemon
- **Implementation:** Scheduled batch job in [aggregation_cron.py](file:///e:/url_shortner/app/workers/aggregation_cron.py).
- **Trigger:** Configured via Kubernetes CronJob or internal scheduler (daily at 00:05 UTC).
- **Action:** Rolls up 24-hour raw click events into compressed `daily_aggregates` records and cleans up expired click events beyond the 90-day retention window.

### 6. Relational Persistence
- **Implementation:** PostgreSQL 16 Alpine.
- **Port:** `5432` (TCP).
- **Driver:** `asyncpg` with connection pooling (`pool_size=20, max_overflow=10`).
- **Isolation:** Read Committed default; row-level locking for one-time links and user account mutations.
