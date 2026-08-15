"""Observability endpoints, request correlation, and safe dashboard tests."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.config import settings
from app.database import init_database
from app.main import app


def _client(tmp_path, monkeypatch) -> TestClient:
    database_path = tmp_path / "observability.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{database_path}")
    init_database()
    return TestClient(app)


def test_correlation_id_is_accepted_or_safely_generated(tmp_path, monkeypatch):
    """Valid caller IDs are echoed while malformed values are replaced."""
    client = _client(tmp_path, monkeypatch)
    accepted = client.get("/health", headers={"X-Correlation-ID": "trace-123.test"})
    assert accepted.headers["X-Correlation-ID"] == "trace-123.test"

    generated = client.get("/health", headers={"X-Correlation-ID": "invalid id"})
    assert generated.headers["X-Correlation-ID"].startswith("corr-")
    assert generated.headers["X-Correlation-ID"] != "invalid id"


def test_metrics_are_public_and_use_bounded_route_labels(tmp_path, monkeypatch):
    """Prometheus scraping needs no business credential and excludes request secrets."""
    client = _client(tmp_path, monkeypatch)
    secret = "customer-secret@example.test"
    client.get("/api/v1/tickets/private-id", headers={"X-Correlation-ID": "metrics-test"})
    response = client.get("/metrics/")
    assert response.status_code == 200
    assert "nordly_http_requests_total" in response.text
    assert 'route="/api/v1/tickets/{ticket_id}"' in response.text
    assert secret not in response.text
    assert "private-id" not in response.text


def test_readiness_checks_database_and_reports_failure(tmp_path, monkeypatch):
    """Readiness reflects a real successful or failed database query."""
    client = _client(tmp_path, monkeypatch)
    assert client.get("/ready").json() == {"status": "ready", "database": "available"}

    class BrokenConnection:
        def __enter__(self):
            raise OSError("database unavailable")

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr("app.api.routes.get_connection", BrokenConnection)
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "database": "unavailable"}


def test_dashboard_uses_safe_dom_rendering_and_session_only_credentials():
    """Untrusted API values cannot be interpreted as HTML by the dashboard."""
    source = Path("app/static/index.html").read_text(encoding="utf-8")
    script = Path("app/static/dashboard.js").read_text(encoding="utf-8")
    assert "innerHTML" not in source
    assert "textContent" in script
    assert "createElement" in script
    assert "sessionStorage" in script
    assert "localStorage" not in script
    assert settings.demo_api_key not in source + script
    assert "response.status===401" in script
    assert "Authorization" in script
    assert "X-API-Key" in script
    assert "<style>" not in source and ">\n  const " not in source
