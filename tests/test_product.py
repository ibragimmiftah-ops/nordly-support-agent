"""Product surface tests for knowledge search and dashboard delivery."""

from fastapi.testclient import TestClient

from app.main import app
from app.tools.knowledge import KnowledgeBase


def test_local_knowledge_search_returns_documented_topic():
    """The local knowledge base answers a documented authentication query."""
    results = KnowledgeBase().search("MFA login", limit=3)
    assert results
    assert any(result.document_name == "authentication" for result in results)


def test_dashboard_is_served():
    """Dashboard route returns the responsive static client."""
    response = TestClient(app).get("/dashboard")
    assert response.status_code == 200
    assert "Nordly Support Operations" in response.text
    assert "viewport" in response.text
