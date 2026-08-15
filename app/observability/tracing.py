"""Optional OpenTelemetry tracing that is a no-op when unavailable."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

_tracer_provider: Any = None


def configure_tracing(application: Any) -> None:
    """Configure OTLP tracing only when an exporter endpoint is explicitly set."""
    from app.config import settings

    if not settings.otel_exporter_otlp_endpoint:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as exc:
        raise RuntimeError(
            "OpenTelemetry dependencies are required when OTLP is configured"
        ) from exc

    global _tracer_provider
    provider = TracerProvider(
        resource=Resource.create({"service.name": settings.otel_service_name})
    )
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint))
    )
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(application, tracer_provider=provider)
    PsycopgInstrumentor().instrument(tracer_provider=provider)
    _tracer_provider = provider


def shutdown_tracing() -> None:
    """Flush configured spans during graceful shutdown."""
    global _tracer_provider
    if _tracer_provider is not None:
        _tracer_provider.shutdown()
        _tracer_provider = None


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[Any]:
    """Create a span if OpenTelemetry is installed, otherwise yield None."""
    try:
        from opentelemetry import trace
    except ImportError:
        yield None
        return

    with trace.get_tracer("nordly.support_agent").start_as_current_span(name) as span:
        for key, value in (attributes or {}).items():
            span.set_attribute(key, value)
        yield span
