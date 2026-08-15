"""Repository-independent, customer-scoped agent memory contracts."""

import hashlib
import json
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import uuid4


@dataclass(frozen=True)
class MemoryRecord:
    """A durable, customer-scoped support fact."""

    memory_id: str
    customer_id: str
    content: str
    tenant_id: str = "demo"
    source: str = "support_fact"
    confidence: float = 1.0
    dedup_hash: str = ""
    created_at: str = ""
    expires_at: str = ""

    @classmethod
    def create(
        cls,
        customer_id: str,
        content: str,
        source: str = "support_fact",
        tenant_id: str = "demo",
        confidence: float = 1.0,
        ttl_days: int = 90,
    ) -> "MemoryRecord":
        """Create a record with portable string identifiers and timestamp."""
        created = datetime.now(UTC)
        return cls(
            memory_id=f"mem-{uuid4().hex}",
            customer_id=customer_id,
            content=content,
            tenant_id=tenant_id,
            source=source,
            confidence=confidence,
            dedup_hash=hashlib.sha256(content.casefold().encode()).hexdigest(),
            created_at=created.isoformat(),
            expires_at=(created + timedelta(days=ttl_days)).isoformat(),
        )


class MemoryStore(Protocol):
    """Minimal persistence contract; implementations own no application repository."""

    def save(self, record: MemoryRecord) -> None:
        """Persist one record."""
        ...

    def load(self, customer_id: str, limit: int) -> Iterable[MemoryRecord]:
        """Load newest records belonging only to one customer."""
        ...


class CallbackMemoryStore:
    """Adapter around persistence callbacks supplied by the composition root."""

    def __init__(
        self,
        save: Callable[[MemoryRecord], None],
        load: Callable[[str, int], Iterable[MemoryRecord]],
    ) -> None:
        """Initialize the adapter with owner-supplied callbacks."""
        self._save = save
        self._load = load

    def save(self, record: MemoryRecord) -> None:
        """Delegate persistence to the injected callback."""
        self._save(record)

    def load(self, customer_id: str, limit: int) -> Iterable[MemoryRecord]:
        """Reject callback results that cross the customer boundary."""
        records = list(self._load(customer_id, limit))
        if any(record.customer_id != customer_id for record in records):
            raise ValueError("Memory callback returned data for another customer")
        return records[:limit]


class AgentMemory:
    """Validated service for bounded support memory."""

    def __init__(self, store: MemoryStore, max_content_length: int = 2000) -> None:
        """Initialize bounded memory over an injected store."""
        self._store = store
        self._max_content_length = max_content_length

    def remember(self, customer_id: str, content: str, kind: str = "support_fact") -> MemoryRecord:
        """Persist a non-empty bounded memory item."""
        customer_id = customer_id.strip()
        content = content.strip()
        if not customer_id or not content:
            raise ValueError("customer_id and content are required")
        if len(content) > self._max_content_length:
            raise ValueError("Memory content exceeds configured limit")
        record = MemoryRecord.create(customer_id, content, kind)
        self._store.save(record)
        return record

    def recall(self, customer_id: str, limit: int = 10) -> list[MemoryRecord]:
        """Return bounded, customer-scoped memory."""
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        return list(self._store.load(customer_id.strip(), limit))


def sqlite_callbacks(
    execute: Callable[[str, tuple[object, ...]], object],
    fetchall: Callable[[str, tuple[object, ...]], Iterable[object]],
) -> tuple[Callable[[MemoryRecord], None], Callable[[str, int], Iterable[MemoryRecord]]]:
    """Build SQLite-compatible callbacks from injected execution primitives.

    The owner creates ``agent_memory(memory_id TEXT PRIMARY KEY, customer_id TEXT,
    payload TEXT, created_at TEXT)`` and controls transactions/connections.
    """

    def save(record: MemoryRecord) -> None:
        execute(
            "INSERT INTO agent_memory (memory_id, customer_id, payload, created_at) "
            "VALUES (?, ?, ?, ?)",
            (record.memory_id, record.customer_id, json.dumps(asdict(record)), record.created_at),
        )

    def load(customer_id: str, limit: int) -> Iterable[MemoryRecord]:
        rows = fetchall(
            "SELECT payload FROM agent_memory WHERE customer_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (customer_id, limit),
        )
        return [MemoryRecord(**json.loads(row[0])) for row in rows]  # type: ignore[index]

    return save, load
