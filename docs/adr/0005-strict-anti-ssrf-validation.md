# ADR 0005: Strict Anti-SSRF Validation & Private IP Blocking

## Status
Accepted

## Context
URL shorteners accept arbitrary target URLs from untrusted clients. If the backend fetches or queries metadata (such as page titles or previews) or redirects internal automated agents to targets, attackers can provide URLs pointing to:
- Loopback addresses (`127.0.0.1`, `::1`) to access local services.
- RFC 1918 Private networks (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`).
- Cloud metadata services (`169.254.169.254` AWS/GCP/Azure instance metadata endpoints).
- Dangerous URI schemes (`file://`, `gopher://`, `dict://`, `javascript://`).

## Decision
We engineered comprehensive multi-layered SSRF validation in [validate_and_normalize_url](file:///e:/url_shortner/app/services/url_service.py):
1. **Scheme Whitelisting:** Only `http` and `https` schemes are permitted. Schemes like `file:`, `ftp:`, `javascript:` are rejected before processing.
2. **Domain Length & Format Limits:** URLs exceeding 2,048 characters are rejected. Hostnames must comply with RFC 1035 and cannot contain control characters.
3. **DNS Resolution & IP Classification:** The system resolves the hostname using `socket.getaddrinfo()` and evaluates every resolved IP address using Python's `ipaddress` library:
   ```python
   is_blocked = (
       ip_obj.is_private or
       ip_obj.is_loopback or
       ip_obj.is_link_local or
       ip_obj.is_multicast
   )
   ```
4. **NAT64/DNS64 Support:** Public IPv6 synthesized prefixes (`64:ff9b::/96`) are preserved so modern dual-stack IPv6 clients are not erroneously blocked.
5. **Pre-Shortening Abuse Check:** Target domains are checked against the [BlockedDomain](file:///e:/url_shortner/app/models/abuse.py) repository to reject known phishing or malware origins.

## Consequences
- **Positive:** Complete protection against Server-Side Request Forgery and internal network reconnaissance.
- **Negative:** Adds a DNS resolution step (~5–15ms) during URL shortening creation time. However, this is executed asynchronously on the creation path and does not touch the redirect path.
