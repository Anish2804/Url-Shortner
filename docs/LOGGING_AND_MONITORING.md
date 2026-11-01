# Logging, Monitoring & Observability — URL Shortener & Distributed Analytics Platform

## 1. Structured JSON Logging Architecture

The platform uses structured JSON logging in [setup_logging](file:///e:/url_shortner/app/core/logging.py) to enable seamless ingestion, filtering, and analysis by modern log aggregation systems (Datadog, ElasticSearch/Logstash, Loki, CloudWatch).

### JSON Log Output Format
```json
{
  "timestamp": "2026-11-01T12:00:00.123Z",
  "level": "INFO",
  "logger": "app.services.redirect_service",
  "message": "Redirect resolved successfully",
  "correlation_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "short_code": "k8s-services",
  "redirect_type": 302,
  "cache_hit": true,
  "elapsed_ms": 1.45
}
```

### Automated Credential Redaction
Logs automatically sanitize sensitive fields before serializing to stdout. Any dictionary key matching `password`, `token`, `secret`, `api_key`, `access_token`, `refresh_token`, or `authorization` has its value replaced with `"[REDACTED]"`.

### Distributed Request Correlation
The [CorrelationMiddleware](file:///e:/url_shortner/app/middleware/correlation.py) reads or generates a UUID4 `X-Request-ID` for every inbound HTTP request and stores it in an asynchronous Python `contextvars.ContextVar`. All subsequent log lines emitted anywhere across the request lifecycle automatically include `"correlation_id": "<uuid>"`.

---

## 2. Prometheus Metric Instruments

Exported on `GET /metrics` via [Prometheus Metrics](file:///e:/url_shortner/app/monitoring/prometheus.py):

| Metric Name | Type | Labels | Description |
| :--- | :--- | :--- | :--- |
| `http_requests_total` | Counter | `method`, `endpoint`, `status` | Total count of HTTP requests processed by endpoint. |
| `http_request_duration_seconds` | Histogram | `method`, `endpoint` | Duration of HTTP requests across latency buckets. |
| `redirects_total` | Counter | `status` (301, 302, 404, 410) | Total count of URL redirections handled. |
| `redirect_latency_seconds` | Histogram | *None* | High-resolution histogram dedicated to the redirection fast path. |
| `cache_hits_total` | Counter | *None* | Count of successful Redis cache-aside reads. |
| `cache_misses_total` | Counter | *None* | Count of cache misses forcing database fallbacks. |
| `events_published_total` | Counter | `topic` | Count of click events dispatched to Kafka. |
| `events_dropped_total` | Counter | `reason` | Count of click events dropped due to bounded queue backpressure. |
| `active_short_codes` | Gauge | *None* | Approximate count of active non-expired short URLs. |

---

## 3. Grafana Dashboard & Real-Time Alerts

A production-ready Grafana dashboard is provisioned in [url_shortener_analytics.json](file:///e:/url_shortner/infra/monitoring/grafana/dashboards/url_shortener_analytics.json):
- **Panel 1: Redirection Throughput (RPS):** Real-time rates of HTTP 301/302 redirects vs 404/410 errors.
- **Panel 2: Latency Percentiles (p50, p95, p99):** Visualizes the critical SLA threshold ($p99 < 30\text{ms}$).
- **Panel 3: Cache Hit Ratio Gauge:** Displays current percentage of requests served from Redis (target: $>90\%$).
- **Panel 4: Kafka Event Throughput & Queue Drops:** Real-time visibility into the asynchronous analytics pipeline.

### Active Prometheus Alerts (`prometheus-alerts.yml`):
- `HighRedirectLatency`: Fires if $p99 > 30\text{ms}$ for 2 consecutive minutes.
- `High5xxErrorRate`: Fires if 5xx errors exceed 1% of total API traffic.
- `KafkaClickEventsDropped`: Fires if events are dropped due to producer backpressure.
- `RedisCacheDropSpike`: Fires if cache miss ratio exceeds 35%.

---

## 4. OpenTelemetry Distributed Tracing

Distributed tracing is initialized in [init_tracer](file:///e:/url_shortner/app/monitoring/tracer.py).
- Injects standard W3C `traceparent` headers for distributed call tracking.
- Tracks span durations across database queries, Redis cache lookups, and Kafka event publishing.
- Supports streaming spans to any OTLP-compliant collector (Jaeger, Tempo, Honeycomb) via `OTEL_EXPORTER_OTLP_ENDPOINT`.
