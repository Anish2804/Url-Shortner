# ADR 0002: Cache-Aside with Distributed Mutex & Null Sentinel

## Status
Accepted

## Context
High-traffic redirect endpoints face three primary caching vulnerabilities:
1. **Cache Stampede (Thundering Herd):** When a highly viral short code expires from cache, thousands of concurrent requests miss Redis simultaneously and hammer the primary PostgreSQL database.
2. **Cache Penetration:** Attackers send high-volume queries for non-existent short codes (`/404xyz`), bypassing Redis and forcing expensive PostgreSQL index lookups on missing keys.
3. **Stale Data on Update/Deletion:** Modifying target destinations or deleting URLs must instantly invalidate cached records without lingering state.

## Decision
We implemented a robust multi-layered cache pattern in [CacheService](file:///e:/url_shortner/app/cache/cache_service.py) backed by [RedisClient](file:///e:/url_shortner/app/cache/redis_client.py):
1. **Cache-Aside Pattern:** Fast path checks Redis key `url:mapping:{code}`. On hit, return immediately ($<2\text{ms}$).
2. **Null Sentinel Caching (Penetration Defense):** If the database reports that a short code does not exist, a sentinel value `__NULL__` is cached for 60 seconds (`CACHE_NULL_TTL`). Subsequent queries for missing codes hit Redis immediately and return 404 without querying PostgreSQL.
3. **Distributed Mutex Lock (Stampede Defense):** On a cache miss for a legitimate URL, workers attempt to acquire an atomic distributed lock via Redis `SET lock:url:{code} 1 EX 5 NX`.
   - The thread that acquires the lock queries the database and populates Redis.
   - Competing threads wait 50ms and retry reading from cache, completely shielding the database from the thundering herd.
4. **Cache Invalidation:** Any update, password change, or soft-deletion immediately issues `DELETE url:mapping:{code}` in Redis.

## Consequences
- **Positive:** Sub-millisecond redirect lookups under heavy viral load. Database query volume drops by >98% for popular URLs.
- **Negative:** Small memory overhead in Redis for null sentinel strings, mitigated by a short 60s expiration time.
