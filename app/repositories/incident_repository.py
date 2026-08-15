"""Incident repository for database operations."""

import json
from typing import Any

from app.agent.schemas import Incident
from app.cache import get_or_set, invalidate
from app.config import settings
from app.database import get_connection


class IncidentRepository:
    """Repository for incident-related database operations."""

    @staticmethod
    def get_active_incidents(
        product_area: str | None = None,
        limit: int = 10,
        tenant_id: str = settings.demo_tenant_id,
    ) -> list[Incident]:
        """Get active incidents, optionally filtered by product area."""
        limit = max(1, min(limit, 50))

        def _load() -> list[dict[str, Any]]:
            with get_connection() as conn:
                cursor = conn.cursor()
                if product_area:
                    cursor.execute(
                        """
                        SELECT incident_id, title, product_area, status, severity,
                               description, started_at, resolved_at, affected_customers
                        FROM incidents
                        WHERE tenant_id = ? AND status != 'resolved' AND product_area = ?
                        ORDER BY started_at DESC LIMIT ?
                        """,
                        (tenant_id, product_area, limit),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT incident_id, title, product_area, status, severity,
                               description, started_at, resolved_at, affected_customers
                        FROM incidents
                        WHERE tenant_id = ? AND status != 'resolved'
                        ORDER BY started_at DESC LIMIT ?
                        """,
                        (tenant_id, limit),
                    )
                rows = cursor.fetchall()
            return [dict(row) for row in rows]

        cached = get_or_set(
            tenant_id,
            "incidents:active",
            (product_area or "all", str(limit)),
            _load,
        )
        return [IncidentRepository._row_to_incident(row) for row in cached]

    @staticmethod
    def get_incident(incident_id: str, tenant_id: str = settings.demo_tenant_id) -> Incident | None:
        """Get incident by ID."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT incident_id, title, product_area, status, severity,
                       description, started_at, resolved_at, affected_customers
                FROM incidents
                WHERE incident_id = ? AND tenant_id = ?
                """,
                (incident_id, tenant_id),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return IncidentRepository._row_to_incident(row)

    @staticmethod
    def get_all_incidents(
        limit: int = 50, tenant_id: str = settings.demo_tenant_id
    ) -> list[Incident]:
        """Get all incidents."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT incident_id, title, product_area, status, severity,
                       description, started_at, resolved_at, affected_customers
                FROM incidents
                WHERE tenant_id = ? ORDER BY started_at DESC
                LIMIT ?
                """,
                (tenant_id, limit),
            )
            rows = cursor.fetchall()
            return [IncidentRepository._row_to_incident(row) for row in rows]

    @staticmethod
    def create_incident(
        incident_data: dict[str, Any], tenant_id: str = settings.demo_tenant_id
    ) -> None:
        """Create a new incident record."""
        with get_connection() as conn:
            cursor = conn.cursor()
            affected = json.dumps(incident_data.get("affected_customers", []))
            cursor.execute(
                """
                INSERT INTO incidents (incident_id, title, product_area, status,
                                      severity, description, started_at, resolved_at,
                                      affected_customers, tenant_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    incident_data["incident_id"],
                    incident_data["title"],
                    incident_data["product_area"],
                    incident_data["status"],
                    incident_data["severity"],
                    incident_data["description"],
                    incident_data["started_at"],
                    incident_data.get("resolved_at"),
                    affected,
                    tenant_id,
                ),
            )
            conn.commit()
        invalidate(tenant_id, "incidents")

    @staticmethod
    def _row_to_incident(row: Any) -> Incident:
        """Convert a database row to an Incident object."""
        affected = []
        if row["affected_customers"]:
            affected = json.loads(row["affected_customers"])
        return Incident(
            incident_id=row["incident_id"],
            title=row["title"],
            product_area=row["product_area"],
            status=row["status"],
            severity=row["severity"],
            description=row["description"],
            started_at=row["started_at"],
            resolved_at=row["resolved_at"],
            affected_customers=affected,
        )
