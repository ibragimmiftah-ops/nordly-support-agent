"""Offline API workflow tests."""

import pytest
from fastapi.testclient import TestClient

from app.auth.repository import AuthRepository
from app.config import settings
from app.database import init_database
from app.main import app
from data.seed import seed_all


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    """Create an isolated demo API client."""
    database_path = tmp_path / "api.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{database_path}")
    init_database()
    seed_all()
    AuthRepository.ensure_demo_credentials()
    return TestClient(app, headers={"X-API-Key": settings.demo_api_key})


def test_api_ticket_workflow_and_bounded_lists(api_client):
    """Create, analyze, fetch, review, and list a ticket."""
    created = api_client.post(
        "/api/v1/tickets",
        json={
            "customer_email": "support@bergenlogistics.no",
            "subject": "How do I enable MFA?",
            "message": "Please explain the setup steps.",
        },
    )
    assert created.status_code == 200
    ticket_id = created.json()["ticket_id"]
    analyzed = api_client.post(f"/api/v1/tickets/{ticket_id}/analyze")
    assert analyzed.status_code == 200
    assert analyzed.json()["decision"]["ticket_id"] == ticket_id
    assert api_client.get(f"/api/v1/tickets/{ticket_id}").status_code == 200
    assert (
        api_client.post(
            f"/api/v1/tickets/{ticket_id}/review", json={"status": "resolved"}
        ).status_code
        == 200
    )
    assert len(api_client.get("/api/v1/tickets?limit=1000").json()["tickets"]) <= 100
    assert len(api_client.get("/api/v1/incidents?limit=1000").json()["incidents"]) <= 100


def test_api_not_found_and_health(api_client):
    """Health and missing-resource responses are stable."""
    assert api_client.get("/health").json()["status"] == "healthy"
    assert api_client.get("/api/v1/tickets/missing").status_code == 404
    assert api_client.get("/api/v1/customers/C-NL-9999").status_code == 404
