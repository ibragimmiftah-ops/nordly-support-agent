"""Bounded, redacted support-memory service."""

from app.agent.memory import MemoryRecord
from app.observability.logging import redact_pii
from app.repositories.memory_repository import MemoryRepository


class MemoryService:
    """Create safe support facts and format bounded recall context."""

    MAX_CONTENT = 1000
    MAX_RECALL = 5

    @classmethod
    def remember(
        cls, tenant_id: str, customer_id: str, content: str, source: str, confidence: float
    ) -> MemoryRecord | None:
        """Redact and persist one bounded, deduplicated support fact."""
        safe_content = str(redact_pii(content)).strip()[: cls.MAX_CONTENT]
        if not safe_content:
            return None
        record = MemoryRecord.create(
            customer_id, safe_content, source, tenant_id, max(0.0, min(confidence, 1.0))
        )
        return record if MemoryRepository.save(record) else None

    @classmethod
    def recall_context(cls, tenant_id: str, customer_id: str) -> str:
        """Build an untrusted, bounded context block from the exact scope."""
        records = MemoryRepository.recall(tenant_id, customer_id, cls.MAX_RECALL)
        return "\n".join(f"- {record.content}" for record in records)[:4000]
