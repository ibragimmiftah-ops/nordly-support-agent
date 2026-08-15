"""Tenant-aware Redis cache facade for frequent lookups.

Provides safe, bounded caching for read-only data. Writes always invalidate
cached entries for the affected tenant to prevent stale reads across replicas.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.config import settings
from app.observability import get_logger, metrics

logger = get_logger(__name__)

_PREFIX = "nordly:cache"


def _redis_client() -> Any | None:
    """Return a synchronous Redis client when REDIS_URL is configured."""
    if not settings.redis_url:
        return None
    try:
        from redis import Redis

        return Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=2)
    except Exception as exc:  # pragma: no cover - depends on network
        logger.warning("redis_client_failed", error=str(exc))
        return None


def _cache_key(tenant_id: str, namespace: str, *parts: str) -> str:
    """Build a deterministic, tenant-scoped cache key."""
    payload = "|".join([tenant_id, namespace, *parts])
    return f"{_PREFIX}:{namespace}:{tenant_id}:{hashlib.sha256(payload.encode()).hexdigest()[:32]}"


def get_or_set(tenant_id: str, namespace: str, key_parts: tuple[str, ...], producer: Any) -> Any:
    """Return cached value or compute it, store it, and return it.

    The producer must be a callable that returns a JSON-serializable value.
    """
    client = _redis_client()
    ttl = settings.cache_ttl_seconds
    if not client or ttl <= 0:
        return producer()

    key = _cache_key(tenant_id, namespace, *key_parts)
    try:
        cached = client.get(key)
        if cached is not None:
            metrics.http_requests.labels(method="CACHE", route=namespace, status="HIT").inc()
            return json.loads(cached)
    except Exception as exc:  # pragma: no cover - depends on network
        logger.warning("cache_read_failed", key=key, error=str(exc))

    value = producer()
    try:
        serialized = json.dumps(value, default=str)
        client.setex(key, ttl, serialized)
    except Exception as exc:  # pragma: no cover - depends on network
        logger.warning("cache_write_failed", key=key, error=str(exc))
    metrics.http_requests.labels(method="CACHE", route=namespace, status="MISS").inc()
    return value


def invalidate(tenant_id: str, namespace: str | None = None) -> None:
    """Drop cached entries for a tenant, optionally scoped to one namespace."""
    client = _redis_client()
    if not client:
        return

    pattern = f"{_PREFIX}:{namespace or '*'}:{tenant_id}:*"
    try:
        cursor = 0
        while True:
            cursor, keys = client.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                client.delete(*keys)
            if cursor == 0:
                break
    except Exception as exc:  # pragma: no cover - depends on network
        logger.warning("cache_invalidate_failed", pattern=pattern, error=str(exc))
