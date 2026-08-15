"""Customer lookup tool for the support agent.

Bounded: only returns data for the exact email or domain match.
"""

from app.agent.schemas import Customer
from app.repositories.customer_repository import CustomerRepository


def get_customer_by_email(email: str, tenant_id: str = "demo") -> Customer | None:
    """Look up a customer by email address.

    Args:
        email: Customer email address.
        tenant_id: Authenticated tenant boundary.

    Returns:
        Customer record if found, None otherwise.
    """
    return CustomerRepository.get_by_email(email, tenant_id)
