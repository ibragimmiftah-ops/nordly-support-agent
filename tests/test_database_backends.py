"""Backend-neutral database connection tests."""

# ruff: noqa: D102, D103, D107

import os

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.database import PostgresConnection, _convert_qmark_placeholders, get_connection


class FakeCursor:
    """Record calls made through the PostgreSQL compatibility adapter."""

    def __init__(self) -> None:
        self.calls = []
        self.rowcount = 1

    def execute(self, sql, params):
        self.calls.append(("execute", sql, params))

    def executemany(self, sql, params):
        self.calls.append(("executemany", sql, list(params)))

    def fetchone(self):
        return {"value": 1}

    def fetchall(self):
        return [{"value": 1}]


class FakeConnection:
    """Provide the psycopg connection methods used by the adapter."""

    def __init__(self) -> None:
        self.fake_cursor = FakeCursor()
        self.committed = False
        self.closed = False

    def cursor(self):
        return self.fake_cursor

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


def test_qmark_conversion_ignores_literals_identifiers_and_comments():
    sql = "SELECT ?, '?', \"?\", $$?$$ -- ?\nFROM data WHERE value = ? /* ? */"
    assert _convert_qmark_placeholders(sql) == (
        "SELECT %s, '?', \"?\", $$?$$ -- ?\nFROM data WHERE value = %s /* ? */"
    )


def test_postgres_adapter_converts_execute_and_executemany():
    raw = FakeConnection()
    connection = PostgresConnection(raw)

    row = connection.execute("SELECT value FROM data WHERE id = ?", (3,)).fetchone()
    connection.executemany("INSERT INTO data VALUES (?)", [(1,), (2,)])
    connection.commit()
    connection.close()

    assert row == {"value": 1}
    assert raw.fake_cursor.calls == [
        ("execute", "SELECT value FROM data WHERE id = %s", (3,)),
        ("executemany", "INSERT INTO data VALUES (%s)", [(1,), (2,)]),
    ]
    assert raw.committed is True
    assert raw.closed is True


def test_database_password_file_is_url_encoded(tmp_path):
    password_file = tmp_path / "password"
    password_file.write_text("p@ss:/ word\n", encoding="utf-8")

    configured = Settings(
        _env_file=None,
        DATABASE_URL="postgresql://nordly:{password}@postgres/nordly",
        DATABASE_PASSWORD_FILE=str(password_file),
    )

    assert configured.database_url == "postgresql://nordly:p%40ss%3A%2F%20word@postgres/nordly"


def test_database_password_placeholder_requires_file():
    with pytest.raises(ValidationError, match="DATABASE_PASSWORD_FILE is required"):
        Settings(_env_file=None, DATABASE_URL="postgresql://nordly:{password}@postgres/nordly")


def test_production_secrets_are_loaded_from_files(tmp_path):
    """Production rejects the default development JWT and resolves supported secret files."""
    jwt = tmp_path / "jwt"
    api = tmp_path / "api"
    bootstrap = tmp_path / "bootstrap"
    encryption = tmp_path / "encryption"
    jwt.write_text("production-jwt-secret-at-least-32-bytes", encoding="utf-8")
    api.write_text("sk-production", encoding="utf-8")
    bootstrap.write_text("strong-bootstrap-password", encoding="utf-8")
    encryption.write_text("production-encryption-material-at-least-32-bytes", encoding="utf-8")
    configured = Settings(
        _env_file=None,
        DEMO_MODE=False,
        JWT_SECRET_FILE=str(jwt),
        OPENAI_API_KEY_FILE=str(api),
        BOOTSTRAP_ADMIN_PASSWORD_FILE=str(bootstrap),
        BOOTSTRAP_ADMIN_USERNAME="admin",
        BOOTSTRAP_ADMIN_TENANT="tenant-a",
        ENCRYPTION_KEY_FILE=str(encryption),
        REDIS_URL="redis://redis:6379/0",
        METRICS_TOKEN="metrics-secret",
    )
    assert configured.jwt_secret.startswith("production-")
    assert configured.openai_api_key == "sk-production"
    assert configured.production_bootstrap_configured


def test_production_rejects_default_jwt_secret():
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(_env_file=None, DEMO_MODE=False)


@pytest.mark.integration
def test_postgres_connection_returns_mapping_rows(monkeypatch):
    """Run only when an explicit disposable PostgreSQL test URL is available."""
    database_url = os.getenv("POSTGRES_TEST_URL")
    if not database_url:
        pytest.skip("POSTGRES_TEST_URL is not configured")

    monkeypatch.setattr("app.database.settings.database_url", database_url)
    with get_connection() as connection:
        row = connection.execute("SELECT ? AS value", (1,)).fetchone()
    assert row["value"] == 1
