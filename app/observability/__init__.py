"""Observability primitives with optional provider integrations."""

from app.observability.context import correlation_context, get_correlation_id
from app.observability.logging import configure_logging, get_logger, redact_pii
from app.observability.metrics import metrics
from app.observability.tracing import configure_tracing, shutdown_tracing, trace_span

__all__ = [
    "configure_logging",
    "configure_tracing",
    "correlation_context",
    "get_correlation_id",
    "get_logger",
    "metrics",
    "redact_pii",
    "shutdown_tracing",
    "trace_span",
]
