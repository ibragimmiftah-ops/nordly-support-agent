"""Subscription and account status lookup tools.

Bounded: requires verified customer_id.
"""

from app.agent.schemas import AccountStatus, Subscription
from app.repositories.customer_repository import CustomerRepository


def get_subscription(customer_id: str, tenant_id: str = "demo") -> Subscription | None:
    """Get subscription details for a customer.

    Args:
        customer_id: Verified customer ID.
        tenant_id: Authenticated tenant boundary.

    Returns:
        Subscription record if found, None otherwise.
    """
    if not customer_id or len(customer_id) > 64:
        return None
    return CustomerRepository.get_subscription(customer_id, tenant_id)


def get_account_status(customer_id: str, tenant_id: str = "demo") -> AccountStatus | None:
    """Get account status for a customer.

    Args:
        customer_id: Verified customer ID.
        tenant_id: Authenticated tenant boundary.

    Returns:
        AccountStatus record if found, None otherwise.
    """
    if not customer_id or len(customer_id) > 64:
        return None
    return CustomerRepository.get_account_status(customer_id, tenant_id)
