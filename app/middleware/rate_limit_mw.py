"""Global rate limiting middleware applying sliding-window limits."""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.cache.rate_limiter import rate_limiter
from app.core.config import settings
from app.core.security import decode_access_token


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforces sliding-window rate limiting on all incoming requests."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        # Exclude static assets, frontend root, health check, and metrics from rate limits
        if (
            path in ("/", "/health", "/metrics", "/docs", "/openapi.json", "/dashboard", "/favicon.ico")
            or path.startswith("/static/")
            or path.endswith((".css", ".js", ".png", ".jpg", ".svg", ".ico", ".woff2", ".woff"))
        ):
            return await call_next(request)

        # Extract client IP
        forwarded = request.headers.get("X-Forwarded-For")
        client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "127.0.0.1")

        # Determine user identity from Authorization header if present
        auth_header = request.headers.get("Authorization")
        user_id = None
        if auth_header and auth_header.startswith("Bearer "):
            try:
                payload = decode_access_token(auth_header.split(" ")[1])
                user_id = payload.get("sub")
            except Exception:
                pass

        # Determine appropriate limit
        if user_id:
            identifier = f"user:{user_id}"
            limit = settings.RATE_LIMIT_AUTHENTICATED_RPM
        else:
            identifier = f"ip:{client_ip}"
            # Redirect paths get higher threshold
            if not path.startswith("/api/"):
                limit = settings.RATE_LIMIT_REDIRECT_RPM
            else:
                limit = settings.RATE_LIMIT_ANONYMOUS_RPM

        allowed, remaining, retry_after = await rate_limiter.is_allowed(
            identifier=identifier,
            limit=limit,
            window_seconds=60,
        )

        if not allowed:
            return JSONResponse(
                status_code=429,
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(retry_after),
                },
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please slow down and try again later.",
                        "details": {"retry_after_seconds": retry_after},
                    },
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
