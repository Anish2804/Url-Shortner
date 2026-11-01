"""OpenTelemetry distributed tracing configuration and span helpers."""

from typing import Optional
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("tracer")

_provider: Optional[TracerProvider] = None


def setup_telemetry() -> trace.Tracer:
    """Initialize OpenTelemetry tracer provider."""
    global _provider
    if not settings.OTEL_ENABLED:
        return trace.get_tracer("noop-tracer")

    try:
        resource = Resource.create({"service.name": settings.OTEL_SERVICE_NAME})
        _provider = TracerProvider(resource=resource)
        # Use batch span processor
        processor = BatchSpanProcessor(ConsoleSpanExporter())
        _provider.add_span_processor(processor)
        trace.set_tracer_provider(_provider)
        logger.info("OpenTelemetry tracing initialized for service %s", settings.OTEL_SERVICE_NAME)
    except Exception as e:
        logger.warning("Failed to initialize OpenTelemetry: %s", str(e))

    return trace.get_tracer(settings.OTEL_SERVICE_NAME)


def get_tracer(name: str = "url-shortener") -> trace.Tracer:
    return trace.get_tracer(name)
