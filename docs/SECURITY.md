# Application Security Architecture — URL Shortener & Distributed Analytics Platform

## 1. Threat Model & Mitigation Matrix

| Threat Category | Potential Attack Vector | Platform Engineering Defense |
| :--- | :--- | :--- |
| **Server-Side Request Forgery (SSRF)** | Submitting target URLs pointing to `127.0.0.1`, AWS metadata `169.254.169.254`, or private LAN IPs `10.0.0.0/8`. | [validate_and_normalize_url](file:///e:/url_shortner/app/services/url_service.py) resolves DNS and evaluates every IP against private, loopback, link-local, and multicast ranges before accepting. |
| **Insecure Direct Object Reference (IDOR)** | Guessing or modifying short URLs or analytics owned by other users. | All mutation endpoints (`PUT`, `DELETE`) and analytics endpoints enforce strict `url.user_id == current_user.id` or `admin` role checks. |
| **Malicious Domain / Phishing Abuse** | Shortening links pointing to known malware or phishing hubs. | Pre-shortening check against `blocked_domains` repository; administrative abuse reporting and instantaneous domain blocking. |
| **Cache Stampede / Thundering Herd** | Concurrently requesting a newly-expired viral short code to crash the primary database. | Atomic Redis distributed mutex locking (`lock:url:{code}`) ensures exactly 1 DB query while concurrent requests wait and read cache. |
| **Cache Penetration Attack** | Flooding requests for non-existent codes to bypass Redis and overload PostgreSQL. | Missing short codes are cached as `__NULL__` sentinels with 60-second TTLs. |
| **Credential Stuffing & Brute Force** | Dictionary attacks against user login endpoints. | Exponential lockout (5 failed attempts = 15m lock) and Argon2id memory-hard hashing. |
| **Timing Attacks** | Measuring response latency variances to deduce valid API keys or password hashes. | Constant-time comparisons using Python's `secrets.compare_digest()`. |
| **Privacy Regulations (GDPR/CCPA)** | Storing raw visitor IP addresses in analytics logs. | Raw IPs are discarded; only HMAC-SHA256 salted hashes and masked subnets (`192.168.1.0/24`) are stored. |

---

## 2. Strict Anti-SSRF Defense Implementation

SSRF protection in [url_service.py](file:///e:/url_shortner/app/services/url_service.py) applies defense-in-depth:

```python
# 1. Scheme Whitelisting
if parsed.scheme.lower() not in ("http", "https"):
    raise SSRFBlockedException("Only http and https protocols are permitted.")

# 2. Hostname Validation
hostname = parsed.hostname
if not hostname or len(hostname) > 255:
    raise SSRFBlockedException("Invalid hostname format.")

# 3. DNS Resolution & IP Classification
addr_info = socket.getaddrinfo(hostname, None)
for entry in addr_info:
    ip_str = entry[4][0]
    ip_obj = ipaddress.ip_address(ip_str)
    
    # Block RFC 1918, RFC 3927, Loopback, Multicast
    if (
        ip_obj.is_private or
        ip_obj.is_loopback or
        ip_obj.is_link_local or
        ip_obj.is_multicast
    ):
        raise SSRFBlockedException(f"Destination IP {ip_str} resolves to a prohibited internal network.")
```

---

## 3. Distributed Sliding-Window Rate Limiting

The platform implements sliding-window rate limiting in [SlidingWindowRateLimiter](file:///e:/url_shortner/app/cache/rate_limiter.py) backed by Redis sorted sets.

### Tiers & Limits
- **Anonymous Clients (IP-based):** 30 requests / minute
- **Authenticated Users (User ID):** 120 requests / minute
- **API Keys (Key-based):** 300 requests / minute
- **Global Redirect Protection:** 10,000 requests / minute per client IP

### Sliding Window Algorithm
1. Redis Key: `rate_limit:{identifier}:{window_seconds}`
2. Remove expired entries: `ZREMRANGEBYSCORE key 0 (now - window)`
3. Add current timestamp: `ZADD key now now`
4. Count entries in window: `ZCARD key`
5. If count exceeds threshold, return **HTTP 429 Too Many Requests** with `Retry-After` header.

---

## 4. Privacy Preserving Analytics (GDPR & CCPA Compliance)

The platform guarantees that no Personally Identifiable Information (PII) is persisted:
1. **IP Anonymization:** Raw visitor IP is transformed via HMAC-SHA256 using an environment-isolated salt (`IP_HASH_SALT`):
   $$\text{ip\_hash} = \text{HMAC-SHA256}(\text{salt}, \text{client\_ip})$$
2. **Subnet Masking:** For IPv4, the last octet is zeroed (`198.51.100.42` $\rightarrow$ `198.51.100.0/24`). For IPv6, the host portion is zeroed (`2001:db8::1` $\rightarrow$ `2001:db8::/64`).
3. **User-Agent Decomposition:** The raw User-Agent header is parsed into synthetic categorical tokens (e.g. Browser: `Chrome`, OS: `Linux`, Device: `Desktop`) and then safely discarded.

---

## 5. Security Response Headers

All HTTP responses pass through [SecurityHeadersMiddleware](file:///e:/url_shortner/app/middleware/security_headers.py), which injects:
- `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
- `Content-Security-Policy: default-src 'self'; script-src 'self'; object-src 'none';`
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), camera=(), microphone=()`
