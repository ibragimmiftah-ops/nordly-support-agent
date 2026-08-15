"""Deterministic cleanup of records beyond configured retention windows."""

from datetime import UTC, datetime, timedelta

from app.config import settings
from app.database import get_connection
from app.tenant import bind_tenant, reset_tenant


class RetentionRepository:
    """Delete expired memory, audit logs, and tool activity events."""

    @staticmethod
    def cleanup() -> None:
        """Run bounded tenant-aware retention cleanup during startup."""
        now = datetime.now(UTC)
        with get_connection() as conn:
            tenants = [
                row["tenant_id"]
                for row in conn.execute("SELECT DISTINCT tenant_id FROM auth_users").fetchall()
            ]
            conn.execute(
                "DELETE FROM audit_logs WHERE created_at < ?",
                ((now - timedelta(days=settings.audit_retention_days)).isoformat(),),
            )
            conn.commit()
        for tenant_id in tenants:
            token = bind_tenant(tenant_id)
            try:
                with get_connection() as conn:
                    conn.execute(
                        "DELETE FROM agent_memory WHERE tenant_id = ? AND "
                        "(expires_at <= ? OR created_at < ?)",
                        (
                            tenant_id,
                            now.isoformat(),
                            (now - timedelta(days=settings.memory_retention_days)).isoformat(),
                        ),
                    )
                    conn.execute(
                        "DELETE FROM tool_events WHERE tenant_id = ? AND timestamp < ?",
                        (
                            tenant_id,
                            (now - timedelta(days=settings.tool_event_retention_days)).isoformat(),
                        ),
                    )
                    conn.commit()
            finally:
                reset_tenant(token)
