"""Customer repository for database operations."""

import json
from typing import Any

from app.agent.schemas import (
    AccountState,
    AccountStatus,
    BillingStatus,
    Customer,
    PlanType,
    Subscription,
)
from app.config import settings
from app.database import get_connection
from app.security.encryption import decrypt, encrypt


class CustomerRepository:
    """Repository for customer-related database operations."""

    @staticmethod
    def get_by_email(email: str, tenant_id: str = settings.demo_tenant_id) -> Customer | None:
        """Get customer by email address."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT customer_id, company, domain, account_state, country,
                       seats, plan, main_contact_email, created_at
                FROM customers
                WHERE tenant_id = ? AND (main_contact_email = ? OR ? LIKE '%' || domain)
                LIMIT 1
                """,
                (tenant_id, email, email),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return Customer(
                customer_id=row["customer_id"],
                company=row["company"],
                domain=row["domain"],
                account_state=AccountState(row["account_state"]),
                country=row["country"],
                seats=row["seats"],
                plan=PlanType(row["plan"]),
                main_contact_email=row["main_contact_email"],
                created_at=row["created_at"],
            )

    @staticmethod
    def get_by_id(customer_id: str, tenant_id: str = settings.demo_tenant_id) -> Customer | None:
        """Get customer by ID."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT customer_id, company, domain, account_state, country,
                       seats, plan, main_contact_email, created_at
                FROM customers
                WHERE customer_id = ? AND tenant_id = ?
                """,
                (customer_id, tenant_id),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return Customer(
                customer_id=row["customer_id"],
                company=row["company"],
                domain=row["domain"],
                account_state=AccountState(row["account_state"]),
                country=row["country"],
                seats=row["seats"],
                plan=PlanType(row["plan"]),
                main_contact_email=row["main_contact_email"],
                created_at=row["created_at"],
            )

    @staticmethod
    def get_subscription(
        customer_id: str, tenant_id: str = settings.demo_tenant_id
    ) -> Subscription | None:
        """Get subscription for a customer."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT customer_id, plan, billing_status, renewal_date,
                       cancellation_status, seat_limit, features, monthly_price
                FROM subscriptions
                WHERE customer_id = ? AND tenant_id = ?
                """,
                (customer_id, tenant_id),
            )
            row = cursor.fetchone()
            if not row:
                return None
            features = []
            if row["features"]:
                features = json.loads(row["features"])
            return Subscription(
                customer_id=row["customer_id"],
                plan=PlanType(row["plan"]),
                billing_status=BillingStatus(row["billing_status"]),
                renewal_date=row["renewal_date"],
                cancellation_status=bool(row["cancellation_status"]),
                seat_limit=row["seat_limit"],
                features=features,
                monthly_price=row["monthly_price"],
            )

    @staticmethod
    def get_account_status(
        customer_id: str, tenant_id: str = settings.demo_tenant_id
    ) -> AccountStatus | None:
        """Get account status for a customer."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT customer_id, state, state_reason, last_login,
                       mfa_enabled, sso_enabled, suspicious_activity, notes
                FROM account_status
                WHERE customer_id = ? AND tenant_id = ?
                """,
                (customer_id, tenant_id),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return AccountStatus(
                customer_id=row["customer_id"],
                state=AccountState(row["state"]),
                state_reason=row["state_reason"],
                last_login=row["last_login"],
                mfa_enabled=bool(row["mfa_enabled"]),
                sso_enabled=bool(row["sso_enabled"]),
                suspicious_activity=bool(row["suspicious_activity"]),
                notes=decrypt(row["notes"]),
            )

    @staticmethod
    def create_customer(
        customer_data: dict[str, Any], tenant_id: str = settings.demo_tenant_id
    ) -> None:
        """Create a new customer record."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO customers (customer_id, company, domain, account_state,
                                       country, seats, plan, main_contact_email, tenant_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    customer_data["customer_id"],
                    customer_data["company"],
                    customer_data["domain"],
                    customer_data["account_state"],
                    customer_data["country"],
                    customer_data["seats"],
                    customer_data["plan"],
                    customer_data["main_contact_email"],
                    tenant_id,
                ),
            )
            conn.commit()

    @staticmethod
    def create_subscription(
        sub_data: dict[str, Any], tenant_id: str = settings.demo_tenant_id
    ) -> None:
        """Create a new subscription record."""
        with get_connection() as conn:
            cursor = conn.cursor()
            features_json = json.dumps(sub_data.get("features", []))
            cursor.execute(
                """
                INSERT INTO subscriptions (customer_id, plan, billing_status,
                                           renewal_date, cancellation_status,
                                           seat_limit, features, monthly_price, tenant_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sub_data["customer_id"],
                    sub_data["plan"],
                    sub_data["billing_status"],
                    sub_data.get("renewal_date"),
                    sub_data.get("cancellation_status", False),
                    sub_data["seat_limit"],
                    features_json,
                    sub_data["monthly_price"],
                    tenant_id,
                ),
            )
            conn.commit()

    @staticmethod
    def create_account_status(
        status_data: dict[str, Any], tenant_id: str = settings.demo_tenant_id
    ) -> None:
        """Create a new account status record."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO account_status (customer_id, state, state_reason,
                                           last_login, mfa_enabled, sso_enabled,
                                           suspicious_activity, notes, tenant_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    status_data["customer_id"],
                    status_data["state"],
                    status_data.get("state_reason"),
                    status_data.get("last_login"),
                    status_data.get("mfa_enabled", False),
                    status_data.get("sso_enabled", False),
                    status_data.get("suspicious_activity", False),
                    encrypt(status_data.get("notes")),
                    tenant_id,
                ),
            )
            conn.commit()
