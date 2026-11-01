# Database Schema & Data Architecture — URL Shortener & Distributed Analytics Platform

## 1. Entity-Relationship Diagram (ERD)

```mermaid
erDiagram
    USERS ||--o{ USER_ROLES : has
    ROLES ||--o{ USER_ROLES : assigned
    USERS ||--o{ REFRESH_TOKENS : owns
    USERS ||--o{ API_KEYS : owns
    USERS ||--o{ URLS : creates
    USERS ||--o{ CUSTOM_DOMAINS : registers
    USERS ||--o{ AUDIT_LOGS : triggers

    URLS ||--o{ CLICK_EVENTS : receives
    URLS ||--o{ DAILY_AGGREGATES : aggregates
    URLS ||--o{ HOURLY_AGGREGATES : aggregates
    URLS ||--o{ ABUSE_REPORTS : reported_in

    USERS {
        uuid id PK
        varchar email UK
        varchar hashed_password
        varchar full_name
        boolean is_active
        boolean is_verified
        integer failed_login_attempts
        timestamp locked_until
        timestamp created_at
        timestamp updated_at
    }

    ROLES {
        uuid id PK
        varchar name UK
        varchar description
        timestamp created_at
    }

    USER_ROLES {
        uuid user_id PK,FK
        uuid role_id PK,FK
    }

    REFRESH_TOKENS {
        uuid id PK
        uuid user_id FK
        varchar token_hash UK
        timestamp expires_at
        boolean is_revoked
        timestamp revoked_at
        timestamp created_at
    }

    API_KEYS {
        uuid id PK
        uuid user_id FK
        varchar name
        varchar prefix
        varchar hashed_key UK
        jsonb scopes
        timestamp expires_at
        timestamp last_used_at
        boolean is_active
        timestamp created_at
    }

    URLS {
        uuid id PK
        uuid user_id FK
        varchar original_url
        varchar short_code UK
        varchar custom_alias UK
        varchar title
        smallint redirect_type
        varchar password_hash
        timestamp expires_at
        boolean is_one_time
        boolean is_consumed
        boolean is_active
        boolean is_deleted
        bigint click_count
        timestamp created_at
        timestamp updated_at
    }

    CLICK_EVENTS {
        uuid id PK
        uuid url_id FK
        timestamp clicked_at
        varchar ip_hash
        varchar masked_ip
        varchar country_code
        varchar city
        varchar browser
        varchar os
        varchar device_type
        varchar referrer
        varchar user_agent
    }

    DAILY_AGGREGATES {
        uuid id PK
        uuid url_id FK
        date date
        bigint total_clicks
        bigint unique_clicks
        jsonb browsers
        jsonb platforms
        jsonb devices
        jsonb countries
        jsonb referrers
    }

    HOURLY_AGGREGATES {
        uuid id PK
        uuid url_id FK
        timestamp bucket_hour
        bigint total_clicks
        bigint unique_clicks
    }

    BLOCKED_DOMAINS {
        uuid id PK
        varchar domain UK
        varchar reason
        uuid blocked_by FK
        timestamp created_at
    }

    ABUSE_REPORTS {
        uuid id PK
        uuid url_id FK
        varchar reporter_email
        varchar reason
        varchar status
        text details
        timestamp created_at
    }

    CUSTOM_DOMAINS {
        uuid id PK
        uuid user_id FK
        varchar domain UK
        varchar status
        varchar verification_token
        timestamp created_at
    }

    AUDIT_LOGS {
        uuid id PK
        uuid user_id FK
        varchar action
        varchar resource_type
        varchar resource_id
        varchar ip_address
        varchar user_agent
        jsonb changes
        timestamp created_at
    }
```

---

## 2. Table Specifications & Indexing Strategy

### Table: `urls`
Primary registry of all shortened URLs and custom aliases.
- **Indexes:**
  - `ix_urls_short_code` (B-Tree, UNIQUE): Guaranteed $O(\log N)$ lookup during URL redirection.
  - `ix_urls_custom_alias` (B-Tree, UNIQUE): Resolves branded/custom aliases.
  - `ix_urls_user_id` (B-Tree): Filters URLs by owner in dashboard listings.
  - `ix_urls_is_active_expires_at`: Composite index for pruning expired links.

### Table: `click_events`
High-volume raw clickstream partition.
- **Indexes:**
  - `ix_click_events_url_id_clicked_at` (Composite B-Tree): Essential for timeseries range scans on individual URLs.
  - `ix_click_events_clicked_at`: Partition pruning key for archival and rollups.
- **Partitioning Strategy (Production PostgreSQL):**
  In high-scale deployments, `click_events` is partitioned by range on `clicked_at`:
  ```sql
  CREATE TABLE click_events (
      id UUID NOT NULL,
      url_id UUID NOT NULL,
      clicked_at TIMESTAMPTZ NOT NULL,
      ...
  ) PARTITION BY RANGE (clicked_at);

  CREATE TABLE click_events_2026_11 PARTITION OF click_events
      FOR VALUES FROM ('2026-11-01 00:00:00+00') TO ('2026-12-01 00:00:00+00');
  ```

### Table: `api_keys`
- **Prefix Lookup Indexing:** The `prefix` column (first 8 chars of key) has an index `ix_api_keys_prefix`. Key validation locates matching candidates by prefix first, avoiding full-table hash comparisons.

---

## 3. Database Migration Management

Database migrations are managed via Alembic in [alembic/versions/001_initial_schema.py](file:///e:/url_shortner/alembic/versions/001_initial_schema.py).

### Commands
```bash
# Upgrade to latest schema revision
alembic upgrade head

# Rollback one revision (verified reversible)
alembic downgrade -1

# Generate new autodetected migration
alembic revision --autogenerate -m "add_new_feature"
```
