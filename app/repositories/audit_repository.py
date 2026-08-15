"""Tenant-scoped immutable security audit log persistence."""

import json
import uuid
from typing import Any

from app.database import get_connection
from app.security.pii import redact_pii
from app.tenant import bind_tenant, reset_tenant


class AuditRepository:
    """Write redacted security and privacy events."""

    @staticmethod
    def record(
        tenant_id: str,
        principal: str,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        outcome: str = "success",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Append a tenant-scoped audit event."""
        token = bind_tenant(tenant_id)
        try:
            with get_connection() as conn:
                conn.execute(
                    "INSERT INTO audit_logs (audit_id, tenant_id, principal, action, "
                    "resource_type, resource_id, outcome, metadata_json) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        f"aud-{uuid.uuid4().hex}",
                        tenant_id,
                        principal,
                        action,
                        resource_type,
                        resource_id,
                        outcome,
                        json.dumps(redact_pii(metadata or {})),
                    ),
                )
                conn.commit()
        finally:
            reset_tenant(token)
