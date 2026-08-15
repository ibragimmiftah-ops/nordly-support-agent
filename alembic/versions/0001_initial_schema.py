"""Create the current tenant, authentication, and audit schema.

Revision ID: 0001
Revises: None
"""

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

BUSINESS_TABLES = (
    "customers",
    "subscriptions",
    "account_status",
    "tickets",
    "incidents",
    "escalations",
    "agent_runs",
    "tool_events",
)


def tenant_column() -> sa.Column:
    """Return the tenant discriminator shared by business tables."""
    return sa.Column("tenant_id", sa.Text(), nullable=False, server_default="demo")


def upgrade() -> None:
    """Create the baseline schema matching app.database.init_database."""
    op.create_table(
        "customers",
        sa.Column("customer_id", sa.Text(), primary_key=True),
        sa.Column("company", sa.Text(), nullable=False),
        sa.Column("domain", sa.Text(), nullable=False),
        sa.Column("account_state", sa.Text(), nullable=False),
        sa.Column("country", sa.Text(), nullable=False),
        sa.Column("seats", sa.Integer(), nullable=False),
        sa.Column("plan", sa.Text(), nullable=False),
        sa.Column("main_contact_email", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.func.current_timestamp()),
        tenant_column(),
    )
    op.create_table(
        "subscriptions",
        sa.Column("subscription_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("customer_id", sa.Text(), sa.ForeignKey("customers.customer_id"), nullable=False),
        sa.Column("plan", sa.Text(), nullable=False),
        sa.Column("billing_status", sa.Text(), nullable=False),
        sa.Column("renewal_date", sa.Text()),
        sa.Column("cancellation_status", sa.Boolean(), server_default=sa.false()),
        sa.Column("seat_limit", sa.Integer(), nullable=False),
        sa.Column("features", sa.Text()),
        sa.Column("monthly_price", sa.Float(), nullable=False),
        tenant_column(),
    )
    op.create_table(
        "account_status",
        sa.Column("account_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "customer_id",
            sa.Text(),
            sa.ForeignKey("customers.customer_id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("state_reason", sa.Text()),
        sa.Column("last_login", sa.Text()),
        sa.Column("mfa_enabled", sa.Boolean(), server_default=sa.false()),
        sa.Column("sso_enabled", sa.Boolean(), server_default=sa.false()),
        sa.Column("suspicious_activity", sa.Boolean(), server_default=sa.false()),
        sa.Column("notes", sa.Text()),
        tenant_column(),
    )
    op.create_table(
        "tickets",
        sa.Column("ticket_id", sa.Text(), primary_key=True),
        sa.Column("customer_email", sa.Text(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("product_area", sa.Text()),
        sa.Column("status", sa.Text(), server_default="open"),
        sa.Column("priority", sa.Text()),
        sa.Column("category", sa.Text()),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.func.current_timestamp()),
        sa.Column("analyzed_at", sa.TIMESTAMP()),
        sa.Column("decision_json", sa.Text()),
        tenant_column(),
    )
    op.create_table(
        "incidents",
        sa.Column("incident_id", sa.Text(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("product_area", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("started_at", sa.Text(), nullable=False),
        sa.Column("resolved_at", sa.Text()),
        sa.Column("affected_customers", sa.Text()),
        tenant_column(),
    )
    op.create_table(
        "escalations",
        sa.Column("escalation_id", sa.Text(), primary_key=True),
        sa.Column("ticket_id", sa.Text(), nullable=False),
        sa.Column("destination_team", sa.Text(), nullable=False),
        sa.Column("priority", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("agent_summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.func.current_timestamp()),
        sa.Column("status", sa.Text(), server_default="pending"),
        tenant_column(),
    )
    op.create_table(
        "agent_runs",
        sa.Column("run_id", sa.Text(), primary_key=True),
        sa.Column("ticket_id", sa.Text(), nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(), server_default=sa.func.current_timestamp()),
        sa.Column("completed_at", sa.TIMESTAMP()),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("final_status", sa.Text()),
        sa.Column("tools_used", sa.Text()),
        sa.Column("failure_category", sa.Text()),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.false()),
        tenant_column(),
    )
    op.create_table(
        "tool_events",
        sa.Column("event_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Text(), sa.ForeignKey("agent_runs.run_id"), nullable=False),
        sa.Column("tool_name", sa.Text(), nullable=False),
        sa.Column("tool_input", sa.Text()),
        sa.Column("tool_output_summary", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.TIMESTAMP(), server_default=sa.func.current_timestamp()),
        sa.Column("duration_ms", sa.Integer()),
        tenant_column(),
    )
    role_check = sa.CheckConstraint("role IN ('admin', 'agent', 'viewer')")
    op.create_table(
        "auth_users",
        sa.Column("user_id", sa.Text(), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.func.current_timestamp()),
        role_check,
        sa.UniqueConstraint("tenant_id", "username"),
    )
    op.create_table(
        "api_keys",
        sa.Column("key_id", sa.Text(), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("principal", sa.Text(), nullable=False),
        sa.Column("key_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.func.current_timestamp()),
        sa.CheckConstraint("role IN ('admin', 'agent', 'viewer')"),
    )
    op.create_table(
        "audit_logs",
        sa.Column("audit_id", sa.Text(), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("principal", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("resource_type", sa.Text(), nullable=False),
        sa.Column("resource_id", sa.Text()),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.Text()),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.func.current_timestamp()),
    )

    indexes = {
        "subscriptions": (("idx_subscriptions_customer", ("customer_id",), True),),
        "tickets": (
            ("idx_tickets_email", ("customer_email",), False),
            ("idx_tickets_status", ("status",), False),
        ),
        "incidents": (("idx_incidents_status", ("status",), False),),
        "escalations": (("idx_escalations_ticket", ("ticket_id",), False),),
        "agent_runs": (("idx_agent_runs_ticket", ("ticket_id",), False),),
        "audit_logs": (("idx_audit_tenant_created", ("tenant_id", "created_at"), False),),
    }
    for table, table_indexes in indexes.items():
        for name, columns, unique in table_indexes:
            op.create_index(name, table, list(columns), unique=unique)
    for table in BUSINESS_TABLES:
        op.create_index(f"idx_{table}_tenant", table, ["tenant_id"])

    if op.get_bind().dialect.name == "postgresql":
        tenant_tables = (*BUSINESS_TABLES, "auth_users", "api_keys", "audit_logs")
        for table in tenant_tables:
            op.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
            op.execute(
                sa.text(f"""CREATE POLICY {table}_tenant_policy ON {table}
                USING (NULLIF(current_setting('app.tenant_id', TRUE), '') IS NULL
                       OR tenant_id = current_setting('app.tenant_id', TRUE))
                WITH CHECK (NULLIF(current_setting('app.tenant_id', TRUE), '') IS NULL
                       OR tenant_id = current_setting('app.tenant_id', TRUE))""")
            )


def downgrade() -> None:
    """Remove all baseline schema objects."""
    for table in ("audit_logs", "api_keys", "auth_users", *reversed(BUSINESS_TABLES)):
        op.drop_table(table)
