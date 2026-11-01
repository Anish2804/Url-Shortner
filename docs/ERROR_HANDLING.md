# Error Handling Architecture — URL Shortener & Distributed Analytics Platform

## 1. RFC-Standard Error Response Envelope

All application exceptions, validation errors, and uncaught exceptions return a standardized JSON error envelope adhering to RFC 7807 Problem Details principles. This format ensures consistency across frontend clients, automated SDKs, and API consumers.

Implemented in [app/core/handlers.py](file:///e:/url_shortner/app/core/handlers.py):

```json
{
  "error": "LinkAlreadyConsumed",
  "message": "This one-time link has already been accessed and consumed.",
  "status_code": 410,
  "timestamp": "2026-11-01T12:00:00.123456Z",
  "path": "/secret-otp-link",
  "correlation_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "details": null
}
```

### Schema Attributes
- `error` (string): PascalCase machine-readable error classifier.
- `message` (string): Human-readable error description explaining why the request failed.
- `status_code` (integer): Corresponding HTTP status code.
- `timestamp` (string): ISO 8601 UTC timestamp of when the error occurred.
- `path` (string): Request URI path that generated the exception.
- `correlation_id` (string): The `X-Request-ID` linking the client response to backend structured logs.
- `details` (any): Optional contextual metadata (e.g., Pydantic validation field errors).

---

## 2. Domain Exception Catalog & Status Code Mapping

All application exceptions inherit from [AppException](file:///e:/url_shortner/app/core/exceptions.py):

| Domain Exception Class | HTTP Status | Error Classifier | Description |
| :--- | :--- | :--- | :--- |
| `ValidationException` | 400 | `ValidationError` | Malformed request parameters or JSON schema violation. |
| `SSRFBlockedException` | 400 | `SSRFBlocked` | Target URL resolves to a prohibited private, loopback, or cloud metadata IP address. |
| `InvalidShortCodeException` | 400 | `InvalidShortCode` | Short code contains characters outside Base62 or exceeds length limits. |
| `MalformedUrlException` | 400 | `MalformedUrl` | Target URL contains invalid syntax or unsupported protocol scheme. |
| `AuthenticationException` | 401 | `AuthenticationRequired` | Missing or invalid Bearer token or API key. |
| `InvalidCredentialsException` | 401 | `InvalidCredentials` | Incorrect email or password during login attempt. |
| `TokenExpiredException` | 401 | `TokenExpired` | JWT access token has passed its expiration timestamp. |
| `PasswordRequiredException` | 401 | `PasswordRequired` | Short link is password protected and requires valid `X-Link-Password` header. |
| `PermissionDeniedException` | 403 | `PermissionDenied` | Authenticated user lacks required role or API key scope. |
| `AccountLockedException` | 403 | `AccountLocked` | Account locked due to 5 consecutive failed login attempts. |
| `DomainBlockedException` | 403 | `DomainBlocked` | Target URL belongs to a domain blacklisted for abuse or malware. |
| `UrlNotFoundException` | 404 | `UrlNotFound` | Short code or custom alias does not exist. |
| `UserNotFoundException` | 404 | `UserNotFound` | User ID was not located in database. |
| `AliasAlreadyTakenException` | 409 | `AliasAlreadyTaken` | Custom alias requested is already claimed by another active link. |
| `UserAlreadyExistsException` | 409 | `UserAlreadyExists` | Email is already registered with an existing account. |
| `LinkExpiredException` | 410 | `LinkExpired` | Short link has passed its configured `expires_at` timestamp. |
| `LinkAlreadyConsumedException` | 410 | `LinkAlreadyConsumed` | One-time self-destructing link was already accessed and consumed. |
| `RateLimitExceededException` | 429 | `RateLimitExceeded` | Client exceeded sliding-window rate limit threshold. |
| `DatabaseException` | 500 | `DatabaseError` | Relational query failure or transaction deadlock. |

---

## 3. Background Worker Resilience & Dead Letter Queue (DLQ)

Failures occurring inside asynchronous background daemons (such as [AnalyticsConsumer](file:///e:/url_shortner/app/events/consumer.py)) cannot return HTTP status codes to clients. Instead:
1. **Poison Pill Isolation:** If an unparseable or schema-corrupted message arrives on `url-clicks`, parsing throws a handled exception.
2. **Dead Letter Queue Routing:** The consumer routes the corrupted payload directly to `url-clicks-dlq` along with error metadata.
3. **Offset Commit:** The partition offset advances so the consumer does not get stuck in an infinite retry crash loop.
4. **Alert Trigger:** The `KafkaClickEventsDropped` alert in Prometheus fires if DLQ write volume exceeds threshold.
