"""Persistent tenant-scoped provider usage accounting."""

import uuid
from datetime import UTC, datetime, timedelta

from app.database import get_connection


class UsageRepository:
    """Store usage and calculate tenant budget windows."""

    @staticmethod
    def record(
        tenant_id: str, model: str, input_tokens: int, output_tokens: int, cost: float
    ) -> None:
        """Persist one provider usage event."""
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO provider_usage (usage_id, tenant_id, model, input_tokens, "
                "output_tokens, cost_usd, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    f"use-{uuid.uuid4().hex}",
                    tenant_id,
                    model,
                    input_tokens,
                    output_tokens,
                    cost,
                    datetime.now(UTC).isoformat(),
                ),
            )
            conn.commit()

    @staticmethod
    def reserve(
        tenant_id: str, estimated_cost: float, daily_limit: float, weekly_limit: float
    ) -> str | None:
        """Atomically reserve worst-case cost against both rolling budgets."""
        reservation_id = f"res-{uuid.uuid4().hex}"
        now = datetime.now(UTC)
        with get_connection() as conn:
            if conn.__class__.__name__ == "PostgresConnection":
                conn.execute("SELECT pg_advisory_xact_lock(hashtext(?))", (tenant_id,))
            else:
                conn.execute("BEGIN IMMEDIATE")
            daily = UsageRepository._total(conn, tenant_id, now - timedelta(days=1))
            weekly = UsageRepository._total(conn, tenant_id, now - timedelta(days=7))
            reserved_row = conn.execute(
                "SELECT COALESCE(SUM(estimated_cost_usd), 0) AS total "
                "FROM budget_reservations WHERE tenant_id = ?",
                (tenant_id,),
            ).fetchone()
            reserved = float(reserved_row["total"])
            daily_exceeded = daily + reserved + estimated_cost > daily_limit
            weekly_exceeded = weekly + reserved + estimated_cost > weekly_limit
            if daily_exceeded or weekly_exceeded:
                conn.rollback()
                return None
            conn.execute(
                "INSERT INTO budget_reservations "
                "(reservation_id, tenant_id, estimated_cost_usd, created_at) VALUES (?, ?, ?, ?)",
                (reservation_id, tenant_id, estimated_cost, now.isoformat()),
            )
            conn.commit()
        return reservation_id

    @staticmethod
    def _total(conn, tenant_id: str, since: datetime) -> float:
        row = conn.execute(
            "SELECT COALESCE(SUM(cost_usd), 0) AS total FROM provider_usage "
            "WHERE tenant_id = ? AND created_at >= ?",
            (tenant_id, since.isoformat()),
        ).fetchone()
        return float(row["total"])

    @staticmethod
    def finalize(
        reservation_id: str,
        tenant_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        customer_id: str | None = None,
    ) -> None:
        """Replace one reservation with actual usage in the same transaction."""
        with get_connection() as conn:
            deleted = conn.execute(
                "DELETE FROM budget_reservations WHERE reservation_id = ? AND tenant_id = ?",
                (reservation_id, tenant_id),
            )
            if deleted.rowcount != 1:
                raise ValueError("Budget reservation does not exist")
            conn.execute(
                "INSERT INTO provider_usage (usage_id, tenant_id, model, input_tokens, "
                "output_tokens, cost_usd, created_at, customer_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"use-{uuid.uuid4().hex}",
                    tenant_id,
                    model,
                    input_tokens,
                    output_tokens,
                    cost,
                    datetime.now(UTC).isoformat(),
                    customer_id,
                ),
            )
            conn.commit()

    @staticmethod
    def release(reservation_id: str, tenant_id: str) -> None:
        """Release capacity after a provider failure or cancellation."""
        with get_connection() as conn:
            conn.execute(
                "DELETE FROM budget_reservations WHERE reservation_id = ? AND tenant_id = ?",
                (reservation_id, tenant_id),
            )
            conn.commit()

    @staticmethod
    def spent_since(tenant_id: str, since: datetime) -> float:
        """Sum cost inside one tenant and time window."""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(cost_usd), 0) AS total FROM provider_usage "
                "WHERE tenant_id = ? AND created_at >= ?",
                (tenant_id, since.isoformat()),
            ).fetchone()
        return float(row["total"])

    @classmethod
    def current_spend(cls, tenant_id: str) -> tuple[float, float]:
        """Return rolling daily and weekly spend for a tenant."""
        now = datetime.now(UTC)
        return cls.spent_since(tenant_id, now - timedelta(days=1)), cls.spent_since(
            tenant_id, now - timedelta(days=7)
        )
