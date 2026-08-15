"""Tests for the deterministic Nordly development dataset."""

import json

import pytest

from app.config import settings
from app.database import get_connection
from data.seed import ACCOUNT_STATUSES, CUSTOMERS, HISTORICAL_TICKETS, seed_all


@pytest.fixture
def seeded_database(tmp_path, monkeypatch):
    """Seed an isolated database and return its path."""
    database_path = tmp_path / "nordly-test.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{database_path}")
    seed_all()
    return database_path


def table_counts():
    """Return counts for all entities populated by the seed."""
    with get_connection() as connection:
        return {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("customers", "subscriptions", "account_status", "tickets", "incidents")
        }


def test_seed_has_required_size_and_coverage(seeded_database):
    """The seed contains the required plans, states, history, and incident."""
    counts = table_counts()
    assert 20 <= counts["customers"] <= 30
    assert 30 <= counts["tickets"] <= 50
    assert counts["subscriptions"] == counts["customers"]
    assert counts["account_status"] == counts["customers"]

    with get_connection() as connection:
        plans = {row[0] for row in connection.execute("SELECT DISTINCT plan FROM customers")}
        states = {row[0] for row in connection.execute("SELECT DISTINCT state FROM account_status")}
        incident = connection.execute(
            "SELECT severity, product_area, status FROM incidents WHERE incident_id = ?",
            ("INC-2041",),
        ).fetchone()
        incident_statuses = {
            row[0] for row in connection.execute("SELECT DISTINCT status FROM incidents")
        }

    assert plans == {"Starter", "Pro", "Business"}
    assert {"active", "trial", "suspended", "billing_hold", "cancelled"} <= states
    assert tuple(incident) == ("critical", "authentication", "investigating")
    assert "resolved" in incident_statuses
    assert incident_statuses - {"resolved"}


def test_seed_is_consistent_and_idempotent(seeded_database):
    """Every relationship is valid and a second seed does not change data."""
    with get_connection() as connection:
        first_counts = table_counts()
        first_tickets = connection.execute(
            "SELECT ticket_id, customer_email, created_at FROM tickets ORDER BY ticket_id"
        ).fetchall()

        assert (
            connection.execute(
                "SELECT COUNT(*) FROM subscriptions GROUP BY customer_id HAVING COUNT(*) != 1"
            ).fetchone()
            is None
        )
        assert (
            connection.execute(
                """SELECT COUNT(*) FROM tickets t
               LEFT JOIN customers c ON c.main_contact_email = t.customer_email
               WHERE c.customer_id IS NULL"""
            ).fetchone()[0]
            == 0
        )

        incidents = connection.execute("SELECT affected_customers FROM incidents").fetchall()
        customer_ids = {row[0] for row in connection.execute("SELECT customer_id FROM customers")}
        assert all(set(json.loads(row[0])) <= customer_ids for row in incidents)

    seed_all()

    with get_connection() as connection:
        second_tickets = connection.execute(
            "SELECT ticket_id, customer_email, created_at FROM tickets ORDER BY ticket_id"
        ).fetchall()

    assert table_counts() == first_counts
    assert [tuple(row) for row in second_tickets] == [tuple(row) for row in first_tickets]
    assert len(CUSTOMERS) == len(ACCOUNT_STATUSES)
    assert len({ticket["customer_email"] for ticket in HISTORICAL_TICKETS}) >= 20
