"""Structured JSON logging and recursive PII redaction."""

import json
import logging
import re
from collections.abc import Mapping
from typing import Any

try:
    import structlog
except ImportError:  # pragma: no cover - behavior is covered through the facade
    structlog = None  # type: ignore[assignment]

from app.observability.context import get_correlation_id

_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d .()-]{7,}\d)(?!\w)")
_CARD = re.compile(r"(?<!\d)(?:\d[ -]*?){13,19}(?!\d)")
_SENSITIVE_KEYS = {"authorization", "cookie", "email", "message", "password", "token"}


def _redact_text(value: str) -> str:
    value = _EMAIL.sub("[REDACTED_EMAIL]", value)
    value = _PHONE.sub("[REDACTED_PHONE]", value)
    return _CARD.sub("[REDACTED_PAYMENT]", value)


def redact_pii(value: Any, *, key: str | None = None) -> Any:
    """Recursively redact common PII and secrets without mutating input."""
    if key and key.lower() in _SENSITIVE_KEYS and key.lower() not in {"message"}:
        return "[REDACTED]"
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, Mapping):
        return {item_key: redact_pii(item, key=str(item_key)) for item_key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(redact_pii(item) for item in value)
    if isinstance(value, list):
        return [redact_pii(item) for item in value]
    return value


def _add_context(_logger: Any, _method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    correlation_id = get_correlation_id()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    return event_dict


def _redact_event(_logger: Any, _method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    return redact_pii(event_dict)


def configure_logging(level: str = "INFO") -> None:
    """Configure stdlib and structlog to emit JSON records."""
    logging.basicConfig(level=level.upper(), format="%(message)s", force=True)
    if structlog is None:
        return
    structlog.configure(
        processors=[
            _add_context,
            _redact_event,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


class _StdlibJsonLogger:
    """Small structured logger used when structlog is unavailable."""

    def __init__(self, name: str | None) -> None:
        self._logger = logging.getLogger(name)

    def warning(self, event: str, **values: Any) -> None:
        """Emit one redacted JSON warning."""
        payload = _add_context(None, "warning", {"event": event, **values})
        self._logger.warning(json.dumps(redact_pii(payload), default=str))

    def info(self, event: str, **values: Any) -> None:
        """Emit one redacted JSON info record."""
        payload = _add_context(None, "info", {"event": event, **values})
        self._logger.info(json.dumps(redact_pii(payload), default=str))

    def error(self, event: str, **values: Any) -> None:
        """Emit one redacted JSON error record."""
        payload = _add_context(None, "error", {"event": event, **values})
        self._logger.error(json.dumps(redact_pii(payload), default=str))

    def exception(self, event: str, **values: Any) -> None:
        """Emit one redacted JSON exception record."""
        payload = _add_context(None, "exception", {"event": event, **values})
        self._logger.exception(json.dumps(redact_pii(payload), default=str))


def get_logger(name: str | None = None) -> Any:
    """Return a structured logger."""
    if structlog is None:
        return _StdlibJsonLogger(name)
    return structlog.get_logger(name)
