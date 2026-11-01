"""Prometheus metrics registry and telemetry instruments."""

from prometheus_client import Counter, Gauge, Histogram

# HTTP Metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests received",
    ["method", "endpoint", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency distribution in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0),
)

active_requests_gauge = Gauge(
    "http_active_requests",
    "Number of currently processing HTTP requests",
)

# URL Shortener Metrics
redirects_total = Counter(
    "redirects_total",
    "Total URL redirects handled",
    ["status_code"],
)

# Cache Metrics
cache_hits_total = Counter(
    "cache_hits_total",
    "Total cache-aside hits",
    ["layer"],
)

cache_misses_total = Counter(
    "cache_misses_total",
    "Total cache-aside misses",
    ["layer"],
)

# Kafka Stream Metrics
kafka_events_published_total = Counter(
    "kafka_events_published_total",
    "Total click events published to Kafka stream",
)

kafka_events_dropped_total = Counter(
    "kafka_events_dropped_total",
    "Total click events dropped due to buffer backpressure",
)

kafka_events_consumed_total = Counter(
    "kafka_events_consumed_total",
    "Total click events processed by analytics workers",
)

kafka_dlq_events_total = Counter(
    "kafka_dlq_events_total",
    "Total unprocessable events routed to DLQ",
)
