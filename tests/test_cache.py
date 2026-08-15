"""Cache facade tests with and without Redis."""

import json
from unittest.mock import MagicMock, patch

from app.cache import _cache_key, get_or_set, invalidate


def test_cache_key_is_deterministic_and_tenant_scoped():
    """Cache keys include tenant and namespace and are stable."""
    key = _cache_key("tenant-a", "customers", "email", "a@example.com")
    assert key.startswith("nordly:cache:customers:tenant-a:")
    assert key == _cache_key("tenant-a", "customers", "email", "a@example.com")
    assert key != _cache_key("tenant-b", "customers", "email", "a@example.com")


def test_get_or_set_returns_producer_without_redis():
    """When Redis is unavailable the producer runs every time."""
    calls = []

    def producer():
        calls.append(1)
        return {"value": 42}

    with patch("app.cache.settings.redis_url", None):
        assert get_or_set("tenant-a", "ns", ("k",), producer) == {"value": 42}
        assert get_or_set("tenant-a", "ns", ("k",), producer) == {"value": 42}
    assert len(calls) == 2


def test_get_or_set_uses_redis_and_respects_ttl():
    """Cached values are returned, misses are stored, and TTL is applied."""
    client = MagicMock()
    client.get.return_value = None

    calls = []

    def producer():
        calls.append(1)
        return {"value": 7}

    with (
        patch("app.cache.settings.redis_url", "redis://localhost:6379/0"),
        patch("app.cache.settings.cache_ttl_seconds", 42),
        patch("redis.Redis.from_url", return_value=client),
    ):
        result = get_or_set("tenant-a", "ns", ("k",), producer)

    assert result == {"value": 7}
    assert len(calls) == 1
    client.setex.assert_called_once()
    _, ttl, serialized = client.setex.call_args[0]
    assert ttl == 42
    assert json.loads(serialized) == {"value": 7}


def test_get_or_set_returns_cached_value_on_hit():
    """A cached JSON value is returned directly without calling the producer."""
    client = MagicMock()
    client.get.return_value = json.dumps([{"incident_id": "I-1"}])

    def producer():
        raise AssertionError("producer should not be called")

    with (
        patch("app.cache.settings.redis_url", "redis://localhost:6379/0"),
        patch("redis.Redis.from_url", return_value=client),
    ):
        result = get_or_set("tenant-a", "incidents:active", ("all", "10"), producer)

    assert result == [{"incident_id": "I-1"}]


def test_invalidate_scans_and_deletes_matching_keys():
    """Invalidate removes tenant-scoped keys, optionally filtered by namespace."""
    client = MagicMock()
    client.scan.side_effect = [(42, ["k1", "k2"]), (0, [])]

    with (
        patch("app.cache.settings.redis_url", "redis://localhost:6379/0"),
        patch("redis.Redis.from_url", return_value=client),
    ):
        invalidate("tenant-a", "incidents")

    assert client.scan.call_count == 2
    assert client.scan.call_args_list[0].kwargs == {
        "cursor": 0,
        "match": "nordly:cache:incidents:tenant-a:*",
        "count": 100,
    }
    client.delete.assert_called_once_with("k1", "k2")


def test_invalidate_is_noop_without_redis():
    """Invalidate does nothing when Redis is not configured."""
    with patch("app.cache.settings.redis_url", None):
        invalidate("tenant-a")
