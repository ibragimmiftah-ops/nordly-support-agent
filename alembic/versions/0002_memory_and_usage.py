"""Add tenant-scoped agent memory and provider usage.

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create persistent memory and usage accounting tables."""
    op.create_table(
        "agent_memory",
        sa.Column("memory_id", sa.Text(), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("customer_id", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("dedup_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(), nullable=False),
        sa.UniqueConstraint("tenant_id", "customer_id", "dedup_hash"),
    )
    op.create_index(
        "idx_memory_recall",
        "agent_memory",
        ["tenant_id", "customer_id", "expires_at", "created_at"],
    )
    op.create_table(
        "provider_usage",
        sa.Column("usage_id", sa.Text(), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
    )
    op.create_index("idx_usage_budget", "provider_usage", ["tenant_id", "created_at"])
    if op.get_bind().dialect.name == "postgresql":
        for table in ("agent_memory", "provider_usage"):
            op.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
            op.execute(
                sa.text(f"""CREATE POLICY {table}_tenant_policy ON {table}
                USING (NULLIF(current_setting('app.tenant_id', TRUE), '') IS NULL
                       OR tenant_id = current_setting('app.tenant_id', TRUE))
                WITH CHECK (NULLIF(current_setting('app.tenant_id', TRUE), '') IS NULL
                       OR tenant_id = current_setting('app.tenant_id', TRUE))""")
            )


def downgrade() -> None:
    """Remove provider usage and agent memory."""
    op.drop_table("provider_usage")
    op.drop_table("agent_memory")
