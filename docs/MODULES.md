# Module Specifications — URL Shortener & Distributed Analytics Platform

## 1. Core Module (`app.core`)

Responsible for application configuration, cryptography, error structures, structured logging, and application security.

### Key Classes & Functions
- [Settings](file:///e:/url_shortner/app/core/config.py): Pydantic Settings v2 model parsing environment variables with strict validation rules.
- [hash_password](file:///e:/url_shortner/app/core/security.py): Argon2id password hashing enforcing memory-hard parameters (`m=65536, t=3, p=4`).
- [verify_password](file:///e:/url_shortner/app/core/security.py): Constant-time password verification preventing timing attacks.
- [create_access_token](file:///e:/url_shortner/app/core/security.py): Issues short-lived JWT access tokens signed with HMAC-SHA256.
- [generate_api_key](file:///e:/url_shortner/app/core/security.py): Generates 32-byte cryptographic API keys (`url_live_...`) and computes SHA-256 storage hashes.
- [ensure_utc](file:///e:/url_shortner/app/core/security.py): Normalizes timezone awareness across SQLite (naive) and PostgreSQL (aware).
- [setup_logging](file:///e:/url_shortner/app/core/logging.py): Configures structured JSON logging with automated redaction of sensitive credentials and `X-Request-ID` correlation binding.
- [AppException](file:///e:/url_shortner/app/core/exceptions.py): Base class for domain exceptions mapped to HTTP RFC standard statuses.

---

## 2. Caching Tier (`app.cache`)

Provides high-speed in-memory data lookups, distributed mutual exclusion locks, and rate-limiting state.

### Key Classes & Functions
- [RedisClient](file:///e:/url_shortner/app/cache/redis_client.py): Async Redis connection pool manager tracking connection health and latency metrics.
- [CacheService](file:///e:/url_shortner/app/cache/cache_service.py):
  - `get_url_mapping(short_code)`: Reads cached URL metadata; returns `None` on cache miss or sentinel for missing keys.
  - `set_url_mapping(short_code, data)`: Caches active URL mapping for 24 hours.
  - `set_null_mapping(short_code)`: Caches `__NULL__` sentinel for 60 seconds (penetration defense).
  - `acquire_lock(key, ttl)` / `release_lock(key)`: Atomic Redis mutex using `SET ... NX EX`.
  - `invalidate_url(short_code)`: Purges cached mapping on updates or deletions.
- [SlidingWindowRateLimiter](file:///e:/url_shortner/app/cache/rate_limiter.py): Sliding-window rate limiter using Redis sorted sets (`ZADD`, `ZREMRANGEBYSCORE`, `ZCARD`) with fallback to local in-memory dictionaries.

---

## 3. Event Processing Engine (`app.events`)

Decoupled clickstream event publishing and consumption via Apache Kafka.

### Key Classes & Functions
- [ClickEventMessage](file:///e:/url_shortner/app/events/schema.py): Versioned Pydantic model (`schema_version="1.0"`) capturing click event attributes.
- [EventProducer](file:///e:/url_shortner/app/events/producer.py):
  - Maintains an asynchronous bounded queue (`asyncio.Queue(maxsize=5000)`).
  - `dispatch_click_event(...)`: Non-blocking enqueuing executed during HTTP redirection.
  - `_background_worker()`: Continuously drains queue and publishes JSON payloads to Kafka topic `url-clicks`.
- [AnalyticsConsumer](file:///e:/url_shortner/app/events/consumer.py):
  - Subscribes to `url-clicks` with consumer group `url-shortener-analytics-workers`.
  - Implements an LRU deduplication cache (`_seen_event_ids`).
  - Flushes batches to PostgreSQL; routes unparseable poison messages to Dead Letter Queue `url-clicks-dlq`.

---

## 4. Repositories (`app.repositories`)

Abstracts relational persistence using SQLAlchemy 2.0 async sessions.

- [BaseRepository](file:///e:/url_shortner/app/repositories/base.py): Generic CRUD repository providing `get`, `create`, `update`, `delete`, and pagination.
- [UrlRepository](file:///e:/url_shortner/app/repositories/url_repo.py): Manages URL retrieval, Base62 code lookups, custom aliases, and atomic one-time link consumption.
- [UserRepository](file:///e:/url_shortner/app/repositories/user_repo.py): Manages user accounts, failed login counters, account lockout timestamps, and refresh token records.
- [ApiKeyRepository](file:///e:/url_shortner/app/repositories/api_key_repo.py): Manages prefix-indexed API key lookups and revocations.
- [AnalyticsRepository](file:///e:/url_shortner/app/repositories/analytics_repo.py): Manages click event inserts, timeseries summaries, and CSV streaming queries.

---

## 5. Domain Services (`app.services`)

Encapsulates all business logic, validation, and domain orchestration.

- [UrlService](file:///e:/url_shortner/app/services/url_service.py): Base62 random short code generation, anti-SSRF hostname validation, QR code rendering, and bulk creation.
- [RedirectService](file:///e:/url_shortner/app/services/redirect_service.py): Cache-aside resolution, password challenge verification, one-time link consumption, and non-blocking Kafka dispatch.
- [AuthService](file:///e:/url_shortner/app/services/auth_service.py): User registration, Argon2id verification, account lockout, refresh token rotation, and reuse detection.
- [AnalyticsService](file:///e:/url_shortner/app/services/analytics_service.py): Detailed metrics aggregation (browsers, devices, OS, countries, referrers) and CSV exports.
- [ApiKeyService](file:///e:/url_shortner/app/services/api_key_service.py): API key issuance, scope verification, and revocation.
