"""Correlation ID middleware for distributed request tracing."""

import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import correlation_id_ctx

CORRELATION_HEADER = "X-Request-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware attaching a unique correlation ID to every incoming request and response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Extract existing X-Request-ID or generate new UUID4
        request_id = request.headers.get(CORRELATION_HEADER) or str(uuid.uuid4())
        token = correlation_id_ctx.set(request_id)

        try:
            response = await call_next(request)
            response.headers[CORRELATION_HEADER] = request_id
            return response
        finally:
            correlation_id_ctx.reset(token)
