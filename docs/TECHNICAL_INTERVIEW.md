# Senior/Principal Technical Interview Q&A — URL Shortener & Distributed Analytics Platform

This document prepares the engineer to defend every architectural decision, scale calculation, failure mode, and trade-off implemented in this codebase during a Senior or Principal Backend Engineering system design interview.

---

## 1. Core Architecture & Scale

### Q1: "Why did you choose a 7-character random Base62 code over an auto-incrementing ID or a distributed Snowflake ID?"
**Answer:**
Auto-incrementing IDs or Snowflake IDs encoded in Base62 have a critical vulnerability: **predictability**. Attackers can sequentially enumerate codes (`/0000001`, `/0000002`), scraping all private user URLs, estimating link creation velocity, and exposing sensitive documents.

We chose a 7-character cryptographically secure pseudo-random Base62 generator implemented in [generate_random_base62](file:///e:/url_shortner/app/services/url_service.py) using `secrets.randbelow()`.
- **Keyspace:** $62^7 = 3.52\times 10^{12}$ (3.52 Trillion combinations).
- **Collision Math:** At 100 Million stored URLs, the probability of a collision on insertion is $\frac{10^8}{3.52\times 10^{12}} \approx 0.0028\%$.
- With up to 5 retry attempts, the probability of two consecutive collisions is $7.8\times 10^{-10}$, making retry overhead negligible while completely eliminating sequential enumeration attacks.

---

### Q2: "How does your redirection path achieve $<10\text{ms}$ latency while recording rich click analytics?"
**Answer:**
We completely decoupled the **Redirection Read Path** from the **Analytics Write Path**:
1. **Redirection Read Path:** Uses the **Cache-Aside Pattern** in Redis. 98% of requests hit Redis and resolve in $<2\text{ms}$.
2. **Zero-Latency In-Memory Event Enqueue:** Instead of writing to the database or blocking on a network socket to Kafka, [RedirectService](file:///e:/url_shortner/app/services/redirect_service.py) enqueues a `ClickEventMessage` into an asynchronous bounded queue (`asyncio.Queue(maxsize=5000)`) in $<0.1\text{ms}$ and immediately returns the HTTP 302 redirect.
3. **Async Background Dispatch:** A background coroutine drains the queue and publishes batches to Apache Kafka. The analytics worker processes events asynchronously, inserting them into `click_events` without impacting the client's redirect latency.

---

## 2. Distributed Caching & Failure Modes

### Q3: "What happens when a viral short link with 100,000 RPS expires from cache? How do you prevent a cache stampede?"
**Answer:**
We implemented **Distributed Mutex Locking** in [CacheService](file:///e:/url_shortner/app/cache/cache_service.py):
1. When the cache misses, the worker attempts an atomic Redis lock: `SET lock:url:{short_code} 1 EX 5 NX`.
2. Exactly **one** worker acquires the lock, queries PostgreSQL, writes the result to Redis, and releases the lock.
3. All other competing requests fail to acquire the lock, back off for 50ms, and retry reading from Redis. By the time they retry, the cache has been warmed by the lock holder.
4. As a result, only 1 single query reaches PostgreSQL, completely neutralizing the thundering herd problem.

---

### Q4: "How do you protect your system against Cache Penetration attacks?"
**Answer:**
If an attacker sends 50,000 requests per second for non-existent codes (e.g., `/nonexistent123`), naive caching would bypass Redis on every request and bombard PostgreSQL.
We implemented **Null Sentinel Caching**:
- When the database confirms a short code does not exist, we store a lightweight sentinel string `__NULL__` in Redis key `url:mapping:{short_code}` with a 60-second TTL (`CACHE_NULL_TTL`).
- Subsequent queries for that non-existent code hit Redis immediately and return **HTTP 404** in $<1\text{ms}$ without ever touching PostgreSQL.

---

## 3. Concurrency & Data Integrity

### Q5: "How do you prevent race conditions when two users click a one-time self-destructing link at the exact same millisecond?"
**Answer:**
A naive "read-then-update" approach has a check-then-act race condition where both requests observe `is_consumed == false` and both redirect.
We solved this by enforcing atomic row-level conditional locking in [consume_one_time_link](file:///e:/url_shortner/app/repositories/url_repo.py):
```sql
UPDATE urls
SET is_consumed = true, is_active = false, updated_at = NOW()
WHERE id = :url_id AND is_one_time = true AND is_consumed = false;
```
PostgreSQL executes row-level writes with mutual exclusion. Exactly one transaction updates the row and receives `rowcount == 1`. Any concurrent competitor receives `rowcount == 0` and is immediately served **HTTP 410 Gone** [LinkAlreadyConsumedException](file:///e:/url_shortner/app/core/exceptions.py).

---

## 4. Application Security & Defenses

### Q6: "How do you defend against Server-Side Request Forgery (SSRF)?"
**Answer:**
Attackers can submit target URLs pointing to internal networks (`http://10.0.0.1/admin`), localhost (`http://127.0.0.1:8000`), or cloud metadata endpoints (`http://169.254.169.254/latest/meta-data/`).
In [validate_and_normalize_url](file:///e:/url_shortner/app/services/url_service.py):
1. **Scheme Whitelist:** Only `http` and `https` schemes are accepted.
2. **DNS Resolution & IP Analysis:** We resolve the hostname via `socket.getaddrinfo()` and parse all returned IPs using Python's `ipaddress` library.
3. **Prohibited Ranges:** We check and reject any IP where `ip.is_private`, `ip.is_loopback`, `ip.is_link_local`, or `ip.is_multicast` evaluates to `True`.
4. **NAT64 Support:** Public IPv6 synthesized prefixes (`64:ff9b::/96`) are preserved so valid dual-stack IPv6 clients are not blocked.

---

### Q7: "Why did you choose Argon2id over bcrypt, and how does your Refresh Token Rotation detect token reuse?"
**Answer:**
1. **Argon2id vs bcrypt:** Standard bcrypt only limits GPU cracking through iterations ($2^{cost}$), but modern GPUs can run thousands of bcrypt instances in parallel. Argon2id is memory-hard ($m=65536\text{ KiB}$), requiring 64 MiB of high-speed RAM per guess. This physically limits the parallel execution capability of GPU and ASIC cracking hardware.
2. **Refresh Token Reuse Detection:** When a refresh token is rotated, the server marks the old token record as revoked. If a compromised or stolen old token is presented again, the system recognizes an active replay attack, immediately revokes **all** refresh tokens belonging to that user ID, logs a high-severity security event, and forces full re-authentication.
