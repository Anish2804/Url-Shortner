# API Reference & Specification — URL Shortener & Distributed Analytics Platform

## Global Headers & Protocols

| Header Name | Type | Description |
| :--- | :--- | :--- |
| `Authorization` | String | Bearer access token: `Bearer <jwt_token>` |
| `X-API-Key` | String | Machine-to-machine API key: `url_live_<32_byte_token>` |
| `X-Request-ID` | UUID | Distributed tracing correlation ID (automatically generated if omitted) |
| `X-Link-Password`| String | Password required to unlock password-protected short links |
| `X-Process-Time-Ms`| Float | Injected by API to communicate internal processing latency |

---

## 1. Authentication Endpoints

### Register User
`POST /api/v1/auth/register`
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "engineer@example.com",
    "password": "SecureMasterPassword2026!",
    "full_name": "Senior Backend Engineer"
  }'
```
**Response (201 Created):**
```json
{
  "id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
  "email": "engineer@example.com",
  "full_name": "Senior Backend Engineer",
  "is_active": true,
  "created_at": "2026-11-01T12:00:00Z"
}
```

### Login & Obtain Tokens
`POST /api/v1/auth/login`
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "engineer@example.com",
    "password": "SecureMasterPassword2026!"
  }'
```
**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "refresh_token": "qW3x8P9zL1mK4vT7yU2rE5...",
  "token_type": "bearer",
  "expires_in": 900
}
```

### Rotate Refresh Token
`POST /api/v1/auth/refresh`
```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "qW3x8P9zL1mK4vT7yU2rE5..."
  }'
```

---

## 2. URL Management & Redirection

### Shorten a URL
`POST /api/v1/urls`
```bash
curl -X POST http://localhost:8000/api/v1/urls \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "original_url": "https://kubernetes.io/docs/concepts/services-networking/service/",
    "custom_alias": "k8s-services",
    "title": "Kubernetes Service Docs",
    "redirect_type": 302,
    "is_one_time": false
  }'
```
**Response (201 Created):**
```json
{
  "id": "e4eaaaf2-d142-11e1-b3e4-080027620cdd",
  "short_code": "k8s-services",
  "short_url": "http://localhost:8000/k8s-services",
  "original_url": "https://kubernetes.io/docs/concepts/services-networking/service/",
  "title": "Kubernetes Service Docs",
  "redirect_type": 302,
  "is_one_time": false,
  "click_count": 0,
  "created_at": "2026-11-01T12:00:00Z"
}
```

### URL Redirection
`GET /{short_code}`
```bash
curl -i http://localhost:8000/k8s-services
```
**Response (302 Found):**
```http
HTTP/1.1 302 Found
Location: https://kubernetes.io/docs/concepts/services-networking/service/
X-Process-Time-Ms: 1.25
X-Request-ID: 7d25e0a4-386d-4952-b8e7-1cb0d7ff3f09
```

### Generate QR Code
`GET /api/v1/urls/{short_code}/qr?box_size=10&border=4`
Returns a `PNG` binary image directly renderable in browsers or client interfaces.

---

## 3. Analytics Endpoints

### URL Analytics Summary
`GET /api/v1/analytics/{short_code}?period=30d`
```bash
curl -X GET http://localhost:8000/api/v1/analytics/k8s-services \
  -H "Authorization: Bearer <access_token>"
```
**Response (200 OK):**
```json
{
  "short_code": "k8s-services",
  "total_clicks": 14250,
  "unique_clicks": 9810,
  "browsers": { "Chrome": 8200, "Firefox": 3400, "Safari": 2650 },
  "platforms": { "Linux": 7100, "macOS": 4300, "Windows": 2850 },
  "devices": { "desktop": 11200, "mobile": 3050 },
  "countries": { "US": 6500, "DE": 2800, "IN": 2400 },
  "referrers": { "direct": 9500, "twitter.com": 3200, "github.com": 1550 }
}
```

### Stream CSV Analytics Export
`GET /api/v1/analytics/{short_code}/export`
Streams raw CSV clickstream data with headers `Timestamp,Country,City,Browser,OS,Device,Referrer`.

---

## 4. Machine-to-Machine API Keys

### Create API Key
`POST /api/v1/api-keys`
```bash
curl -X POST http://localhost:8000/api/v1/api-keys \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Microservice Ingest",
    "scopes": ["urls:read", "urls:write"]
  }'
```
**Response (201 Created):**
```json
{
  "id": "f5bca9e1-...",
  "name": "Production Microservice Ingest",
  "prefix": "url_live_a1b2c3d4",
  "key": "url_live_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "scopes": ["urls:read", "urls:write"],
  "expires_at": "2027-11-01T12:00:00Z"
}
```

---

## 5. Observability & Health

- `GET /health`: JSON service health status (`status: "healthy"`).
- `GET /metrics`: Standard Prometheus metrics export for scrapers.
