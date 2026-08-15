"""Fail-closed RLS and atomic budget reservations.

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

TENANT_TABLES = (
    "customers",
    "subscriptions",
    "account_status",
    "tickets",
    "incidents",
    "escalations",
    "agent_runs",
    "tool_events",
    "agent_memory",
    "provider_usage",
)


def upgrade() -> None:
    """Add reservations and replace permissive PostgreSQL tenant policies."""
    op.add_column("provider_usage", sa.Column("customer_id", sa.Text()))
    op.create_table(
        "budget_reservations",
        sa.Column("reservation_id", sa.Text(), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
    )
    op.create_index("idx_budget_reservation_tenant", "budget_reservations", ["tenant_id"])
    if op.get_bind().dialect.name == "postgresql":
        for table in (*TENANT_TABLES, "budget_reservations"):
            op.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
            op.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
            op.execute(sa.text(f"DROP POLICY IF EXISTS {table}_tenant_policy ON {table}"))
            op.execute(
                sa.text(f"""CREATE POLICY {table}_tenant_policy ON {table}
                USING (tenant_id = NULLIF(current_setting('app.tenant_id', TRUE), ''))
                WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', TRUE), ''))""")
            )


def downgrade() -> None:
    """Remove reservations and restore the prior schema shape."""
    op.drop_table("budget_reservations")
    op.drop_column("provider_usage", "customer_id")
