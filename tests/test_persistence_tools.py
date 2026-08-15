"""Offline coverage for bounded tools and persistence repositories."""

import pytest

from app.database import init_database
from app.tools.incidents import check_active_incidents
from app.tools.subscriptions import get_account_status, get_subscription
from app.tools.tickets import get_previous_tickets
from data.seed import seed_all


@pytest.fixture
def seeded_database(tmp_path, monkeypatch):
    """Use a private seeded SQLite database."""
    database_path = tmp_path / "tools.db"
    from app.config import settings

    monkeypatch.setattr(settings, "database_url", f"sqlite:///{database_path}")
    init_database()
    seed_all()


def test_tools_return_scoped_bounded_results(seeded_database):
    """Tools return only requested customer data and respect limits."""
    incidents = check_active_incidents(limit=1)
    assert len(incidents) == 1
    tickets = get_previous_tickets("support@bergenlogistics.no", limit=1000)
    assert len(tickets) <= 20
    assert get_subscription("C-NL-1001").customer_id == "C-NL-1001"
    assert get_account_status("C-NL-1001").customer_id == "C-NL-1001"


def test_tools_handle_empty_and_unauthorized_shaped_inputs(seeded_database):
    """Unknown and malformed customer identifiers reveal no records."""
    assert get_subscription("") is None
    assert get_account_status("x" * 65) is None
    assert get_subscription("C-NL-9999") is None
    assert get_account_status("C-NL-9999") is None
    assert get_previous_tickets("nobody@example.invalid") == []
