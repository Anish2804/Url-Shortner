# Data Flow Architecture — URL Shortener & Distributed Analytics Platform

## 1. URL Creation & Ingestion Data Flow

The flow of data when a client submits a long URL for shortening:

```mermaid
sequenceDiagram
    autonumber
    actor Client as User / API Client
    participant MW as Security & Rate Limit MW
    participant Handler as POST /api/v1/urls
    participant Svc as UrlService
    participant SSRF as SSRF & DNS Validator
    participant DB as PostgreSQL DB
    participant Cache as Redis Cache

    Client->>MW: POST /api/v1/urls (JSON Payload)
    MW->>MW: Check X-Request-ID, verify rate limit
    MW->>Handler: Forward Request
    Handler->>Svc: create_url(user_id, create_schema)
    
    rect rgb(240, 248, 255)
        note right of Svc: Validation & Normalization Phase
        Svc->>SSRF: validate_and_normalize_url(original_url)
        SSRF->>SSRF: Check scheme (http/https only)
        SSRF->>SSRF: Resolve DNS & check IP ranges (block 10/8, 127/8, 169.254/16, ::1)
        SSRF-->>Svc: Normalized URL string
        Svc->>DB: Check if domain is blocked in blocked_domains
    end

    rect rgb(255, 250, 240)
        note right of Svc: Code Generation Phase
        alt Custom Alias Provided
            Svc->>DB: Check custom_alias availability
        else Random Short Code
            Svc->>Svc: generate_random_base62(length=7)
            Svc->>DB: Check short_code uniqueness
        end
    end

    Svc->>DB: INSERT INTO urls (...) VALUES (...)
    DB-->>Svc: Persisted Url Entity
    Svc->>Cache: DEL url:mapping:{short_code} (Ensure no stale null sentinel)
    Svc-->>Handler: UrlResponse Schema
    Handler-->>Client: HTTP 201 Created {short_code, short_url, ...}
```

---

## 2. Click Redirection & Analytics Pipeline Data Flow

```mermaid
flowchart LR
    subgraph Client Journey
        Browser["User Browser"] -->|GET /abc1234| API["FastAPI Redirect"]
        API -->|HTTP 302 Location: target| Browser
    end

    subgraph Fast Path
        API <-->|1. Check Cache| Cache[("Redis Cache")]
        API -.->|2. Fallback Miss| DB[("PostgreSQL")]
    end

    subgraph Event Pipeline
        API -->|3. Non-blocking Enqueue| Queue["asyncio.Queue (5000 max)"]
        Queue -->|4. Async Drain| Producer["Kafka Producer"]
        Producer -->|5. Publish JSON| Kafka["Kafka Topic: url-clicks"]
        Kafka -->|6. Batch Stream| Consumer["Consumer Worker"]
        Consumer -->|7. Deduplicate & Insert| DBAnalytics[("PostgreSQL click_events")]
    end
```

---

## 3. Analytics Aggregation & Reporting Data Flow

Data flow for dashboard queries and high-volume CSV exports:

1. **User Request:** `GET /api/v1/analytics/{short_code}?period=30d`.
2. **Access Control:** [AnalyticsService](file:///e:/url_shortner/app/services/analytics_service.py) verifies the requesting user is the URL owner or an admin.
3. **Hybrid Aggregation Query:**
   - Historical days (older than today) query pre-computed rollups in `daily_aggregates` (sub-10ms response).
   - Current day queries recent records in `click_events` and merges with historical figures.
4. **CSV Streaming:** `GET /api/v1/analytics/{short_code}/export` streams data rows directly from the database cursor to the client using chunked transfer encoding, maintaining a constant memory footprint regardless of dataset size.
