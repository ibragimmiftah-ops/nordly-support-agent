"""Tenant-scoped persistence for bounded agent memory."""

from datetime import UTC, datetime

from app.agent.memory import MemoryRecord
from app.database import get_connection
from app.security.encryption import decrypt, encrypt


class MemoryRepository:
    """Persist and recall memory without crossing tenant or customer boundaries."""

    @staticmethod
    def save(record: MemoryRecord) -> bool:
        """Insert a memory record, treating its scoped dedup key idempotently."""
        with get_connection() as conn:
            exists = conn.execute(
                "SELECT memory_id FROM agent_memory WHERE tenant_id = ? AND customer_id = ? "
                "AND dedup_hash = ?",
                (record.tenant_id, record.customer_id, record.dedup_hash),
            ).fetchone()
            if exists:
                return False
            created_at = (
                record.created_at.isoformat()
                if isinstance(record.created_at, datetime)
                else record.created_at
            )
            expires_at = (
                record.expires_at.isoformat()
                if isinstance(record.expires_at, datetime)
                else record.expires_at
            )
            conn.execute(
                "INSERT INTO agent_memory (memory_id, tenant_id, customer_id, source, confidence, "
                "content, dedup_hash, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record.memory_id,
                    record.tenant_id,
                    record.customer_id,
                    record.source,
                    record.confidence,
                    encrypt(record.content),
                    record.dedup_hash,
                    created_at,
                    expires_at,
                ),
            )
            conn.commit()
            return True

    @staticmethod
    def recall(tenant_id: str, customer_id: str, limit: int) -> list[MemoryRecord]:
        """Return only non-expired records from the exact tenant/customer scope."""
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT memory_id, tenant_id, customer_id, source, confidence, content, "
                "dedup_hash, created_at, expires_at FROM agent_memory WHERE tenant_id = ? "
                "AND customer_id = ? AND expires_at > ? ORDER BY created_at DESC LIMIT ?",
                (tenant_id, customer_id, datetime.now(UTC).isoformat(), limit),
            ).fetchall()
        records = []
        for row in rows:
            values = dict(row)
            values["content"] = decrypt(values["content"])
            records.append(MemoryRecord(**values))
        return records
