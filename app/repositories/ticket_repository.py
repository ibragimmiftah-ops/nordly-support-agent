"""Ticket repository for database operations."""

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from app.agent.schemas import SupportDecision, TicketResponse
from app.config import settings
from app.database import get_connection
from app.security.encryption import decrypt, encrypt


class TicketRepository:
    """Repository for ticket-related database operations."""

    @staticmethod
    def create_ticket(ticket_data: dict[str, Any], tenant_id: str = settings.demo_tenant_id) -> str:
        """Create a new ticket and return the ticket ID."""
        ticket_id = f"TICK-{uuid.uuid4().hex[:8].upper()}"
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO tickets (ticket_id, customer_email, subject, message,
                                    product_area, status, tenant_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ticket_id,
                    ticket_data["customer_email"],
                    ticket_data["subject"],
                    encrypt(ticket_data["message"]),
                    ticket_data.get("product_area"),
                    "open",
                    tenant_id,
                ),
            )
            conn.commit()
        return ticket_id

    @staticmethod
    def get_ticket(
        ticket_id: str, tenant_id: str = settings.demo_tenant_id
    ) -> TicketResponse | None:
        """Get ticket by ID."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT ticket_id, customer_email, subject, message, product_area,
                       status, priority, category, created_at, analyzed_at, decision_json
                FROM tickets
                WHERE ticket_id = ? AND tenant_id = ?
                """,
                (ticket_id, tenant_id),
            )
            row = cursor.fetchone()
            if not row:
                return None

            decision = None
            if row["decision_json"]:
                decision_data = json.loads(decrypt(row["decision_json"]))
                decision = SupportDecision(**decision_data)

            return TicketResponse(
                ticket_id=row["ticket_id"],
                customer_email=row["customer_email"],
                subject=row["subject"],
                message=decrypt(row["message"]),
                product_area=row["product_area"],
                status=row["status"],
                priority=row["priority"],
                category=row["category"],
                created_at=row["created_at"],
                analyzed_at=row["analyzed_at"],
                decision=decision,
            )

    @staticmethod
    def get_tickets(
        limit: int = 50, offset: int = 0, tenant_id: str = settings.demo_tenant_id
    ) -> list[TicketResponse]:
        """Get list of tickets with pagination."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT ticket_id, customer_email, subject, message, product_area,
                       status, priority, category, created_at, analyzed_at, decision_json
                FROM tickets
                WHERE tenant_id = ? ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (tenant_id, limit, offset),
            )
            rows = cursor.fetchall()
            tickets = []
            for row in rows:
                decision = None
                if row["decision_json"]:
                    decision_data = json.loads(decrypt(row["decision_json"]))
                    decision = SupportDecision(**decision_data)

                tickets.append(
                    TicketResponse(
                        ticket_id=row["ticket_id"],
                        customer_email=row["customer_email"],
                        subject=row["subject"],
                        message=decrypt(row["message"]),
                        product_area=row["product_area"],
                        status=row["status"],
                        priority=row["priority"],
                        category=row["category"],
                        created_at=row["created_at"],
                        analyzed_at=row["analyzed_at"],
                        decision=decision,
                    )
                )
            return tickets

    @staticmethod
    def get_previous_tickets(
        customer_email: str, limit: int = 5, tenant_id: str = settings.demo_tenant_id
    ) -> list[dict[str, Any]]:
        """Get previous tickets for a customer."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT ticket_id, subject, status, priority, category, created_at
                FROM tickets
                WHERE customer_email = ? AND tenant_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (customer_email, tenant_id, limit),
            )
            rows = cursor.fetchall()
            return [
                {
                    "ticket_id": row["ticket_id"],
                    "subject": row["subject"],
                    "status": row["status"],
                    "priority": row["priority"],
                    "category": row["category"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

    @staticmethod
    def update_ticket_analysis(
        ticket_id: str,
        decision: SupportDecision,
        tenant_id: str = settings.demo_tenant_id,
    ) -> None:
        """Update ticket with analysis results."""
        with get_connection() as conn:
            cursor = conn.cursor()
            decision_json = json.dumps(decision.model_dump(mode="json"))
            cursor.execute(
                """
                UPDATE tickets
                SET status = ?, priority = ?, category = ?, analyzed_at = ?, decision_json = ?
                WHERE ticket_id = ? AND tenant_id = ?
                """,
                (
                    decision.resolution_status.value,
                    decision.priority.value,
                    decision.category.value,
                    datetime.now(UTC).isoformat(),
                    encrypt(decision_json),
                    ticket_id,
                    tenant_id,
                ),
            )
            conn.commit()

    @staticmethod
    def update_ticket_status(
        ticket_id: str, status: str, tenant_id: str = settings.demo_tenant_id
    ) -> bool:
        """Update ticket status."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tickets SET status = ? WHERE ticket_id = ? AND tenant_id = ?",
                (status, ticket_id, tenant_id),
            )
            conn.commit()
            return cursor.rowcount == 1
