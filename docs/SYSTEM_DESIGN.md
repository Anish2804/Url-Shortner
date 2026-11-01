# System Design Deep Dive — URL Shortener & Distributed Analytics Platform

## 1. Capacity Planning & Quantitative Estimations

### Scale Assumptions
- **Monthly New URLs Created:** 10 Million URLs / month ($\approx 3.86$ URLs / sec write traffic).
- **Monthly Redirections:** 1 Billion Clicks / month ($\approx 386$ redirects / sec average, $2,000 - 5,000$ RPS peak).
- **Read-to-Write Ratio:** $100 : 1$.
- **Data Retention:** 5 Years for URLs, 90 Days for raw click events, indefinite for daily rollups.

### Storage Estimations
1. **URL Metadata Record:**
   - `id` (UUID): 16 bytes
   - `short_code` (VARCHAR 16): ~16 bytes
   - `original_url` (VARCHAR 2048): ~100 bytes avg
   - `user_id` (UUID): 16 bytes
   - `created_at`, `updated_at`, `expires_at`: 24 bytes
   - `click_count`, flags, hash: ~64 bytes
   - *Total Per URL:* $\approx 500$ bytes (accounting for indexes & table overhead).
   - *Annual URL Storage Growth:*
     $$10\text{M} \times 12 \times 500\text{ bytes} \approx 60 \text{ GB / year}$$

2. **Click Analytics Record:**
   - Raw `click_events` row: ~300 bytes.
   - 1 Billion clicks / month $= 300\text{ GB / month}$.
   - 90-day retention partition window $= 900\text{ GB}$.
   - Aggregated rollups (`daily_aggregates`): 100K active URLs $\times 365$ days $\times 100\text{ bytes} \approx 3.65\text{ GB / year}$.

3. **Memory Sizing (80/20 Pareto Cache Rule):**
   - 20% of the active URLs generate 80% of total redirection traffic.
   - Active URLs per month $\approx 20\text{ Million}$.
   - 20% cache working set $= 4\text{ Million URLs}$.
   - Cached mapping JSON in Redis $= 250\text{ bytes}$.
   - *Redis RAM Sizing:*
     $$4\text{M} \times 250\text{ bytes} \approx 1.0\text{ GB RAM}$$
   - Provisioning a 4GB–8GB Redis cluster easily covers working set memory, rate-limit counters, and distributed mutex keys with substantial headroom.

---

## 2. CAP Theorem Trade-Offs

The platform intentionally applies different CAP choices to distinct operational domains:

```
                  Consistency (C)
                        ▲
                       / \
                      /   \
                     /  A  \  (Auth, API Keys, One-Time URLs)
                    /       \
   Availability (A) ◄───────► Partition Tolerance (P)
                  \         /
                   \   B   /  (High-Throughput URL Redirection & Analytics)
                    \     /
                     \   /
                      ▼
```

### Domain A: High Consistency (CP Mode)
- **Use Cases:** One-time self-destructing links, User Authentication, Password Verification, API Key Revocation.
- **Guarantee:** Strict linearizability. A one-time link cannot be consumed twice by concurrent requests. This is enforced via atomic database row-locking (`UPDATE ... WHERE is_consumed=false RETURNING id`). If network partitioning disrupts the primary database, mutations fail safely rather than permitting replay or double redemption.

### Domain B: High Availability & Eventual Consistency (AP Mode)
- **Use Cases:** URL Redirection and Click Analytics Ingestion.
- **Guarantee:** If Redis is completely offline, the system degrades gracefully by falling back to direct PostgreSQL reads without crashing. If Kafka is temporarily partitioned, the bounded queue buffers events in memory; if saturated, oldest non-critical analytics events drop while client 302 redirections continue uninterrupted at 100% availability.

---

## 3. High-Concurrency Race Condition Prevention

### The One-Time Link Double-Redemption Vulnerability
When a one-time link is targeted by concurrent HTTP requests arriving at the exact same millisecond:
- **Vulnerable Approach:** Read `is_consumed`, check if `false`, then issue `UPDATE ... SET is_consumed=true`. Both threads see `false` and both redirect.
- **Our Implementation in [consume_one_time_link](file:///e:/url_shortner/app/repositories/url_repo.py):**
  ```sql
  UPDATE urls
  SET is_consumed = true, is_active = false, updated_at = NOW()
  WHERE id = :url_id AND is_one_time = true AND is_consumed = false;
  ```
  PostgreSQL executes this row-level update with write lock isolation. Exactly one transaction receives `rowcount == 1`. All concurrent competitors receive `rowcount == 0` and are immediately served an HTTP 410 Gone [LinkAlreadyConsumedException](file:///e:/url_shortner/app/core/exceptions.py).

---

## 4. Cold-Start and Cache Warming Strategy

When a new Redis cluster node starts up or an existing cache is purged:
1. **Dynamic Pre-Warming:** A batch initialization worker queries the top 50,000 most frequently visited URLs from the previous 7 days of `daily_aggregates` and pre-loads `url:mapping:{code}` into Redis.
2. **Stampede Shielding:** Any un-warmed link accessed simultaneously by thousands of users is locked via the Redis mutex (`lock:url:{code}`), forcing 1 single DB query while the remaining 9,999 requests wait for the cache to warm.
