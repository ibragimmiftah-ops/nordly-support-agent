"""Request and agent-run correlation context."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from uuid import uuid4

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str | None:
    """Return the correlation ID bound to the current async context."""
    return _correlation_id.get()


@contextmanager
def correlation_context(correlation_id: str | None = None) -> Iterator[str]:
    """Bind a correlation ID and reliably restore the previous context."""
    value = correlation_id or f"corr-{uuid4().hex}"
    token = _correlation_id.set(value)
    try:
        yield value
    finally:
        _correlation_id.reset(token)
