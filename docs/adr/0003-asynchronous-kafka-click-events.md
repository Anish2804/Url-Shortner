# ADR 0003: Asynchronous Kafka Event Stream for Click Analytics

## Status
Accepted

## Context
Capturing rich analytics (HMAC-salted IP hashes, User-Agent parsing, browser, OS, device, referrer, geo metadata) synchronously inside the HTTP redirect request cycle would add 20–80ms of database I/O, destroying redirect throughput and SLA targets ($<15\text{ms}$ p95).
Furthermore, database write bottlenecks during viral spikes could cause HTTP redirects to timeout or fail.

## Decision
We decoupled analytics ingestion from the redirection critical path using an event-driven architecture powered by Apache Kafka, implemented in:
- [EventProducer](file:///e:/url_shortner/app/events/producer.py)
- [AnalyticsConsumer](file:///e:/url_shortner/app/events/consumer.py)
- [ClickEventMessage](file:///e:/url_shortner/app/events/schema.py)

Key Architecture Rules:
1. **Zero-Latency In-Memory Buffer:** The HTTP redirect handler enqueues a `ClickEventMessage` into an asynchronous bounded queue (`asyncio.Queue(maxsize=5000)`) in $<0.1\text{ms}$ and immediately returns the HTTP 302 redirect to the client.
2. **Background Dispatch Worker:** A dedicated background task drains the bounded queue and publishes events to the Kafka topic `url-clicks`.
3. **Graceful Backpressure:** If Kafka is unavailable or down, the bounded queue prevents memory leaks. Once full, newest events increment `events_dropped_total` and log warnings while preserving HTTP redirect availability.
4. **Consumer Deduplication & Batching:** The consumer groups events into batches of 100 or 1.0 second windows, checks an in-memory LRU cache against duplicate `event_id` keys, and executes bulk database inserts with fallback to a Dead Letter Queue (`url-clicks-dlq`).

## Consequences
- **Positive:** HTTP 302 redirects execute at pure in-memory cache speeds without database write contention. Analytics database failures do not impact redirect availability.
- **Negative:** Eventual consistency for real-time analytics dashboards (1–3 second lag under normal conditions).
