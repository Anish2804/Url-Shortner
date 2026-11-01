# Engineering Glossary — URL Shortener & Distributed Analytics Platform

An alphabetical index of distributed systems, security, and backend engineering terms used throughout this project.

### Base62 Encoding
A positional numeral system using 62 alphanumeric characters (`[0-9a-zA-Z]`). Used to generate compact, URL-safe short codes without special characters or percent-encoding.

### Cache-Aside (Lazy Loading)
A caching pattern where the application first checks the cache. On a hit, data is returned immediately. On a miss, the application queries the database, writes the result to the cache for future requests, and returns the result.

### Cache Penetration
An attack pattern where malicious clients deliberately request non-existent keys to bypass the cache and force expensive lookups in the primary database. Mitigated in this platform using **Null Sentinels**.

### Cache Stampede (Thundering Herd)
A phenomenon where the concurrent expiration of a popular cached key causes thousands of simultaneous requests to query the database at the same time, leading to connection exhaustion and database outages. Mitigated using **Distributed Mutex Locks**.

### Dead Letter Queue (DLQ)
A designated queue or topic (`url-clicks-dlq`) where messages that cannot be processed successfully (e.g. malformed payloads or schema violations) are routed for offline inspection without blocking the primary stream.

### Distributed Mutex (Mutual Exclusion)
A distributed synchronization primitive built on Redis (`SET ... NX EX`) that allows only one worker across a distributed cluster to execute a specific task (such as re-populating an expired cache entry) while competing workers wait.

### Horizontal Pod Autoscaler (HPA)
A Kubernetes controller that automatically scales the number of running pod replicas based on observed CPU utilization, memory consumption, or custom Prometheus metrics.

### Insecure Direct Object Reference (IDOR)
An access control vulnerability where an application uses user-supplied input to access database records directly without validating whether the requesting user owns the resource. Mitigated by verifying `resource.user_id == current_user.id`.

### KRaft (Kafka Raft Metadata Mode)
The modern consensus protocol that allows Apache Kafka to manage cluster metadata natively via a Raft quorum, eliminating the historical dependency on Apache ZooKeeper.

### Null Sentinel
A lightweight marker value (`"__NULL__"`) stored in the cache when a database lookup reports that a key does not exist. Prevents repeated database queries for missing resources.

### Server-Side Request Forgery (SSRF)
A security vulnerability where an attacker coerces a server application to make HTTP requests to an arbitrary domain or internal network resource. Mitigated by resolving hostnames and blocking private, loopback, and cloud metadata IP addresses.

### Sliding-Window Rate Limiting
A rate-limiting algorithm that calculates request rates across a continuous rolling time window rather than discrete fixed windows, eliminating the "burst-at-the-boundary" flaw of fixed-window algorithms.

### Token Reuse Detection
A security mechanism where refresh tokens are single-use. If a token that was already rotated is submitted a second time, the server infers that the token was compromised, revokes all active sessions for the user, and demands full re-authentication.
