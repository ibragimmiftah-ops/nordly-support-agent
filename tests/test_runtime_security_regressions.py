"""Regression coverage for runtime security audit findings."""

import threading
import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.agent.memory import MemoryRecord
from app.auth.repository import AuthRepository
from app.config import settings
from app.database import get_connection, init_database
from app.main import app
from app.repositories.memory_repository import MemoryRepository
from app.repositories.ticket_repository import TicketRepository
from app.repositories.usage_repository import UsageRepository


def _database(tmp_path, monkeypatch) -> None:
    path = tmp_path / f"runtime-{uuid.uuid4().hex}.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{path}")
    init_database()


def test_sensitive_fields_are_ciphertext_at_rest_and_decrypt_on_read(tmp_path, monkeypatch):
    """Ticket messages and memory content are never stored as plaintext."""
    _database(tmp_path, monkeypatch)
    ticket_id = TicketRepository.create_ticket(
        {"customer_email": "person@example.com", "subject": "Private", "message": "secret body"}
    )
    record = MemoryRecord(
        memory_id="mem-1",
        tenant_id="demo",
        customer_id="customer-1",
        source="ticket",
        confidence=0.9,
        content="secret memory",
        dedup_hash="hash-1",
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    assert MemoryRepository.save(record)
    with get_connection() as conn:
        ticket_row = conn.execute(
            "SELECT message FROM tickets WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
        memory_row = conn.execute(
            "SELECT content FROM agent_memory WHERE memory_id = ?", (record.memory_id,)
        ).fetchone()
    assert ticket_row["message"].startswith("enc:v1:")
    assert memory_row["content"].startswith("enc:v1:")
    assert "secret" not in ticket_row["message"] + memory_row["content"]
    assert TicketRepository.get_ticket(ticket_id).message == "secret body"
    assert MemoryRepository.recall("demo", "customer-1", 1)[0].content == "secret memory"


def test_budget_reservation_is_atomic_across_concurrent_sqlite_calls(tmp_path, monkeypatch):
    """Concurrent callers cannot both reserve capacity beyond the tenant budget."""
    _database(tmp_path, monkeypatch)
    barrier = threading.Barrier(2)
    results: list[str | None] = []

    def reserve() -> None:
        barrier.wait()
        results.append(UsageRepository.reserve("demo", 0.04, 0.05, 0.05))

    threads = [threading.Thread(target=reserve) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sum(result is not None for result in results) == 1


def test_deactivated_user_cannot_refresh_and_metrics_token_is_enforced(tmp_path, monkeypatch):
    """Refresh checks current user state and metrics uses its dedicated credential."""
    _database(tmp_path, monkeypatch)
    AuthRepository.ensure_demo_credentials()
    client = TestClient(app)
    login = client.post(
        "/api/v1/auth/login",
        json={
            "tenant_id": settings.demo_tenant_id,
            "username": settings.demo_admin_username,
            "password": settings.demo_admin_password,
        },
    ).json()
    with get_connection() as conn:
        conn.execute(
            "UPDATE auth_users SET active = FALSE WHERE tenant_id = ? AND username = ?",
            (settings.demo_tenant_id, settings.demo_admin_username),
        )
        conn.commit()
    assert (
        client.post(
            "/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]}
        ).status_code
        == 401
    )

    monkeypatch.setattr(settings, "metrics_token", "scrape-secret")
    assert client.get("/metrics/").status_code == 401
    assert client.get("/metrics/", headers={"X-Metrics-Token": "scrape-secret"}).status_code == 200
    assert (
        client.get("/metrics/", headers={"Authorization": "Bearer scrape-secret"}).status_code
        == 200
    )
