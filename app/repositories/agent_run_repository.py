"""Persistence operations for agent runs and their tool events."""

from app.agent.schemas import AgentRun, ToolActivityEvent
from app.config import settings
from app.database import get_connection
from app.security.encryption import encrypt


class AgentRunRepository:
    """Repository for agent execution metadata."""

    @staticmethod
    def create(run: AgentRun, tenant_id: str = settings.demo_tenant_id) -> None:
        """Persist an agent run."""
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO agent_runs
                (run_id, ticket_id, started_at, completed_at, duration_ms,
                  final_status, tools_used, failure_category, is_demo, tenant_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run.run_id,
                    run.ticket_id,
                    run.started_at.isoformat(),
                    run.completed_at.isoformat() if run.completed_at else None,
                    run.duration_ms,
                    run.final_status.value if run.final_status else None,
                    ",".join(run.tools_used),
                    run.failure_category,
                    run.is_demo,
                    tenant_id,
                ),
            )
            conn.commit()

    @staticmethod
    def get_by_ticket(
        ticket_id: str, limit: int = 50, tenant_id: str = settings.demo_tenant_id
    ) -> list[AgentRun]:
        """Return runs belonging to one ticket."""
        limit = max(1, min(limit, 100))
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT run_id, ticket_id, started_at, completed_at, duration_ms,
                final_status, tools_used, failure_category, is_demo FROM agent_runs
                WHERE ticket_id = ? AND tenant_id = ? ORDER BY started_at DESC LIMIT ?""",
                (ticket_id, tenant_id, limit),
            ).fetchall()
        return [
            AgentRun(
                run_id=row["run_id"],
                ticket_id=row["ticket_id"],
                started_at=row["started_at"],
                completed_at=row["completed_at"],
                duration_ms=row["duration_ms"],
                final_status=row["final_status"],
                tools_used=row["tools_used"].split(",") if row["tools_used"] else [],
                failure_category=row["failure_category"],
                is_demo=bool(row["is_demo"]),
            )
            for row in rows
        ]


class ToolEventRepository:
    """Repository for tool invocation audit events."""

    @staticmethod
    def create_many(
        events: list[ToolActivityEvent], tenant_id: str = settings.demo_tenant_id
    ) -> None:
        """Persist tool events as one transaction."""
        if not events:
            return
        with get_connection() as conn:
            conn.executemany(
                """INSERT INTO tool_events
                (run_id, tool_name, tool_input, tool_output_summary,
                 timestamp, duration_ms, tenant_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        event.run_id,
                        event.tool_name,
                        encrypt(str(event.tool_input)),
                        event.tool_output_summary,
                        event.timestamp.isoformat(),
                        event.duration_ms,
                        tenant_id,
                    )
                    for event in events
                ],
            )
            conn.commit()
