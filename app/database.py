"""Database connections and schema initialization for SQLite and PostgreSQL."""

# ruff: noqa: E501

import sqlite3
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from app.config import settings
from app.observability.tracing import trace_span
from app.tenant import tenant_id_context

BUSINESS_TABLES = (
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
    "budget_reservations",
)


def _convert_qmark_placeholders(sql: str) -> str:
    """Convert DB-API qmark parameters without touching SQL literals or comments."""
    result: list[str] = []
    index = 0
    state = "sql"
    dollar_tag = ""
    while index < len(sql):
        char = sql[index]
        pair = sql[index : index + 2]
        if state == "sql":
            if char == "'":
                state = "single"
            elif char == '"':
                state = "double"
            elif pair == "--":
                state = "line_comment"
                result.append(pair)
                index += 2
                continue
            elif pair == "/*":
                state = "block_comment"
                result.append(pair)
                index += 2
                continue
            elif char == "$":
                end = sql.find("$", index + 1)
                tag_name = sql[index + 1 : end]
                if end != -1 and (not tag_name or tag_name.replace("_", "a").isalnum()):
                    dollar_tag = sql[index : end + 1]
                    state = "dollar"
                    result.append(dollar_tag)
                    index = end + 1
                    continue
            elif char == "?":
                char = "%s"
        elif state == "single" and char == "'":
            if index + 1 < len(sql) and sql[index + 1] == "'":
                result.append("''")
                index += 2
                continue
            state = "sql"
        elif state == "double" and char == '"':
            if index + 1 < len(sql) and sql[index + 1] == '"':
                result.append('""')
                index += 2
                continue
            state = "sql"
        elif state == "line_comment" and char in "\r\n":
            state = "sql"
        elif state == "block_comment" and pair == "*/":
            result.append(pair)
            index += 2
            state = "sql"
            continue
        elif state == "dollar" and sql.startswith(dollar_tag, index):
            result.append(dollar_tag)
            index += len(dollar_tag)
            state = "sql"
            continue
        result.append(char)
        index += 1
    return "".join(result)


class PostgresCursor:
    """Expose a SQLite-compatible cursor over a psycopg cursor."""

    def __init__(self, cursor: Any) -> None:
        """Wrap a psycopg cursor."""
        self._cursor = cursor

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> "PostgresCursor":
        """Execute SQL after adapting its placeholders."""
        self._cursor.execute(_convert_qmark_placeholders(sql), params)
        return self

    def executemany(self, sql: str, params: Iterable[Sequence[Any]]) -> "PostgresCursor":
        """Execute adapted SQL for every parameter sequence."""
        self._cursor.executemany(_convert_qmark_placeholders(sql), params)
        return self

    def fetchone(self) -> Any:
        """Fetch one mapping row."""
        return self._cursor.fetchone()

    def fetchall(self) -> list[Any]:
        """Fetch all mapping rows."""
        return self._cursor.fetchall()

    @property
    def rowcount(self) -> int:
        """Return the number of affected rows."""
        return self._cursor.rowcount


class PostgresConnection:
    """Expose the subset of sqlite3.Connection used by repositories."""

    def __init__(self, connection: Any) -> None:
        """Wrap a psycopg connection."""
        self._connection = connection

    def cursor(self) -> PostgresCursor:
        """Create a mapping-row cursor."""
        return PostgresCursor(self._connection.cursor())

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> PostgresCursor:
        """Execute one statement and return its cursor."""
        return self.cursor().execute(sql, params)

    def executemany(self, sql: str, params: Iterable[Sequence[Any]]) -> PostgresCursor:
        """Execute one statement for every parameter sequence."""
        return self.cursor().executemany(sql, params)

    def commit(self) -> None:
        """Commit the current transaction."""
        self._connection.commit()

    def rollback(self) -> None:
        """Roll back the current transaction."""
        self._connection.rollback()

    def close(self) -> None:
        """Close the underlying connection."""
        self._connection.close()


def _is_postgres_url(url: str) -> bool:
    return url.startswith(("postgresql://", "postgres://"))


def _add_column(conn: sqlite3.Connection, table: str, definition: str) -> None:
    """Add a column when upgrading an existing SQLite database."""
    column = definition.split()[0]
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")


def get_db_path() -> Path:
    """Extract the SQLite database file path from DATABASE_URL."""
    db_url = settings.database_url
    if db_url.startswith("sqlite:///"):
        return Path(db_url.removeprefix("sqlite:///"))
    return Path(db_url)


SQLITE_TABLES = (
    """CREATE TABLE IF NOT EXISTS customers (customer_id TEXT PRIMARY KEY, company TEXT NOT NULL,
    domain TEXT NOT NULL, account_state TEXT NOT NULL, country TEXT NOT NULL, seats INTEGER NOT NULL,
    plan TEXT NOT NULL, main_contact_email TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS subscriptions (subscription_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL, plan TEXT NOT NULL, billing_status TEXT NOT NULL, renewal_date TEXT,
    cancellation_status BOOLEAN DEFAULT 0, seat_limit INTEGER NOT NULL, features TEXT,
    monthly_price REAL NOT NULL, FOREIGN KEY (customer_id) REFERENCES customers(customer_id))""",
    """CREATE TABLE IF NOT EXISTS account_status (account_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL UNIQUE, state TEXT NOT NULL, state_reason TEXT, last_login TEXT,
    mfa_enabled BOOLEAN DEFAULT 0, sso_enabled BOOLEAN DEFAULT 0, suspicious_activity BOOLEAN DEFAULT 0,
    notes TEXT, FOREIGN KEY (customer_id) REFERENCES customers(customer_id))""",
    """CREATE TABLE IF NOT EXISTS tickets (ticket_id TEXT PRIMARY KEY, customer_email TEXT NOT NULL,
    subject TEXT NOT NULL, message TEXT NOT NULL, product_area TEXT, status TEXT DEFAULT 'open',
    priority TEXT, category TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, analyzed_at TIMESTAMP,
    decision_json TEXT)""",
    """CREATE TABLE IF NOT EXISTS incidents (incident_id TEXT PRIMARY KEY, title TEXT NOT NULL,
    product_area TEXT NOT NULL, status TEXT NOT NULL, severity TEXT NOT NULL, description TEXT NOT NULL,
    started_at TEXT NOT NULL, resolved_at TEXT, affected_customers TEXT)""",
    """CREATE TABLE IF NOT EXISTS escalations (escalation_id TEXT PRIMARY KEY, ticket_id TEXT NOT NULL,
    destination_team TEXT NOT NULL, priority TEXT NOT NULL, reason TEXT NOT NULL, agent_summary TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, status TEXT DEFAULT 'pending')""",
    """CREATE TABLE IF NOT EXISTS agent_runs (run_id TEXT PRIMARY KEY, ticket_id TEXT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, completed_at TIMESTAMP, duration_ms INTEGER,
    final_status TEXT, tools_used TEXT, failure_category TEXT, is_demo BOOLEAN DEFAULT 0)""",
    """CREATE TABLE IF NOT EXISTS tool_events (event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL, tool_name TEXT NOT NULL, tool_input TEXT, tool_output_summary TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, duration_ms INTEGER,
    FOREIGN KEY (run_id) REFERENCES agent_runs(run_id))""",
    """CREATE TABLE IF NOT EXISTS agent_memory (memory_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
    customer_id TEXT NOT NULL, source TEXT NOT NULL, confidence REAL NOT NULL, content TEXT NOT NULL,
    dedup_hash TEXT NOT NULL, created_at TIMESTAMP NOT NULL, expires_at TIMESTAMP NOT NULL,
    UNIQUE (tenant_id, customer_id, dedup_hash))""",
    """CREATE TABLE IF NOT EXISTS provider_usage (usage_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
    model TEXT NOT NULL, input_tokens INTEGER NOT NULL, output_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL, created_at TIMESTAMP NOT NULL, customer_id TEXT)""",
    """CREATE TABLE IF NOT EXISTS budget_reservations (reservation_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL, estimated_cost_usd REAL NOT NULL, created_at TIMESTAMP NOT NULL)""",
)

POSTGRES_TABLES = (
    """CREATE TABLE IF NOT EXISTS customers (customer_id TEXT PRIMARY KEY, company TEXT NOT NULL,
    domain TEXT NOT NULL, account_state TEXT NOT NULL, country TEXT NOT NULL, seats INTEGER NOT NULL,
    plan TEXT NOT NULL, main_contact_email TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tenant_id TEXT NOT NULL DEFAULT 'demo')""",
    """CREATE TABLE IF NOT EXISTS subscriptions (subscription_id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id), plan TEXT NOT NULL, billing_status TEXT NOT NULL,
    renewal_date TEXT, cancellation_status BOOLEAN DEFAULT FALSE, seat_limit INTEGER NOT NULL, features TEXT,
    monthly_price DOUBLE PRECISION NOT NULL, tenant_id TEXT NOT NULL DEFAULT 'demo')""",
    """CREATE TABLE IF NOT EXISTS account_status (account_id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    customer_id TEXT NOT NULL UNIQUE REFERENCES customers(customer_id), state TEXT NOT NULL, state_reason TEXT,
    last_login TEXT, mfa_enabled BOOLEAN DEFAULT FALSE, sso_enabled BOOLEAN DEFAULT FALSE,
    suspicious_activity BOOLEAN DEFAULT FALSE, notes TEXT, tenant_id TEXT NOT NULL DEFAULT 'demo')""",
    """CREATE TABLE IF NOT EXISTS tickets (ticket_id TEXT PRIMARY KEY, customer_email TEXT NOT NULL,
    subject TEXT NOT NULL, message TEXT NOT NULL, product_area TEXT, status TEXT DEFAULT 'open', priority TEXT,
    category TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, analyzed_at TIMESTAMP, decision_json TEXT,
    tenant_id TEXT NOT NULL DEFAULT 'demo')""",
    """CREATE TABLE IF NOT EXISTS incidents (incident_id TEXT PRIMARY KEY, title TEXT NOT NULL,
    product_area TEXT NOT NULL, status TEXT NOT NULL, severity TEXT NOT NULL, description TEXT NOT NULL,
    started_at TEXT NOT NULL, resolved_at TEXT, affected_customers TEXT, tenant_id TEXT NOT NULL DEFAULT 'demo')""",
    """CREATE TABLE IF NOT EXISTS escalations (escalation_id TEXT PRIMARY KEY, ticket_id TEXT NOT NULL,
    destination_team TEXT NOT NULL, priority TEXT NOT NULL, reason TEXT NOT NULL, agent_summary TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, status TEXT DEFAULT 'pending',
    tenant_id TEXT NOT NULL DEFAULT 'demo')""",
    """CREATE TABLE IF NOT EXISTS agent_runs (run_id TEXT PRIMARY KEY, ticket_id TEXT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, completed_at TIMESTAMP, duration_ms INTEGER,
    final_status TEXT, tools_used TEXT, failure_category TEXT, is_demo BOOLEAN DEFAULT FALSE,
    tenant_id TEXT NOT NULL DEFAULT 'demo')""",
    """CREATE TABLE IF NOT EXISTS tool_events (event_id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES agent_runs(run_id), tool_name TEXT NOT NULL, tool_input TEXT,
    tool_output_summary TEXT NOT NULL, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, duration_ms INTEGER,
    tenant_id TEXT NOT NULL DEFAULT 'demo')""",
    """CREATE TABLE IF NOT EXISTS agent_memory (memory_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
    customer_id TEXT NOT NULL, source TEXT NOT NULL, confidence DOUBLE PRECISION NOT NULL,
    content TEXT NOT NULL, dedup_hash TEXT NOT NULL, created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL, UNIQUE (tenant_id, customer_id, dedup_hash))""",
    """CREATE TABLE IF NOT EXISTS provider_usage (usage_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
    model TEXT NOT NULL, input_tokens INTEGER NOT NULL, output_tokens INTEGER NOT NULL,
    cost_usd DOUBLE PRECISION NOT NULL, created_at TIMESTAMP NOT NULL, customer_id TEXT)""",
    """CREATE TABLE IF NOT EXISTS budget_reservations (reservation_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL, estimated_cost_usd DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMP NOT NULL)""",
)

AUTH_TABLES = (
    """CREATE TABLE IF NOT EXISTS auth_users (user_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
    username TEXT NOT NULL, password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'agent', 'viewer')),
    active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (tenant_id, username))""",
    """CREATE TABLE IF NOT EXISTS api_keys (key_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
    principal TEXT NOT NULL, key_hash TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL CHECK (role IN ('admin', 'agent', 'viewer')),
    active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS audit_logs (audit_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
    principal TEXT NOT NULL, action TEXT NOT NULL, resource_type TEXT NOT NULL, resource_id TEXT,
    outcome TEXT NOT NULL, metadata_json TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS refresh_sessions (session_id TEXT PRIMARY KEY,
    jti_hash TEXT NOT NULL UNIQUE, tenant_id TEXT NOT NULL, user_id TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL, revoked_at TIMESTAMP, used_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES auth_users(user_id))""",
)

INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_tickets_email ON tickets(customer_email)",
    "CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)",
    "CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status)",
    "CREATE INDEX IF NOT EXISTS idx_escalations_ticket ON escalations(ticket_id)",
    "CREATE INDEX IF NOT EXISTS idx_agent_runs_ticket ON agent_runs(ticket_id)",
    "CREATE INDEX IF NOT EXISTS idx_audit_tenant_created ON audit_logs(tenant_id, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_refresh_user_active ON refresh_sessions(tenant_id, user_id, expires_at)",
    "CREATE INDEX IF NOT EXISTS idx_memory_recall ON agent_memory(tenant_id, customer_id, expires_at, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_usage_budget ON provider_usage(tenant_id, created_at)",
)


def init_database() -> None:
    """Initialize SQLite only; PostgreSQL schema is exclusively Alembic-managed."""
    postgres = _is_postgres_url(settings.database_url)
    if postgres:
        verify_postgres_schema()
        return
    if not postgres:
        db_path = get_db_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)

    with get_connection() as conn:
        for statement in POSTGRES_TABLES if postgres else SQLITE_TABLES:
            conn.execute(statement)
        if not postgres:
            for table in BUSINESS_TABLES:
                _add_column(conn, table, "tenant_id TEXT NOT NULL DEFAULT 'demo'")
            _add_column(conn, "provider_usage", "customer_id TEXT")
        for statement in AUTH_TABLES:
            conn.execute(statement)
        for statement in INDEXES:
            conn.execute(statement)
        for table in BUSINESS_TABLES:
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_tenant ON {table}(tenant_id)")
        if not postgres:
            conn.execute("""DELETE FROM subscriptions WHERE subscription_id NOT IN
                         (SELECT MIN(subscription_id) FROM subscriptions GROUP BY customer_id)""")
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_subscriptions_customer "
            "ON subscriptions(customer_id)"
        )
        conn.commit()


def verify_postgres_schema() -> None:
    """Fail startup unless PostgreSQL is migrated to this application's Alembic head."""
    with get_connection() as conn:
        row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        if not row or row["version_num"] != "0004":
            raise RuntimeError("PostgreSQL schema is not at Alembic head 0004")
        rows = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        ).fetchall()
        present = {row["table_name"] for row in rows}
        required = set(BUSINESS_TABLES) | {
            "auth_users",
            "api_keys",
            "audit_logs",
            "refresh_sessions",
        }
        missing = required - present
        if missing:
            raise RuntimeError(f"PostgreSQL schema is missing tables: {sorted(missing)}")


@contextmanager
def get_connection() -> Iterator[Any]:
    """Get a SQLite connection or a compatibility-wrapped psycopg connection."""
    postgres = _is_postgres_url(settings.database_url)
    with trace_span("db.connection", {"db.system": "postgresql" if postgres else "sqlite"}):
        if postgres:
            import psycopg
            from psycopg.rows import dict_row

            raw_connection = psycopg.connect(settings.database_url, row_factory=dict_row)
            conn: Any = PostgresConnection(raw_connection)
            raw_connection.execute(
                "SELECT set_config('app.tenant_id', %s, true)",
                (tenant_id_context.get() or "",),
            )
        else:
            raw_connection = sqlite3.connect(str(get_db_path()))
            raw_connection.row_factory = sqlite3.Row
            raw_connection.execute("PRAGMA foreign_keys = ON")
            conn = raw_connection
        try:
            yield conn
        finally:
            conn.close()
