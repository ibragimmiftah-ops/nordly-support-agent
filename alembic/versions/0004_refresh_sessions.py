"""Persist refresh sessions and close audit-log RLS.

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create hashed refresh sessions and enforce fail-closed audit RLS."""
    op.create_table(
        "refresh_sessions",
        sa.Column("session_id", sa.Text(), primary_key=True),
        sa.Column("jti_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), sa.ForeignKey("auth_users.user_id"), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("used_at", sa.TIMESTAMP(timezone=True)),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()
        ),
    )
    op.create_index(
        "idx_refresh_user_active", "refresh_sessions", ["tenant_id", "user_id", "expires_at"]
    )
    if op.get_bind().dialect.name == "postgresql":
        # Authentication resolves tenant identity before app.tenant_id can be trusted.
        for table in ("auth_users", "api_keys"):
            op.execute(sa.text(f"DROP POLICY IF EXISTS {table}_tenant_policy ON {table}"))
            op.execute(sa.text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))
        op.execute(sa.text("ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY"))
        op.execute(sa.text("ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY"))
        op.execute(sa.text("DROP POLICY IF EXISTS audit_logs_tenant_policy ON audit_logs"))
        op.execute(
            sa.text("""CREATE POLICY audit_logs_tenant_policy ON audit_logs
            USING (tenant_id = NULLIF(current_setting('app.tenant_id', TRUE), ''))
            WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', TRUE), ''))""")
        )


def downgrade() -> None:
    """Remove persisted refresh sessions."""
    op.drop_table("refresh_sessions")
