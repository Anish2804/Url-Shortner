# Production Deployment Guide — URL Shortener & Distributed Analytics Platform

## 1. Local & Staging Deployment with Docker Compose

The fastest way to spin up the entire multi-service distributed topology (FastAPI API, Kafka Worker, PostgreSQL, Redis, Kafka KRaft, Prometheus, Grafana):

```bash
# 1. Clone repository and navigate to root
cd url_shortener

# 2. Configure environment file
cp .env.example .env

# 3. Start all services in the background
docker compose up -d --build

# 4. Verify running container health
docker compose ps

# 5. Execute database migrations
docker compose exec api alembic upgrade head
```

### Accessing Services
- **API Engine & Swagger Docs:** `http://localhost:8000/docs`
- **Health Check Endpoint:** `http://localhost:8000/health`
- **Prometheus UI:** `http://localhost:9090`
- **Grafana Dashboards:** `http://localhost:3000` (User: `admin`, Pass: `admin`)

---

## 2. Kubernetes Deployment via Manifests

To deploy to an existing Kubernetes cluster:

```bash
# 1. Apply Namespace, Secrets, and ConfigMap
kubectl apply -f infra/kubernetes/namespace.yaml
kubectl apply -f infra/kubernetes/secret.yaml
kubectl apply -f infra/kubernetes/configmap.yaml

# 2. Deploy API and Analytics Consumer Worker
kubectl apply -f infra/kubernetes/api-deployment.yaml
kubectl apply -f infra/kubernetes/api-service.yaml
kubectl apply -f infra/kubernetes/worker-deployment.yaml

# 3. Enable Horizontal Pod Autoscaling and Ingress
kubectl apply -f infra/kubernetes/api-hpa.yaml
kubectl apply -f infra/kubernetes/ingress.yaml

# 4. Verify deployment rollout status
kubectl rollout status deployment/url-shortener-api -n url-shortener
```

---

## 3. Helm Chart Deployment

Deploying with Helm allows dynamic templating and variable overrides:

```bash
# Install or upgrade Helm release
helm upgrade --install url-shortener ./infra/helm/url-shortener \
  --namespace url-shortener \
  --create-namespace \
  --set replicaCount=3 \
  --set autoscaling.enabled=true \
  --set config.environment=production
```

---

## 4. Production Readiness Checklist

Before routing live production user traffic:
- [ ] **Secrets Injected:** `SECRET_KEY` and `IP_HASH_SALT` are high-entropy 32-byte strings sourced from HashiCorp Vault or Kubernetes Secrets.
- [ ] **Database Migrations Verified:** `alembic upgrade head` executed cleanly with exit code 0.
- [ ] **Connection Pooling Calibrated:** `DB_POOL_SIZE` and `DB_MAX_OVERFLOW` matched to PostgreSQL `max_connections`.
- [ ] **Redis Eviction Configured:** Redis instance has `maxmemory` configured with `allkeys-lru` eviction policy.
- [ ] **Kafka Topics Provisioned:** `url-clicks` and `url-clicks-dlq` created with replication factor $\ge 3$.
- [ ] **Security Headers Active:** HTTPS enforced; HSTS and CSP validated via `curl -I https://short.example.com`.
- [ ] **Non-Root Execution:** Containers run under UID `10001` with `readOnlyRootFilesystem` and no privileged capabilities.
- [ ] **Probes Configured:** Kubernetes `readinessProbe` and `livenessProbe` point to `/health` with appropriate initial delays.
