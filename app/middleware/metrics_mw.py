"""Prometheus HTTP metrics collection middleware."""

import time
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.monitoring.prometheus import (
    active_requests_gauge,
    http_request_duration_seconds,
    http_requests_total,
)


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """Measures latency, request volume, and active connections across all endpoints."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Simplify path template for high-cardinality protection
        endpoint = request.url.path
        if endpoint.startswith("/api/v1/urls/") and len(endpoint.split("/")) > 4:
            endpoint = "/api/v1/urls/{id_or_code}"
        elif endpoint.startswith("/api/v1/analytics/") and len(endpoint.split("/")) > 4:
            endpoint = "/api/v1/analytics/{short_code}"

        active_requests_gauge.inc()
        start = time.perf_counter()

        try:
            response = await call_next(request)
            duration = time.perf_counter() - start
            status = str(response.status_code)

            http_requests_total.labels(
                method=request.method,
                endpoint=endpoint,
                status_code=status,
            ).inc()
            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=endpoint,
            ).observe(duration)

            response.headers["X-Process-Time-Ms"] = f"{duration * 1000:.2f}"
            return response
        finally:
            active_requests_gauge.dec()
