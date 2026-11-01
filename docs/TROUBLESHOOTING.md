# Production Troubleshooting & Incident Playbooks — URL Shortener & Distributed Analytics Platform

## Incident Playbook 1: High Redirection Latency ($p99 > 30\text{ms}$)

### Symptoms
- Prometheus alert `HighRedirectLatency` fires.
- Grafana dashboard shows redirection latency percentiles degrading from $2\text{ms}$ to $>50\text{ms}$.

### Diagnostic Steps
1. **Check Redis Cache Hit Ratio:**
   Look at the Grafana Cache Hit Ratio panel. If the hit ratio dropped below $80\%$, the platform is suffering excessive database fallbacks.
2. **Inspect Redis Latency:**
   Execute `redis-cli --latency` or check Redis slowlog (`SLOWLOG GET 10`).
3. **Verify Database Connection Pool Saturation:**
   Check PostgreSQL active connections:
   ```sql
   SELECT count(*), state FROM pg_stat_activity GROUP BY state;
   ```
   If connections in state `active` match `DB_POOL_SIZE + DB_MAX_OVERFLOW`, pool exhaustion is causing queuing delays.

### Remediation
- If Redis is overloaded or evicted early, increase Redis `maxmemory`.
- Pre-warm the cache for top viral URLs.
- Scale API replicas horizontally via HPA (`kubectl scale deployment url-shortener-api --replicas=8`).

---

## Incident Playbook 2: Kafka Producer Bounded Queue Dropping Events

### Symptoms
- Prometheus alert `KafkaClickEventsDropped` fires (`rate(events_dropped_total) > 0`).
- Log lines emit `WARNING: Kafka click event bounded queue is saturated. Dropping event.`

### Diagnostic Steps
1. **Verify Kafka Broker Connectivity:**
   ```bash
   nc -zv $KAFKA_BOOTSTRAP_SERVERS
   ```
2. **Check Background Producer Worker Status:**
   Inspect API logs for unhandled connection errors from `aiokafka.AIOKafkaProducer`.
3. **Inspect Broker Disk & Network Saturation:**
   Ensure Kafka brokers have not reached disk capacity or network throttling limits.

### Remediation
- If the broker is restarting, the bounded queue (`maxsize=5000`) protects the API memory. No intervention is required for short disruptions; events will resume publishing as soon as the broker recovers.
- If the broker is degraded long-term, scale Kafka broker partitions and increase worker concurrency.

---

## Incident Playbook 3: Consumer Lag Spiking on `url-clicks`

### Symptoms
- Real-time click analytics dashboard shows delayed numbers.
- Kafka consumer group lag metric increases continuously.

### Diagnostic Steps
1. **Check Consumer Group Lag:**
   ```bash
   kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group url-shortener-analytics-workers
   ```
2. **Check Worker CPU and DB Write Throughput:**
   Examine if the database batch insert transaction (`INSERT INTO click_events ...`) is bottlenecked on disk I/O.

### Remediation
- Increase consumer batch size in `app/events/consumer.py` (`batch_size=500`).
- Scale consumer worker deployment replicas up to the number of topic partitions (`kubectl scale deployment url-shortener-worker --replicas=3`). Note: Adding more workers than partitions provides no benefit.

---

## Incident Playbook 4: Redis Complete Outage (Total Cache Failure)

### Symptoms
- Redis nodes are unreachable or terminated.
- Application logs emit `Redis connection error: ... Defaulting to direct database fallback.`

### System Behavior
- **Automatic Fallback:** The platform’s [CacheService](file:///e:/url_shortner/app/cache/cache_service.py) catches all `RedisError` exceptions and defaults gracefully to PostgreSQL reads.
- **Redirection remains 100% available**, albeit with higher latency (~15ms p95).

### Recovery Runbook
1. Restore or restart Redis instances.
2. The [RedisClient](file:///e:/url_shortner/app/cache/redis_client.py) connection pool will automatically re-establish connections without requiring application pod restarts.
3. Once online, cache-aside lookups automatically resume populating Redis keys.
