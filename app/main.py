"""Main FastAPI application entry point with lifespan management, middleware, and routers."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.v1.redirect import router as redirect_router
from app.api.v1.router import v1_router
from app.cache.redis_client import redis_manager
from app.core.config import settings
from app.core.handlers import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.database.session import check_db_health, engine, init_db
from app.events.producer import kafka_producer
from app.middleware.correlation import CorrelationIdMiddleware
from app.middleware.metrics_mw import PrometheusMetricsMiddleware
from app.middleware.rate_limit_mw import RateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.monitoring.tracer import setup_telemetry

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle management for startup and graceful shutdown."""
    # 1. Startup phase
    setup_logging(log_level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)
    logger.info("Starting %s in %s environment...", settings.APP_NAME, settings.ENVIRONMENT)

    # Initialize OpenTelemetry if enabled
    setup_telemetry()

    # Initialize database tables
    try:
        await init_db()
    except Exception as e:
        logger.error("Failed to initialize database tables: %s", str(e))

    # Initialize Redis connection pool
    await redis_manager.initialize()

    # Start Kafka Producer background dispatcher
    await kafka_producer.start()

    logger.info("%s started successfully and ready for traffic.", settings.APP_NAME)
    yield

    # 2. Graceful Shutdown phase
    logger.info("Initiating graceful shutdown...")
    await kafka_producer.stop()
    await redis_manager.close()
    await engine.dispose()
    logger.info("Shutdown completed cleanly.")


def create_application() -> FastAPI:
    """Application factory configuring middlewares, exception handlers, and endpoints."""
    app = FastAPI(
        title=settings.APP_NAME,
        description="Production-grade URL Shortening & Distributed Analytics Platform.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # 1. Register Exception Handlers
    register_exception_handlers(app)

    # 2. Register Middleware (Order matters: outer to inner)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=500)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(PrometheusMetricsMiddleware)
    app.add_middleware(RateLimitMiddleware)

    # 3. Observability Endpoints
    @app.get("/health", tags=["Observability"], summary="Comprehensive health check")
    async def health_check():
        db_health = await check_db_health()
        redis_metrics = redis_manager.get_metrics()
        kafka_metrics = kafka_producer.get_metrics()

        overall_healthy = db_health["status"] == "healthy"
        status_code = status.HTTP_200_OK if overall_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

        import json
        return Response(
            content=json.dumps({
                "status": "healthy" if overall_healthy else "degraded",
                "app": settings.APP_NAME,
                "environment": settings.ENVIRONMENT,
                "dependencies": {
                    "database": db_health,
                    "redis": redis_metrics,
                    "kafka_producer": kafka_metrics,
                },
            }),
            media_type="application/json",
            status_code=status_code,
        )

    @app.get("/metrics", tags=["Observability"], summary="Prometheus metrics scrape target")
    def metrics_scrape():
        """Scrape endpoint for Prometheus agent."""
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    # 4. Include Master API v1 Router
    app.include_router(v1_router, prefix=settings.API_V1_STR)

    # 5. Static Files & Web Dashboard UI
    import os
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

        @app.get("/", include_in_schema=False)
        @app.get("/dashboard", include_in_schema=False)
        async def serve_dashboard():
            response = FileResponse(os.path.join(static_dir, "index.html"))
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            response.headers["Clear-Site-Data"] = '"cache"'
            return response

    # 6. Include Root Redirect Router (mounted directly at root /{short_code})
    app.include_router(redirect_router)

    return app


app = create_application()
