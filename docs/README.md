# Technical Documentation Suite — URL Shortener & Distributed Analytics Platform

Welcome to the comprehensive technical documentation for the **URL Shortener & Distributed Analytics Platform**. This documentation suite has been engineered to adhere to the highest production standards.

---

## Documentation Index

### 1. Architectural Foundations & Design
- [Project Overview](file:///e:/url_shortner/docs/PROJECT_OVERVIEW.md): Executive summary, core value proposition, and architectural highlights.
- [System Architecture](file:///e:/url_shortner/docs/ARCHITECTURE.md): High-level system topology, deep Mermaid diagrams, and component boundaries.
- [System Design Deep Dive](file:///e:/url_shortner/docs/SYSTEM_DESIGN.md): Capacity planning, quantitative estimations, CAP theorem trade-offs, and concurrency control.
- [Project Structure](file:///e:/url_shortner/docs/PROJECT_STRUCTURE.md): Granular file-by-file codebase layout and component responsibilities.
- [Module Specifications](file:///e:/url_shortner/docs/MODULES.md): Detailed module breakdown, exported classes, and inter-module dependencies.
- [Component Architecture](file:///e:/url_shortner/docs/COMPONENTS.md): Software components, interaction protocols, and specifications.

### 2. Data Pipelines & Operational Workflows
- [Data Flow Architecture](file:///e:/url_shortner/docs/DATA_FLOW.md): Ingress, transformation, storage, and egress data flows.
- [Operational Workflows](file:///e:/url_shortner/docs/WORKFLOWS.md): End-to-end workflows for auth, one-time links, API keys, and abuse management.
- [Database Schema & Data Architecture](file:///e:/url_shortner/docs/DATABASE.md): Complete ERD, table specs, indexing strategy, and partitioning guide.

### 3. API, Authentication & Security
- [API Reference & Specification](file:///e:/url_shortner/docs/API_DOCUMENTATION.md): Global headers, request/response schemas, and cURL examples for all endpoints.
- [Authentication & Authorization](file:///e:/url_shortner/docs/AUTHENTICATION.md): Dual-auth model, Argon2id hashing, token rotation, and RBAC scopes.
- [Application Security Architecture](file:///e:/url_shortner/docs/SECURITY.md): Threat model, strict anti-SSRF defense, sliding-window rate limiting, and GDPR compliance.
- [Error Handling Architecture](file:///e:/url_shortner/docs/ERROR_HANDLING.md): RFC-standard error envelopes, domain exception catalog, and DLQ handling.

### 4. Configuration, Operations & Observability
- [Configuration Management Guide](file:///e:/url_shortner/docs/CONFIGURATION.md): Pydantic Settings v2 architecture and environment profiles.
- [Environment Variables Reference](file:///e:/url_shortner/docs/ENVIRONMENT_VARIABLES.md): Exhaustive reference table of all configuration parameters.
- [Logging & Monitoring](file:///e:/url_shortner/docs/LOGGING_AND_MONITORING.md): Structured JSON logging, Prometheus metrics, and Grafana dashboard layout.
- [Performance & Optimization](file:///e:/url_shortner/docs/PERFORMANCE.md): Latency targets, optimization mechanisms, and load testing execution.
- [Testing Strategy & Verification](file:///e:/url_shortner/docs/TESTING.md): Test pyramid, directory structure, commands, and isolation fixtures.
- [Production Deployment Guide](file:///e:/url_shortner/docs/DEPLOYMENT.md): Docker Compose, Kubernetes manifests, Helm chart, and production checklist.
- [Production Troubleshooting](file:///e:/url_shortner/docs/TROUBLESHOOTING.md): Playbooks for latency spikes, queue drops, consumer lag, and Redis outages.

### 5. Governance & Career Defense
- [Contributing Guidelines](file:///e:/url_shortner/docs/CONTRIBUTING.md): Engineering principles, local setup, and pull request conventions.
- [Changelog](file:///e:/url_shortner/docs/CHANGELOG.md): Historical record of features, security fixes, and releases.
- [Engineering Glossary](file:///e:/url_shortner/docs/GLOSSARY.md): Definitions of distributed systems, security, and backend engineering terms.
- [Technical Interview Q&A](file:///e:/url_shortner/docs/TECHNICAL_INTERVIEW.md): Senior/Principal interview defense questions on architecture and tradeoffs.

---

## Architecture Decision Records (ADRs)

- [ADR 0001: Base62 Cryptographically Random Short Code Generation](file:///e:/url_shortner/docs/adr/0001-base62-random-short-codes.md)
- [ADR 0002: Cache-Aside with Distributed Mutex & Null Sentinel](file:///e:/url_shortner/docs/adr/0002-cache-aside-with-redis-mutex.md)
- [ADR 0003: Asynchronous Kafka Event Stream for Click Analytics](file:///e:/url_shortner/docs/adr/0003-asynchronous-kafka-click-events.md)
- [ADR 0004: Argon2id Password Hashing & Cryptographic Refresh Token Rotation](file:///e:/url_shortner/docs/adr/0004-argon2id-and-refresh-token-rotation.md)
- [ADR 0005: Strict Anti-SSRF Validation & Private IP Blocking](file:///e:/url_shortner/docs/adr/0005-strict-anti-ssrf-validation.md)
