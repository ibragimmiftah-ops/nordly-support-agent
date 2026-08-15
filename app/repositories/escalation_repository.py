"""Persistence operations for escalations."""

from typing import Any

from app.agent.schemas import Escalation, EscalationTeam, Priority
from app.config import settings
from app.database import get_connection


class EscalationRepository:
    """Repository for bounded escalation persistence."""

    @staticmethod
    def create(escalation: Escalation, tenant_id: str = settings.demo_tenant_id) -> None:
        """Persist an escalation."""
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO escalations
                (escalation_id, ticket_id, destination_team, priority, reason,
                 agent_summary, created_at, status, tenant_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    escalation.escalation_id,
                    escalation.ticket_id,
                    escalation.destination_team.value,
                    escalation.priority.value,
                    escalation.reason,
                    escalation.agent_summary,
                    escalation.created_at.isoformat(),
                    escalation.status,
                    tenant_id,
                ),
            )
            conn.commit()

    @staticmethod
    def get_by_ticket(
        ticket_id: str, limit: int = 50, tenant_id: str = settings.demo_tenant_id
    ) -> list[Escalation]:
        """Return escalations belonging to one ticket."""
        limit = max(1, min(limit, 100))
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT escalation_id, ticket_id, destination_team, priority,
                reason, agent_summary, created_at, status FROM escalations
                WHERE ticket_id = ? AND tenant_id = ? ORDER BY created_at DESC LIMIT ?""",
                (ticket_id, tenant_id, limit),
            ).fetchall()
        return [EscalationRepository._to_model(row) for row in rows]

    @staticmethod
    def list_all(
        limit: int = 50, offset: int = 0, tenant_id: str = settings.demo_tenant_id
    ) -> list[Escalation]:
        """Return escalations with bounded pagination."""
        limit = max(1, min(limit, 100))
        offset = max(0, offset)
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT escalation_id, ticket_id, destination_team, priority,
                reason, agent_summary, created_at, status FROM escalations
                WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?""",
                (tenant_id, limit, offset),
            ).fetchall()
        return [EscalationRepository._to_model(row) for row in rows]

    @staticmethod
    def _to_model(row: Any) -> Escalation:
        """Convert a database row to a model."""
        return Escalation(
            escalation_id=row["escalation_id"],
            ticket_id=row["ticket_id"],
            destination_team=EscalationTeam(row["destination_team"]),
            priority=Priority(row["priority"]),
            reason=row["reason"],
            agent_summary=row["agent_summary"],
            created_at=row["created_at"],
            status=row["status"],
        )
