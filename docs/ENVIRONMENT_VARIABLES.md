# Environment Variables Reference — URL Shortener & Distributed Analytics Platform

An exhaustive reference of all configuration environment variables supported by the platform.

| Variable Name | Type | Default Value | Required in Prod | Description |
| :--- | :--- | :--- | :--- | :--- |
| `APP_NAME` | String | `"URL Shortener & Analytics Platform"` | No | Name of the service emitted in logs and OpenAPI docs. |
| `ENVIRONMENT` | String | `"development"` | Yes | Runtime environment: `development`, `test`, `staging`, `production`. |
| `DEBUG` | Boolean | `True` | Yes (Set to `False`) | Enables verbose error traces and development endpoints. |
| `APP_HOST` | String | `"0.0.0.0"` | No | Network interface binding. |
| `APP_PORT` | Integer | `8000` | No | HTTP listening port. |
| `BASE_URL` | URL | `"http://localhost:8000"` | Yes | Public root URL used to construct short link URLs. |
| `DATABASE_URL` | String | `"sqlite+aiosqlite:///./urlshortener.db"` | Yes | Async SQLAlchemy connection URI (e.g. `postgresql+asyncpg://user:pass@host:5432/db`). |
| `DB_POOL_SIZE` | Integer | `20` | No | Connection pool base size for database connections. |
| `DB_MAX_OVERFLOW` | Integer | `10` | No | Maximum extra connections allowed during traffic bursts. |
| `REDIS_URL` | String | `"redis://localhost:6379/0"` | Yes | Redis connection string with database index. |
| `CACHE_DEFAULT_TTL` | Integer | `86400` (24h) | No | Default expiration time in seconds for cached URL mappings. |
| `CACHE_NULL_TTL` | Integer | `60` (1m) | No | Expiration time for `__NULL__` sentinels (cache penetration defense). |
| `KAFKA_BOOTSTRAP_SERVERS` | String | `"localhost:9092"` | Yes | Comma-separated list of Kafka broker endpoints. |
| `KAFKA_TOPIC_CLICKS` | String | `"url-clicks"` | No | Kafka topic name for asynchronous click events. |
| `KAFKA_TOPIC_DLQ` | String | `"url-clicks-dlq"` | No | Dead Letter Queue topic for failed click event messages. |
| `SECRET_KEY` | String | *Required in Prod* | Yes | 32-byte cryptographic secret key used for signing JWT access tokens. |
| `ALGORITHM` | String | `"HS256"` | No | Cryptographic algorithm for JWT signature. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Integer | `15` | No | Validity duration of user access tokens. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Integer | `7` | No | Validity duration of rotating refresh tokens. |
| `IP_HASH_SALT` | String | *Required in Prod* | Yes | Salt string used for irreversible HMAC-SHA256 IP anonymization. |
| `RATE_LIMIT_GLOBAL_PER_MINUTE` | Integer | `120` | No | Default rate limit per minute per client. |
| `RATE_LIMIT_ANONYMOUS_PER_MINUTE`| Integer | `30` | No | Rate limit per minute for unauthenticated clients. |
| `RATE_LIMIT_AUTHENTICATED_PER_MINUTE` | Integer | `300` | No | Rate limit per minute for verified users and API keys. |
| `CORS_ORIGINS` | List[String]| `["*"]` | Yes | Permitted origins for Cross-Origin Resource Sharing. |
| `LOG_LEVEL` | String | `"INFO"` | No | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |
| `OTEL_EXPORTER_OTLP_ENDPOINT`| String | `""` | No | OpenTelemetry collector endpoint (e.g. `http://otel-collector:4317`). |
