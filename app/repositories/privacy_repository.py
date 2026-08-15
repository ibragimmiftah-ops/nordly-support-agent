"""Deterministic tenant/customer data erasure operations."""

from app.database import get_connection


class PrivacyRepository:
    """Delete customer data while enforcing tenant boundaries."""

    @staticmethod
    def delete_customer(tenant_id: str, customer_id: str) -> bool:
        """Delete a customer and related data only inside the caller's tenant."""
        with get_connection() as conn:
            customer = conn.execute(
                "SELECT main_contact_email FROM customers WHERE tenant_id = ? AND customer_id = ?",
                (tenant_id, customer_id),
            ).fetchone()
            if not customer:
                return False
            ticket_rows = conn.execute(
                "SELECT ticket_id FROM tickets WHERE tenant_id = ? AND customer_email = ?",
                (tenant_id, customer["main_contact_email"]),
            ).fetchall()
            ticket_ids = [row["ticket_id"] for row in ticket_rows]
            conn.execute(
                "DELETE FROM agent_memory WHERE tenant_id = ? AND customer_id = ?",
                (tenant_id, customer_id),
            )
            conn.execute(
                "UPDATE provider_usage SET customer_id = NULL "
                "WHERE tenant_id = ? AND customer_id = ?",
                (tenant_id, customer_id),
            )
            for ticket_id in ticket_ids:
                run_rows = conn.execute(
                    "SELECT run_id FROM agent_runs WHERE tenant_id = ? AND ticket_id = ?",
                    (tenant_id, ticket_id),
                ).fetchall()
                for run in run_rows:
                    conn.execute(
                        "DELETE FROM tool_events WHERE tenant_id = ? AND run_id = ?",
                        (tenant_id, run["run_id"]),
                    )
                conn.execute(
                    "DELETE FROM agent_runs WHERE tenant_id = ? AND ticket_id = ?",
                    (tenant_id, ticket_id),
                )
                conn.execute(
                    "DELETE FROM escalations WHERE tenant_id = ? AND ticket_id = ?",
                    (tenant_id, ticket_id),
                )
            conn.execute(
                "DELETE FROM tickets WHERE tenant_id = ? AND customer_email = ?",
                (tenant_id, customer["main_contact_email"]),
            )
            conn.execute(
                "DELETE FROM account_status WHERE tenant_id = ? AND customer_id = ?",
                (tenant_id, customer_id),
            )
            conn.execute(
                "DELETE FROM subscriptions WHERE tenant_id = ? AND customer_id = ?",
                (tenant_id, customer_id),
            )
            conn.execute(
                "DELETE FROM customers WHERE tenant_id = ? AND customer_id = ?",
                (tenant_id, customer_id),
            )
            conn.commit()
        return True
