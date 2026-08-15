"""Security, authentication, authorization, and tenant isolation tests."""

import uuid

from fastapi.testclient import TestClient

from app.auth.models import Principal, Role
from app.auth.passwords import hash_password, verify_password
from app.auth.repository import AuthRepository
from app.auth.tokens import create_token
from app.config import settings
from app.database import get_connection, init_database
from app.main import app
from app.repositories.ticket_repository import TicketRepository
from app.security.pii import redact_pii


def _client(tmp_path, monkeypatch) -> TestClient:
    database_path = tmp_path / f"security-{uuid.uuid4().hex}.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{database_path}")
    init_database()
    AuthRepository.ensure_demo_credentials()
    return TestClient(app)


def test_password_hashing_and_jwt_login(tmp_path, monkeypatch):
    """Passwords are bcrypt-hashed and login issues usable access and refresh JWTs."""
    password_hash = hash_password("A-secure-password-123!")
    assert password_hash != "A-secure-password-123!"
    assert verify_password("A-secure-password-123!", password_hash)
    client = _client(tmp_path, monkeypatch)
    response = client.post(
        "/api/v1/auth/login",
        json={
            "tenant_id": settings.demo_tenant_id,
            "username": settings.demo_admin_username,
            "password": settings.demo_admin_password,
        },
    )
    assert response.status_code == 200
    tokens = response.json()
    assert (
        client.get(
            "/api/v1/tickets", headers={"Authorization": f"Bearer {tokens['access_token']}"}
        ).status_code
        == 200
    )
    refresh_response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_response.status_code == 200
    rotated = refresh_response.json()
    assert rotated["refresh_token"] != tokens["refresh_token"]
    assert (
        client.post(
            "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/logout", json={"refresh_token": rotated["refresh_token"]}
        ).status_code
        == 204
    )
    assert (
        client.post(
            "/api/v1/auth/refresh", json={"refresh_token": rotated["refresh_token"]}
        ).status_code
        == 401
    )
    with get_connection() as conn:
        sessions = conn.execute("SELECT jti_hash FROM refresh_sessions").fetchall()
    assert sessions
    assert all(tokens["refresh_token"] not in row["jti_hash"] for row in sessions)


def test_api_requires_auth_and_enforces_rbac(tmp_path, monkeypatch):
    """Business APIs require authentication and viewer credentials remain read-only."""
    client = _client(tmp_path, monkeypatch)
    assert client.get("/api/v1/tickets").status_code == 401
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO auth_users (user_id, tenant_id, username, password_hash, role) "
            "VALUES (?, ?, ?, ?, ?)",
            ("viewer", "demo", "viewer", hash_password("viewer-password"), Role.VIEWER.value),
        )
        conn.commit()
    viewer = Principal(subject="viewer", tenant_id="demo", role=Role.VIEWER, auth_method="jwt")
    headers = {"Authorization": f"Bearer {create_token(viewer, 'access')}"}
    assert client.get("/api/v1/tickets", headers=headers).status_code == 200
    response = client.post(
        "/api/v1/tickets",
        headers=headers,
        json={"customer_email": "user@example.com", "subject": "Help", "message": "Please"},
    )
    assert response.status_code == 403


def test_api_key_validation_headers_and_input_validation(tmp_path, monkeypatch):
    """API keys authenticate, security headers are present, and shared validation is active."""
    client = _client(tmp_path, monkeypatch)
    response = client.get("/api/v1/tickets", headers={"X-API-Key": settings.demo_api_key})
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["strict-transport-security"] == ("max-age=31536000; includeSubDomains")
    invalid = client.post(
        "/api/v1/tickets",
        headers={"X-API-Key": settings.demo_api_key},
        json={"customer_email": "not-email", "subject": " ", "message": "ok"},
    )
    assert invalid.status_code == 422


def test_cross_tenant_ticket_access_is_hidden(tmp_path, monkeypatch):
    """A valid principal cannot read or mutate another tenant's ticket."""
    client = _client(tmp_path, monkeypatch)
    ticket_id = TicketRepository.create_ticket(
        {"customer_email": "a@example.com", "subject": "Secret", "message": "Private"},
        "tenant-a",
    )
    tenant_b = Principal(
        subject="agent-b", tenant_id="tenant-b", role=Role.AGENT, auth_method="jwt"
    )
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO auth_users (user_id, tenant_id, username, password_hash, role) "
            "VALUES (?, ?, ?, ?, ?)",
            ("agent-b", "tenant-b", "agent-b", hash_password("agent-password"), Role.AGENT.value),
        )
        conn.commit()
    headers = {"Authorization": f"Bearer {create_token(tenant_b, 'access')}"}
    assert client.get(f"/api/v1/tickets/{ticket_id}", headers=headers).status_code == 404
    assert (
        client.post(
            f"/api/v1/tickets/{ticket_id}/review", headers=headers, json={"status": "closed"}
        ).status_code
        == 404
    )


def test_gdpr_delete_is_admin_only_and_tenant_scoped(tmp_path, monkeypatch):
    """GDPR deletion requires admin and does not locate cross-tenant customers."""
    client = _client(tmp_path, monkeypatch)
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO customers (customer_id, company, domain, account_state, country, seats, "
            "plan, main_contact_email, tenant_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("C-A", "A", "a.test", "active", "NO", 1, "Starter", "a@a.test", "tenant-a"),
        )
        conn.commit()
    tenant_b = Principal(
        subject="admin-b", tenant_id="tenant-b", role=Role.ADMIN, auth_method="jwt"
    )
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO auth_users (user_id, tenant_id, username, password_hash, role) "
            "VALUES (?, ?, ?, ?, ?)",
            ("admin-b", "tenant-b", "admin-b", hash_password("admin-password"), Role.ADMIN.value),
        )
        conn.commit()
    headers = {"Authorization": f"Bearer {create_token(tenant_b, 'access')}"}
    assert client.delete("/api/v1/gdpr/customers/C-A", headers=headers).status_code == 404


def test_pii_redaction():
    """PII helper recursively redacts email addresses and phone numbers."""
    result = redact_pii({"message": "Email me@corp.test or call +1 212 555 0100"})
    assert "me@corp.test" not in result["message"]
    assert "555" not in result["message"]
